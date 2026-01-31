"""
Compute Clean Patient Status and DQI scores.

Usage:
    python manage.py compute_metrics [--study_id=Study_1]

Architecture Integration:
- KPI + Analytics Service component
- Computes metrics based on fact table data
- Feeds all role-based dashboards
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Sum, Avg
from apps.core.models import Study, Site, Subject
from apps.monitoring.models import Query, MissingVisit, MissingPage, NonConformantEvent, SDVStatus, PISignatureStatus
from apps.safety.models import SAEDiscrepancy, LabIssue
from apps.medical_coding.models import CodingItem, EDRROpenIssue
from apps.metrics.models import CleanPatientStatus, DQIScoreSubject, DQIScoreSite, DQIScoreStudy, DQIWeightConfig
import json


class Command(BaseCommand):
    help = 'Compute Clean Patient Status and DQI scores'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study_id',
            type=str,
            help='Compute for specific study (default: all studies)'
        )

    def handle(self, *args, **options):
        study_id = options.get('study_id')

        if study_id:
            studies = Study.objects.filter(study_id=study_id)
        else:
            studies = Study.objects.all()

        for study in studies:
            self.stdout.write(f'\n=== Computing metrics for {study.study_id} ===')

            # Step 1: Compute Clean Patient Status
            self._compute_clean_status(study)

            # Step 2: Compute DQI Scores (Subject level)
            self._compute_dqi_subject(study)

            # Step 3: Roll up to Site level
            self._compute_dqi_site(study)

            # Step 4: Roll up to Study level
            self._compute_dqi_study(study)

        self.stdout.write(self.style.SUCCESS('\nMetrics computation complete'))

    def _compute_clean_status(self, study):
        """Compute Clean Patient Status for all subjects in study."""
        self.stdout.write('Computing Clean Patient Status...')

        subjects = Subject.objects.filter(study=study)
        computed = 0

        for subject in subjects:
            # Count blockers
            missing_visits = MissingVisit.objects.filter(subject=subject).count()
            missing_pages = MissingPage.objects.filter(subject=subject).count()
            open_queries = Query.objects.filter(subject=subject, query_status='Open').count()
            non_conformant = NonConformantEvent.objects.filter(subject=subject, status='Open').count()
            sae_discrepancies = SAEDiscrepancy.objects.filter(subject=subject).count()

            # Get SDV completion
            sdv_record = SDVStatus.objects.filter(subject=subject).first()
            sdv_pct = sdv_record.completion_percentage if sdv_record else 0
            sdv_incomplete = sdv_pct < 100

            # Get PI signature completion
            pi_sig = PISignatureStatus.objects.filter(subject=subject).first()
            pi_pct = pi_sig.completion_percentage if pi_sig else 0
            pi_incomplete = pi_pct < 100

            # Get coding backlog
            coding_uncoded = CodingItem.objects.filter(
                subject=subject,
                coding_status__in=['Uncoded', 'Pending']
            ).count()

            # Get EDRR issues
            edrr = EDRROpenIssue.objects.filter(subject=subject).first()
            edrr_count = edrr.total_open_issue_count if edrr else 0

            # Determine if clean (ALL conditions must be true)
            is_clean = (
                missing_visits == 0 and
                missing_pages == 0 and
                open_queries == 0 and
                non_conformant == 0 and
                sae_discrepancies == 0 and
                not sdv_incomplete and
                not pi_incomplete
                # Optional: coding_uncoded == 0 and edrr_count == 0
            )

            # Build blockers JSON
            blockers = []
            if missing_visits > 0:
                blockers.append({'type': 'missing_visits', 'count': missing_visits, 'severity': 'high'})
            if missing_pages > 0:
                blockers.append({'type': 'missing_pages', 'count': missing_pages, 'severity': 'medium'})
            if open_queries > 0:
                blockers.append({'type': 'open_queries', 'count': open_queries, 'severity': 'medium'})
            if non_conformant > 0:
                blockers.append({'type': 'non_conformant', 'count': non_conformant, 'severity': 'medium'})
            if sae_discrepancies > 0:
                blockers.append({'type': 'sae_discrepancies', 'count': sae_discrepancies, 'severity': 'critical'})
            if sdv_incomplete:
                blockers.append({'type': 'sdv_incomplete', 'count': 100 - sdv_pct, 'severity': 'high'})
            if pi_incomplete:
                blockers.append({'type': 'pi_signature_incomplete', 'count': 100 - pi_pct, 'severity': 'high'})

            # Create or update Clean Patient Status
            CleanPatientStatus.objects.update_or_create(
                subject=subject,
                defaults={
                    'is_clean': is_clean,
                    'has_missing_visits': missing_visits > 0,
                    'missing_visits_count': missing_visits,
                    'has_missing_pages': missing_pages > 0,
                    'missing_pages_count': missing_pages,
                    'has_open_queries': open_queries > 0,
                    'open_queries_count': open_queries,
                    'has_non_conformant': non_conformant > 0,
                    'non_conformant_count': non_conformant,
                    'has_sae_discrepancies': sae_discrepancies > 0,
                    'sae_discrepancy_count': sae_discrepancies,
                    'sdv_incomplete': sdv_incomplete,
                    'sdv_completion_pct': sdv_pct,
                    'pi_signature_incomplete': pi_incomplete,
                    'pi_signature_completion_pct': pi_pct,
                    'has_coding_backlog': coding_uncoded > 0,
                    'coding_uncoded_count': coding_uncoded,
                    'has_edrr_issues': edrr_count > 0,
                    'edrr_open_issue_count': edrr_count,
                    'blockers_json': json.dumps(blockers)
                }
            )
            computed += 1

        self.stdout.write(f'Computed Clean Status for {computed} subjects')

    def _compute_dqi_subject(self, study):
        """Compute DQI scores at subject level."""
        self.stdout.write('Computing DQI scores (subject level)...')

        subjects = Subject.objects.filter(study=study)
        weights = {w.metric_name: w.weight for w in DQIWeightConfig.objects.filter(is_active=True)}

        computed = 0

        for subject in subjects:
            clean_status = CleanPatientStatus.objects.filter(subject=subject).first()
            if not clean_status:
                continue

            # Normalize each component to 0-100 (lower is better)
            # Simple normalization: cap at 100
            sae_score = min(clean_status.sae_discrepancy_count * 25, 100)
            missing_visits_score = min(clean_status.missing_visits_count * 10, 100)
            missing_pages_score = min(clean_status.missing_pages_count * 5, 100)
            open_queries_score = min(clean_status.open_queries_count * 3, 100)
            non_conformant_score = min(clean_status.non_conformant_count * 5, 100)
            sdv_score = 100 - clean_status.sdv_completion_pct
            pi_sig_score = 100 - clean_status.pi_signature_completion_pct
            coding_score = min(clean_status.coding_uncoded_count * 2, 100)
            edrr_score = min(clean_status.edrr_open_issue_count * 5, 100)

            # Calculate weighted composite DQI
            composite_dqi = (
                sae_score * weights.get('sae_unresolved_count', 0.25) +
                missing_visits_score * weights.get('missing_visits_days_overdue', 0.15) +
                open_queries_score * weights.get('open_queries_count', 0.15) +
                missing_pages_score * weights.get('missing_pages_count', 0.10) +
                non_conformant_score * weights.get('non_conformant_count', 0.10) +
                sdv_score * weights.get('sdv_incomplete_pct', 0.10) +
                pi_sig_score * weights.get('pi_signature_incomplete_pct', 0.05) +
                coding_score * weights.get('coding_uncoded_count', 0.05) +
                edrr_score * weights.get('edrr_open_issue_count', 0.05)
            )

            # Assign risk band
            if composite_dqi < 25:
                risk_band = 'Low'
            elif composite_dqi < 50:
                risk_band = 'Medium'
            elif composite_dqi < 75:
                risk_band = 'High'
            else:
                risk_band = 'Critical'

            # Create or update DQI score
            DQIScoreSubject.objects.update_or_create(
                subject=subject,
                defaults={
                    'sae_unresolved_score': sae_score,
                    'missing_visits_score': missing_visits_score,
                    'missing_pages_score': missing_pages_score,
                    'open_queries_score': open_queries_score,
                    'non_conformant_score': non_conformant_score,
                    'sdv_incomplete_score': sdv_score,
                    'pi_signature_score': pi_sig_score,
                    'coding_backlog_score': coding_score,
                    'edrr_issue_score': edrr_score,
                    'composite_dqi_score': round(composite_dqi, 2),
                    'risk_band': risk_band
                }
            )
            computed += 1

        self.stdout.write(f'Computed DQI for {computed} subjects')

    def _compute_dqi_site(self, study):
        """Roll up DQI to site level."""
        self.stdout.write('Computing DQI scores (site level)...')

        sites = Site.objects.filter(study=study)

        for site in sites:
            subjects = Subject.objects.filter(site=site)
            total_subjects = subjects.count()

            if total_subjects == 0:
                continue

            clean_subjects = CleanPatientStatus.objects.filter(
                subject__in=subjects,
                is_clean=True
            ).count()

            clean_pct = (clean_subjects / total_subjects * 100) if total_subjects > 0 else 0

            # Average DQI score
            avg_dqi = DQIScoreSubject.objects.filter(
                subject__in=subjects
            ).aggregate(Avg('composite_dqi_score'))['composite_dqi_score__avg'] or 0

            # Assign risk band
            if avg_dqi < 25:
                risk_band = 'Low'
            elif avg_dqi < 50:
                risk_band = 'Medium'
            elif avg_dqi < 75:
                risk_band = 'High'
            else:
                risk_band = 'Critical'

            DQIScoreSite.objects.update_or_create(
                site=site,
                defaults={
                    'total_subjects': total_subjects,
                    'clean_subjects': clean_subjects,
                    'clean_percentage': round(clean_pct, 2),
                    'composite_dqi_score': round(avg_dqi, 2),
                    'risk_band': risk_band
                }
            )

        self.stdout.write(f'Computed DQI for {sites.count()} sites')

    def _compute_dqi_study(self, study):
        """Roll up DQI to study level."""
        self.stdout.write('Computing DQI scores (study level)...')

        sites = Site.objects.filter(study=study)
        subjects = Subject.objects.filter(study=study)

        total_sites = sites.count()
        total_subjects = subjects.count()

        clean_subjects = CleanPatientStatus.objects.filter(
            subject__in=subjects,
            is_clean=True
        ).count()

        clean_pct = (clean_subjects / total_subjects * 100) if total_subjects > 0 else 0

        # Average DQI across all subjects
        avg_dqi = DQIScoreSubject.objects.filter(
            subject__in=subjects
        ).aggregate(Avg('composite_dqi_score'))['composite_dqi_score__avg'] or 0

        # Determine readiness status
        if clean_pct >= 95:
            readiness = 'Ready for Database Lock'
        elif clean_pct >= 80:
            readiness = 'Ready for Interim Analysis'
        elif clean_pct >= 50:
            readiness = 'In Progress'
        else:
            readiness = 'Not Ready'

        DQIScoreStudy.objects.update_or_create(
            study=study,
            defaults={
                'total_sites': total_sites,
                'total_subjects': total_subjects,
                'clean_subjects': clean_subjects,
                'clean_percentage': round(clean_pct, 2),
                'composite_dqi_score': round(avg_dqi, 2),
                'readiness_status': readiness
            }
        )

        self.stdout.write(self.style.SUCCESS(f'Study {study.study_id}: {clean_pct:.1f}% clean ({readiness})'))
