"""
Management command to seed minimal smoke test data.

Creates a complete hierarchy from Study → Query to verify the schema works.

Usage:
    python manage.py seed_smoke_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.core.models import Study, Country, Site, Subject, Visit, FormPage
from apps.monitoring.models import Query, OpenIssueSummary, MissingVisit
from apps.safety.models import SAEDiscrepancy
from apps.metrics.models import CleanPatientStatus, DQIScoreSubject


class Command(BaseCommand):
    help = 'Seeds minimal smoke test data (1 of each entity) for UI verification'

    def handle(self, *args, **options):
        self.stdout.write('Seeding smoke test data...\n')

        today = timezone.now().date()

        # 1. Study
        study, _ = Study.objects.update_or_create(
            study_id='Smoke_Test_Study',
            defaults={
                'study_name': 'Smoke Test Study',
                'region': 'GLOBAL',
                'status': 'Active',
                'snapshot_date': today,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  Study: {study.study_id}'))

        # 2. Country
        country, _ = Country.objects.update_or_create(
            study=study,
            country_code='TST',
            defaults={
                'country_name': 'Test Country',
                'region': 'GLOBAL',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  Country: {country.country_name}'))

        # 3. Site
        site_id = f'{study.study_id}__SITE_001'
        site, _ = Site.objects.update_or_create(
            site_id=site_id,
            defaults={
                'study': study,
                'country': country,
                'site_number': '001',
                'site_name': 'Smoke Test Hospital',
                'status': 'Active',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  Site: {site.site_id}'))

        # 4. Subject
        subject_id = f'{study.study_id}__{site.site_number}__TEST-001'
        subject, _ = Subject.objects.update_or_create(
            subject_id=subject_id,
            defaults={
                'study': study,
                'site': site,
                'subject_external_id': 'TEST-001',
                'subject_status': 'Enrolled',
                'enrollment_date': today - timedelta(days=30),
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  Subject: {subject.subject_id}'))

        # 5. Visit
        visit, _ = Visit.objects.update_or_create(
            subject=subject,
            visit_name='Screening',
            defaults={
                'visit_date': today - timedelta(days=30),
                'projected_date': today - timedelta(days=32),
                'status': 'Completed',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  Visit: {visit.visit_name}'))

        # 6. FormPage
        form_page, _ = FormPage.objects.update_or_create(
            visit=visit,
            folder_name='SCREENING',
            form_name='Demographics',
            form_oid='DM_FORM',
            defaults={
                'page_name': 'Demographics Page 1',
                'status': 'Submitted',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  FormPage: {form_page.form_name}'))

        # 7. Query
        query, _ = Query.objects.update_or_create(
            study=study,
            site=site,
            subject=subject,
            form_name='Demographics',
            field_oid='DM.0001',
            log_number='Q-001',
            defaults={
                'page': form_page,
                'visit': visit,
                'region': country.region,
                'country_code': country.country_code,
                'site_number': site.site_number,
                'folder_name': 'SCREENING',
                'query_status': 'Open',
                'action_owner': 'Site',
                'query_open_date': today - timedelta(days=5),
                'visit_date': visit.visit_date,
                'days_since_open': 5,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  Query: {query.log_number}'))

        # 8. OpenIssueSummary
        ois, _ = OpenIssueSummary.objects.update_or_create(
            study=study,
            subject=subject,
            defaults={
                'site': site,
                'open_query_count': 1,
                'total_open_issue_count': 1,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  OpenIssueSummary: {ois.total_open_issue_count} issues'))

        # 9. MissingVisit
        missing_visit, _ = MissingVisit.objects.update_or_create(
            subject=subject,
            visit_name='Week 4',
            defaults={
                'study': study,
                'site': site,
                'projected_date': today - timedelta(days=7),
                'days_outstanding': 7,
                'is_resolved': False,
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  MissingVisit: {missing_visit.visit_name}'))

        # 10. DQI Score
        dqi, _ = DQIScoreSubject.objects.update_or_create(
            subject=subject,
            defaults={
                'composite_dqi_score': 75.0,
                'risk_band': 'Medium',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  DQI Score: {dqi.composite_dqi_score}'))

        # 11. Clean Patient Status
        cps, _ = CleanPatientStatus.objects.update_or_create(
            subject=subject,
            defaults={
                'is_clean': False,
                'has_open_queries': True,
                'open_queries_count': 1,
                'has_missing_visits': True,
                'missing_visits_count': 1,
                'blockers_json': '["Open queries", "Missing visits"]',
            }
        )
        self.stdout.write(self.style.SUCCESS(f'  CleanPatientStatus: is_clean={cps.is_clean}'))

        self.stdout.write(self.style.SUCCESS('\n✅ Smoke test data seeding complete!'))
        self.stdout.write('\nEntity counts:')
        self.stdout.write(f'  Studies: {Study.objects.count()}')
        self.stdout.write(f'  Countries: {Country.objects.count()}')
        self.stdout.write(f'  Sites: {Site.objects.count()}')
        self.stdout.write(f'  Subjects: {Subject.objects.count()}')
        self.stdout.write(f'  Visits: {Visit.objects.count()}')
        self.stdout.write(f'  FormPages: {FormPage.objects.count()}')
        self.stdout.write(f'  Queries: {Query.objects.count()}')

