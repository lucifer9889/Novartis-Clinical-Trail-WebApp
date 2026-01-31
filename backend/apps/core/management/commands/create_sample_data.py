"""
Management command to create sample data for demo.

Usage:
    python manage.py create_sample_data
"""

from django.core.management.base import BaseCommand
from apps.core.models import Study, Country, Site, Subject
from apps.monitoring.models import Query, MissingVisit, MissingPage
from apps.metrics.models import (
    DQIScoreStudy, DQIScoreSite, DQIScoreSubject,
    CleanPatientStatus, DQIWeightConfig
)
from apps.blockchain.models import BlockchainTransaction
from apps.blockchain.services import BlockchainService
from django.utils import timezone
from decimal import Decimal
import random
import hashlib
import json


class Command(BaseCommand):
    help = 'Create sample data for demo'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...\n')

        # 1. Create DQI Weights
        self._create_dqi_weights()

        # 2. Create Study
        study = self._create_study()

        # 3. Create Countries
        countries = self._create_countries(study)

        # 4. Create Sites
        sites = self._create_sites(study, countries)

        # 5. Create Subjects with related data
        subjects_created = self._create_subjects(study, sites)

        # 6. Create Site DQI Scores
        self._create_site_dqi(sites)

        # 7. Create Study DQI Score
        self._create_study_dqi(study, sites)

        # 8. Record blockchain events
        self._create_blockchain_events(study)

        self.stdout.write(self.style.SUCCESS(
            f'\nSample data creation complete!\n'
            f'  Subjects: {Subject.objects.filter(study=study).count()}\n'
            f'  Sites: {Site.objects.filter(study=study).count()}\n'
            f'  Queries: {Query.objects.count()}\n'
            f'  Missing Visits: {MissingVisit.objects.count()}\n'
            f'  Missing Pages: {MissingPage.objects.count()}\n'
            f'  Blockchain Blocks: {BlockchainTransaction.objects.count()}\n'
        ))

    def _create_dqi_weights(self):
        """Create DQI weight configuration entries."""
        weights = [
            ('sae_unresolved_count', Decimal('0.250'), 'SAE unresolved discrepancies'),
            ('missing_visits_days_overdue', Decimal('0.150'), 'Missing visits days overdue'),
            ('open_queries_count', Decimal('0.150'), 'Open queries count'),
            ('missing_pages_count', Decimal('0.100'), 'Missing pages count'),
            ('non_conformant_count', Decimal('0.100'), 'Non-conformant events'),
            ('sdv_incomplete_pct', Decimal('0.100'), 'SDV incomplete percentage'),
            ('pi_signature_incomplete_pct', Decimal('0.050'), 'PI signature incomplete'),
            ('coding_uncoded_count', Decimal('0.050'), 'Coding backlog'),
            ('edrr_open_issue_count', Decimal('0.050'), 'EDRR open issues'),
        ]
        for metric_name, weight, desc in weights:
            DQIWeightConfig.objects.get_or_create(
                metric_name=metric_name,
                defaults={'weight': weight, 'description': desc}
            )
        self.stdout.write('  [OK] DQI weights created')

    def _create_study(self):
        """Create study."""
        study, _ = Study.objects.get_or_create(
            study_id='Study_1',
            defaults={
                'study_name': 'Phase 3 Clinical Trial - Oncology',
                'region': 'Global',
                'status': 'Active',
                'snapshot_date': timezone.now().date()
            }
        )
        self.stdout.write('  [OK] Study created')
        return study

    def _create_countries(self, study):
        """Create countries."""
        countries_data = [
            ('USA', 'United States', 'North America'),
            ('CAN', 'Canada', 'North America'),
            ('GBR', 'United Kingdom', 'Europe'),
            ('DEU', 'Germany', 'Europe'),
            ('IND', 'India', 'APAC'),
        ]
        countries = []
        for code, name, region in countries_data:
            country, _ = Country.objects.get_or_create(
                study=study,
                country_code=code,
                defaults={'country_name': name, 'region': region}
            )
            countries.append(country)
        self.stdout.write(f'  [OK] {len(countries)} countries created')
        return countries

    def _create_sites(self, study, countries):
        """Create sites across countries."""
        sites = []
        site_idx = 1
        for country in countries:
            num_sites = 2 if country.country_code in ('USA', 'IND') else 1
            for j in range(num_sites):
                site_num = f'{site_idx:03d}'
                site_id = f'Study_1_{site_num}'
                site, _ = Site.objects.get_or_create(
                    site_id=site_id,
                    defaults={
                        'site_number': site_num,
                        'site_name': f'{country.country_name} Medical Center {j+1}',
                        'country': country,
                        'study': study,
                        'status': 'Active'
                    }
                )
                sites.append(site)
                site_idx += 1
        self.stdout.write(f'  [OK] {len(sites)} sites created')
        return sites

    def _create_subjects(self, study, sites):
        """Create subjects with queries, missing visits, missing pages, DQI, and clean status."""
        subjects_created = 0
        visit_names = ['Screening', 'Baseline', 'Week 2', 'Week 4', 'Week 8',
                       'Week 12', 'Week 16', 'Week 20', 'Week 24', 'End of Study']
        page_names = ['Demographics', 'Vital Signs', 'Lab Results', 'Adverse Events',
                      'Concomitant Meds', 'ECG Results', 'Physical Exam', 'Medical History']
        form_names = ['DM_Form', 'VS_Form', 'LB_Form', 'AE_Form',
                      'CM_Form', 'EG_Form', 'PE_Form', 'MH_Form']

        for site in sites:
            num_subjects = random.randint(12, 16)
            for j in range(1, num_subjects + 1):
                subject_id = f'Study_1_{site.site_number}-{j:03d}'
                ext_id = f'{site.site_number}-{j:03d}'

                days_ago = random.randint(30, 365)
                enroll_date = (timezone.now() - timezone.timedelta(days=days_ago)).date()

                subject, created = Subject.objects.get_or_create(
                    subject_id=subject_id,
                    defaults={
                        'subject_external_id': ext_id,
                        'subject_status': random.choice(['Enrolled', 'Enrolled', 'Active', 'Completed']),
                        'enrollment_date': enroll_date,
                        'site': site,
                        'study': study
                    }
                )

                if not created:
                    continue

                subjects_created += 1

                # --- Queries ---
                open_q_count = 0
                if random.random() > 0.35:
                    num_queries = random.randint(1, 8)
                    for q in range(num_queries):
                        q_status = random.choice(['Open', 'Open', 'Closed', 'Answered'])
                        if q_status == 'Open':
                            open_q_count += 1
                        q_open_date = (timezone.now() - timezone.timedelta(
                            days=random.randint(1, 90))).date()
                        Query.objects.create(
                            subject=subject,
                            log_number=f'Q{random.randint(1000, 9999)}',
                            form_name=random.choice(form_names),
                            query_status=q_status,
                            query_open_date=q_open_date,
                            days_since_open=random.randint(1, 60),
                            action_owner=random.choice(['Site', 'CRA', 'DM']),
                        )

                # --- Missing Visits ---
                mv_count = 0
                if random.random() > 0.80:
                    num_mv = random.randint(1, 2)
                    for _ in range(num_mv):
                        vname = random.choice(visit_names)
                        obj, was_created = MissingVisit.objects.get_or_create(
                            subject=subject,
                            visit_name=vname,
                            defaults={
                                'projected_date': (timezone.now() - timezone.timedelta(
                                    days=random.randint(5, 60))).date(),
                                'days_outstanding': random.randint(1, 30),
                            }
                        )
                        if was_created:
                            mv_count += 1

                # --- Missing Pages ---
                mp_count = 0
                if random.random() > 0.65:
                    num_mp = random.randint(1, 5)
                    for _ in range(num_mp):
                        MissingPage.objects.create(
                            subject=subject,
                            visit_name=random.choice(visit_names),
                            page_name=random.choice(page_names),
                            days_missing=random.randint(1, 45),
                        )
                        mp_count += 1

                # --- DQI Score ---
                dqi_score = Decimal(str(round(random.uniform(10.0, 55.0), 2)))
                if dqi_score < 25:
                    risk_band = 'Low'
                elif dqi_score < 40:
                    risk_band = 'Medium'
                elif dqi_score < 55:
                    risk_band = 'High'
                else:
                    risk_band = 'Critical'

                DQIScoreSubject.objects.get_or_create(
                    subject=subject,
                    defaults={
                        'composite_dqi_score': dqi_score,
                        'risk_band': risk_band,
                        'open_queries_score': Decimal(str(round(open_q_count * 8.0, 2))),
                        'missing_visits_score': Decimal(str(round(mv_count * 15.0, 2))),
                        'missing_pages_score': Decimal(str(round(mp_count * 5.0, 2))),
                    }
                )

                # --- Clean Patient Status ---
                is_clean = (open_q_count == 0 and mv_count == 0 and mp_count == 0
                            and random.random() > 0.3)

                CleanPatientStatus.objects.get_or_create(
                    subject=subject,
                    defaults={
                        'is_clean': is_clean,
                        'has_open_queries': open_q_count > 0,
                        'open_queries_count': open_q_count,
                        'has_missing_visits': mv_count > 0,
                        'missing_visits_count': mv_count,
                        'has_missing_pages': mp_count > 0,
                        'missing_pages_count': mp_count,
                        'sdv_completion_pct': Decimal(str(random.randint(60, 100))),
                        'sdv_incomplete': random.random() > 0.7,
                        'pi_signature_completion_pct': Decimal(str(random.randint(50, 100))),
                        'pi_signature_incomplete': random.random() > 0.7,
                    }
                )

        self.stdout.write(f'  [OK] {subjects_created} subjects created with related data')
        return subjects_created

    def _create_site_dqi(self, sites):
        """Create DQI scores at site level."""
        for site in sites:
            total = Subject.objects.filter(site=site).count()
            clean = CleanPatientStatus.objects.filter(
                subject__site=site, is_clean=True
            ).count()
            if total > 0:
                clean_pct = Decimal(str(round((clean / total) * 100, 2)))
                dqi = Decimal(str(round(random.uniform(18.0, 40.0), 2)))
                DQIScoreSite.objects.get_or_create(
                    site=site,
                    defaults={
                        'total_subjects': total,
                        'clean_subjects': clean,
                        'clean_percentage': clean_pct,
                        'composite_dqi_score': dqi,
                    }
                )
        self.stdout.write(f'  [OK] Site DQI scores created')

    def _create_study_dqi(self, study, sites):
        """Create DQI score at study level."""
        total_subjects = Subject.objects.filter(study=study).count()
        clean_subjects = CleanPatientStatus.objects.filter(
            subject__study=study, is_clean=True
        ).count()
        clean_pct = Decimal(str(round(
            (clean_subjects / total_subjects) * 100, 2
        ))) if total_subjects > 0 else Decimal('0')

        DQIScoreStudy.objects.get_or_create(
            study=study,
            defaults={
                'total_sites': len(sites),
                'total_subjects': total_subjects,
                'clean_subjects': clean_subjects,
                'clean_percentage': clean_pct,
                'composite_dqi_score': Decimal('27.45'),
                'readiness_status': 'In Progress'
            }
        )
        self.stdout.write(f'  [OK] Study DQI score created ({clean_subjects}/{total_subjects} clean)')

    def _create_blockchain_events(self, study):
        """Record sample blockchain events."""
        try:
            service = BlockchainService()

            # Record DQI computation event
            service.record_dqi_computation(study.study_id, {
                'total_subjects': Subject.objects.filter(study=study).count(),
                'clean_percentage': float(CleanPatientStatus.objects.filter(
                    subject__study=study, is_clean=True).count()),
                'composite_dqi_score': 27.45
            })

            # Record a few clean status updates
            clean_statuses = CleanPatientStatus.objects.filter(
                subject__study=study
            ).select_related('subject')[:5]
            for cs in clean_statuses:
                service.record_clean_status_update(
                    cs.subject.subject_id,
                    {
                        'is_clean': cs.is_clean,
                        'blockers': [],
                        'dqi_score': 0
                    }
                )

            self.stdout.write(f'  [OK] Blockchain events recorded')
        except Exception as e:
            self.stdout.write(f'  [!] Blockchain events skipped: {e}')
