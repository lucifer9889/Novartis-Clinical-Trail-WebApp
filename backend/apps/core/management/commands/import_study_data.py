"""
Management command to import clinical trial data from Excel files.

Usage:
    python manage.py import_study_data --study_id=Study_1 --data_dir=../data/study_1/

Architecture Integration:
- Excel Upload / Legacy Bridge component
- Validates data before loading into Governed Data Pods
- Triggers Validation + Workflow Engine for data quality checks

This command imports all 9 Excel files for a study:
1. CPID_EDC_Metrics (multiple sheets)
2. Visit_Projection_Tracker
3. Missing_Pages_Report
4. Missing_Lab_Name_and_Ranges
5. eSAE_Dashboard (DM + Safety sheets)
6. GlobalCodingReport_MedDRA
7. GlobalCodingReport_WHODD
8. Compiled_EDRR
9. Inactivated_Forms_Folders_Records_Report

Reference: NEST2 Project Document Section 8 (Data Integration Pipeline)
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import pandas as pd
import os
from pathlib import Path
from datetime import datetime

from apps.core.models import Study, Country, Site, Subject, Visit, FormPage
from apps.monitoring.models import Query, SDVStatus, PISignatureStatus, ProtocolDeviation, NonConformantEvent, MissingVisit, MissingPage
from apps.safety.models import LabIssue, SAEDiscrepancy
from apps.medical_coding.models import CodingItem, EDRROpenIssue, InactivatedRecord


class Command(BaseCommand):
    help = 'Import clinical trial data from Excel files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--study_id',
            type=str,
            required=True,
            help='Study ID (e.g., Study_1)'
        )
        parser.add_argument(
            '--data_dir',
            type=str,
            required=True,
            help='Directory containing Excel files'
        )
        parser.add_argument(
            '--skip_validation',
            action='store_true',
            help='Skip validation checks (use with caution)'
        )

    def handle(self, *args, **options):
        study_id = options['study_id']
        data_dir = Path(options['data_dir'])
        skip_validation = options['skip_validation']

        self.stdout.write(self.style.SUCCESS(f'\n=== Starting import for {study_id} ==='))
        self.stdout.write(f'Data directory: {data_dir}')

        # Validate directory exists
        if not data_dir.exists():
            raise CommandError(f'Data directory does not exist: {data_dir}')

        # Track statistics
        stats = {
            'studies': 0,
            'countries': 0,
            'sites': 0,
            'subjects': 0,
            'visits': 0,
            'form_pages': 0,
            'queries': 0,
            'missing_visits': 0,
            'missing_pages': 0,
            'lab_issues': 0,
            'sae_discrepancies': 0,
            'coding_items': 0,
            'errors': []
        }

        try:
            with transaction.atomic():
                # Step 1: Create/Update Study
                self.stdout.write('\n--- Step 1: Creating Study ---')
                study = self._create_study(study_id)
                stats['studies'] = 1

                # Step 2: Load CPID_EDC_Metrics (main file with multiple sheets)
                self.stdout.write('\n--- Step 2: Loading CPID_EDC_Metrics ---')
                cpid_file = self._find_file(data_dir, 'CPID_EDC_Metrics')
                if cpid_file:
                    self._load_cpid_metrics(study, cpid_file, stats)
                else:
                    self.stdout.write(self.style.WARNING('CPID_EDC_Metrics file not found'))

                # Step 3: Load Visit Projection Tracker
                self.stdout.write('\n--- Step 3: Loading Visit Projection Tracker ---')
                visit_file = self._find_file(data_dir, 'Visit_Projection_Tracker')
                if visit_file:
                    self._load_missing_visits(study, visit_file, stats)

                # Step 4: Load Missing Pages Report
                self.stdout.write('\n--- Step 4: Loading Missing Pages Report ---')
                pages_file = self._find_file(data_dir, 'Missing_Pages_Report')
                if pages_file:
                    self._load_missing_pages(study, pages_file, stats)

                # Step 5: Load Lab Issues
                self.stdout.write('\n--- Step 5: Loading Lab Issues ---')
                lab_file = self._find_file(data_dir, 'Missing_Lab')
                if lab_file:
                    self._load_lab_issues(study, lab_file, stats)

                # Step 6: Load SAE Discrepancies
                self.stdout.write('\n--- Step 6: Loading SAE Discrepancies ---')
                sae_file = self._find_file(data_dir, 'eSAE_Dashboard')
                if sae_file:
                    self._load_sae_discrepancies(study, sae_file, stats)

                # Step 7: Load Coding Items (MedDRA + WHODD)
                self.stdout.write('\n--- Step 7: Loading Coding Items ---')
                self._load_coding_items(study, data_dir, stats)

                # Step 8: Load EDRR Issues
                self.stdout.write('\n--- Step 8: Loading EDRR Issues ---')
                edrr_file = self._find_file(data_dir, 'Compiled_EDRR')
                if edrr_file:
                    self._load_edrr_issues(study, edrr_file, stats)

                # Step 9: Load Inactivated Records
                self.stdout.write('\n--- Step 9: Loading Inactivated Records ---')
                inactive_file = self._find_file(data_dir, 'Inactivated')
                if inactive_file:
                    self._load_inactivated_records(study, inactive_file, stats)

                # Step 10: Validation (if not skipped)
                if not skip_validation:
                    self.stdout.write('\n--- Step 10: Validating Data ---')
                    self._validate_data(study, stats)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\nError during import: {str(e)}'))
            stats['errors'].append(str(e))
            raise

        # Print final statistics
        self._print_statistics(stats)

    def _find_file(self, data_dir, pattern):
        """Find Excel file matching pattern."""
        for file in data_dir.glob('*.xlsx'):
            if pattern.lower() in file.name.lower():
                return file
        for file in data_dir.glob('*.xls'):
            if pattern.lower() in file.name.lower():
                return file
        return None

    def _create_study(self, study_id):
        """Create or get Study."""
        study, created = Study.objects.get_or_create(
            study_id=study_id,
            defaults={
                'study_name': f'{study_id} - Clinical Trial',
                'region': 'Multi-Regional',
                'status': 'Active',
                'snapshot_date': timezone.now().date()
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created study: {study_id}'))
        else:
            self.stdout.write(f'Study already exists: {study_id}')
        return study

    def _load_cpid_metrics(self, study, file_path, stats):
        """Load CPID_EDC_Metrics file (multiple sheets)."""
        self.stdout.write(f'Loading {file_path.name}')

        try:
            # Load Subject Level Metrics sheet
            df_subjects = pd.read_excel(file_path, sheet_name='Subject Level Metrics')
            self.stdout.write(f'Found {len(df_subjects)} subjects')

            for _, row in df_subjects.iterrows():
                # Create Site if not exists
                site_number = str(row.get('Site', 'Unknown'))
                site_id = f"{study.study_id}_{site_number}"

                # Create Country if needed
                country_code = row.get('Country', 'XX')
                country, _ = Country.objects.get_or_create(
                    study=study,
                    country_code=country_code,
                    defaults={
                        'country_name': country_code,
                        'region': row.get('Region', 'Unknown')
                    }
                )
                stats['countries'] = Country.objects.filter(study=study).count()

                # Create Site
                site, created = Site.objects.get_or_create(
                    site_id=site_id,
                    defaults={
                        'study': study,
                        'country': country,
                        'site_number': site_number,
                        'status': 'Active'
                    }
                )
                if created:
                    stats['sites'] += 1

                # Create Subject
                subject_external_id = str(row.get('Subject', 'Unknown'))
                subject_id = f"{study.study_id}_{subject_external_id}"

                subject, created = Subject.objects.get_or_create(
                    subject_id=subject_id,
                    defaults={
                        'study': study,
                        'site': site,
                        'subject_external_id': subject_external_id,
                        'subject_status': row.get('Subject Status', 'Enrolled'),
                        'enrollment_date': pd.to_datetime(row.get('Enrollment Date'), errors='coerce')
                    }
                )
                if created:
                    stats['subjects'] += 1

            # Load Query Report sheet
            try:
                df_queries = pd.read_excel(file_path, sheet_name='Query Report - Cumulative')
                self._load_queries(study, df_queries, stats)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Could not load queries: {e}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading CPID_EDC_Metrics: {e}'))
            stats['errors'].append(f'CPID_EDC_Metrics: {e}')

    def _load_queries(self, study, df, stats):
        """Load queries from dataframe."""
        self.stdout.write(f'Loading {len(df)} queries')

        for _, row in df.iterrows():
            try:
                # Find subject
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                # Create query
                Query.objects.get_or_create(
                    subject=subject,
                    log_number=str(row.get('Log Number', '')),
                    defaults={
                        'form_name': row.get('Form Name', ''),
                        'field_oid': row.get('Field OID', ''),
                        'query_status': row.get('Query Status', 'Open'),
                        'action_owner': row.get('Action Owner', 'Site'),
                        'query_open_date': pd.to_datetime(row.get('Query Open Date'), errors='coerce') or timezone.now().date(),
                        'days_since_open': int(row.get('Days Since Open', 0))
                    }
                )
                stats['queries'] += 1
            except Exception as e:
                stats['errors'].append(f'Query row error: {e}')

    def _load_missing_visits(self, study, file_path, stats):
        """Load missing visits from Visit Projection Tracker."""
        self.stdout.write(f'Loading {file_path.name}')

        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f'Found {len(df)} missing visits')

            for _, row in df.iterrows():
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                MissingVisit.objects.get_or_create(
                    subject=subject,
                    visit_name=row.get('Visit Name', 'Unknown'),
                    defaults={
                        'projected_date': pd.to_datetime(row.get('Projected Date'), errors='coerce') or timezone.now().date(),
                        'days_outstanding': int(row.get('Days Outstanding', 0))
                    }
                )
                stats['missing_visits'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading missing visits: {e}'))
            stats['errors'].append(f'Missing visits: {e}')

    def _load_missing_pages(self, study, file_path, stats):
        """Load missing pages."""
        self.stdout.write(f'Loading {file_path.name}')

        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f'Found {len(df)} missing pages')

            for _, row in df.iterrows():
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                MissingPage.objects.get_or_create(
                    subject=subject,
                    visit_name=row.get('Visit Name', 'Unknown'),
                    page_name=row.get('Page Name', 'Unknown'),
                    defaults={
                        'visit_date': pd.to_datetime(row.get('Visit Date'), errors='coerce'),
                        'days_missing': int(row.get('Days Missing', 0))
                    }
                )
                stats['missing_pages'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading missing pages: {e}'))
            stats['errors'].append(f'Missing pages: {e}')

    def _load_lab_issues(self, study, file_path, stats):
        """Load lab issues."""
        self.stdout.write(f'Loading {file_path.name}')

        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f'Found {len(df)} lab issues')

            for _, row in df.iterrows():
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                LabIssue.objects.create(
                    subject=subject,
                    visit_name=row.get('Visit', 'Unknown'),
                    form_name=row.get('Form', 'Unknown'),
                    lab_category=row.get('Lab Category', 'Unknown'),
                    test_name=row.get('Test Name', 'Unknown'),
                    issue=row.get('Issue Type', 'Missing Lab Name')
                )
                stats['lab_issues'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading lab issues: {e}'))
            stats['errors'].append(f'Lab issues: {e}')

    def _load_sae_discrepancies(self, study, file_path, stats):
        """Load SAE discrepancies."""
        self.stdout.write(f'Loading {file_path.name}')

        try:
            # Try DM sheet first
            df = pd.read_excel(file_path, sheet_name='SAE Dashboard_DM')
            self.stdout.write(f'Found {len(df)} SAE discrepancies')

            for _, row in df.iterrows():
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                SAEDiscrepancy.objects.get_or_create(
                    subject=subject,
                    discrepancy_id=str(row.get('Discrepancy ID', '')),
                    defaults={
                        'study': study,
                        'site': subject.site,
                        'review_status_dm': row.get('Review Status', ''),
                        'action_status_dm': row.get('Action Status', ''),
                        'discrepancy_created_timestamp': pd.to_datetime(row.get('Created Date'), errors='coerce') or timezone.now()
                    }
                )
                stats['sae_discrepancies'] += 1

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error loading SAE discrepancies: {e}'))
            stats['errors'].append(f'SAE discrepancies: {e}')

    def _load_coding_items(self, study, data_dir, stats):
        """Load MedDRA and WHODD coding items."""
        # Load MedDRA
        meddra_file = self._find_file(data_dir, 'MedDRA')
        if meddra_file:
            self._load_coding_file(study, meddra_file, 'MedDRA', stats)

        # Load WHODD
        whodd_file = self._find_file(data_dir, 'WHODD')
        if whodd_file:
            self._load_coding_file(study, whodd_file, 'WHODD', stats)

    def _load_coding_file(self, study, file_path, dictionary, stats):
        """Load coding items from file."""
        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f'Loading {len(df)} {dictionary} coding items')

            for _, row in df.iterrows():
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                CodingItem.objects.create(
                    subject=subject,
                    study=study,
                    dictionary_name=dictionary,
                    form_oid=row.get('Form OID', 'Unknown'),
                    coding_status=row.get('Coding Status', 'Uncoded')
                )
                stats['coding_items'] += 1

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not load {dictionary}: {e}'))

    def _load_edrr_issues(self, study, file_path, stats):
        """Load EDRR open issues."""
        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f'Found {len(df)} EDRR issues')

            for _, row in df.iterrows():
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                EDRROpenIssue.objects.get_or_create(
                    study=study,
                    subject=subject,
                    defaults={
                        'total_open_issue_count': int(row.get('Open Issue Count', 0))
                    }
                )

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not load EDRR: {e}'))

    def _load_inactivated_records(self, study, file_path, stats):
        """Load inactivated records."""
        try:
            df = pd.read_excel(file_path)
            self.stdout.write(f'Found {len(df)} inactivated records')

            for _, row in df.iterrows():
                subject_external_id = str(row.get('Subject', ''))
                subject = Subject.objects.filter(
                    study=study,
                    subject_external_id=subject_external_id
                ).first()

                if not subject:
                    continue

                InactivatedRecord.objects.create(
                    subject=subject,
                    form_name=row.get('Form Name', 'Unknown'),
                    audit_action=row.get('Audit Action', 'Inactivated')
                )

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not load inactivated records: {e}'))

    def _validate_data(self, study, stats):
        """Validate imported data."""
        self.stdout.write('Validating data integrity...')

        # Check subject count
        subject_count = Subject.objects.filter(study=study).count()
        self.stdout.write(f'Total subjects: {subject_count}')

        if subject_count == 0:
            raise CommandError('No subjects imported!')

        # Check for orphaned records
        queries_without_subject = Query.objects.filter(subject__isnull=True).count()
        if queries_without_subject > 0:
            self.stdout.write(self.style.WARNING(f'Found {queries_without_subject} queries without subject'))

    def _print_statistics(self, stats):
        """Print import statistics."""
        self.stdout.write(self.style.SUCCESS('\n=== Import Complete ==='))
        self.stdout.write(f"Studies: {stats['studies']}")
        self.stdout.write(f"Countries: {stats['countries']}")
        self.stdout.write(f"Sites: {stats['sites']}")
        self.stdout.write(f"Subjects: {stats['subjects']}")
        self.stdout.write(f"Queries: {stats['queries']}")
        self.stdout.write(f"Missing Visits: {stats['missing_visits']}")
        self.stdout.write(f"Missing Pages: {stats['missing_pages']}")
        self.stdout.write(f"Lab Issues: {stats['lab_issues']}")
        self.stdout.write(f"SAE Discrepancies: {stats['sae_discrepancies']}")
        self.stdout.write(f"Coding Items: {stats['coding_items']}")

        if stats['errors']:
            self.stdout.write(self.style.WARNING(f"\nErrors encountered: {len(stats['errors'])}"))
            for error in stats['errors'][:5]:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
