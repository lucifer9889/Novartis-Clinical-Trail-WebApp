"""
Management command to load Study-1 real data from Excel files.

This command replaces sample data with REAL Study-1 data from multiple Excel reports.

Usage:
    python manage.py load_study1 --data_dir ./data/study1 --dry-run    # Parse only, no writes
    python manage.py load_study1 --data_dir ./data/study1 --wipe       # Wipe Study-1 data, then load
    python manage.py load_study1 --data_dir ./data/study1              # Idempotent upsert

Data Sources:
    1. Study 1_CPID_EDC_Metrics_URSV2.0_14 NOV 2025_updated.xlsx
       - Subject Level Metrics (102 rows)
       - Query Report - Cumulative (574 rows)
       - Query Report - Site Action (388 rows)
       - Query Report - CRA Action (26 rows)
       - Non conformant (12 rows)
       - PI Signature Report (1167 rows)
       - SDV (7351 rows)
       - Protocol Deviation (15 rows)
       - CRF Freeze/UnFreeze/Locked/UnLocked
    2. Study 1_Compiled_EDRR_updated.xlsx (28 rows)
    3. Study 1_eSAE Dashboard_Standard DM_Safety Report_updated.xlsx
       - SAE Dashboard_DM (700 rows)
       - SAE Dashboard_Safety (574 rows)
    4. Study 1_GlobalCodingReport_MedDRA_updated.xlsx (1513 rows)
    5. Study 1_GlobalCodingReport_WHODD_updated.xlsx (1573 rows)
    6. Study 1_Inactivated Forms, Folders and Records Report_updated.xlsx (5607 rows)
    7. Study 1_Missing_Lab_Name_and_Missing_Ranges_14NOV2025_updated.xlsx (128 rows)
    8. Study 1_Missing_Pages_Report_URSV3.0_14 NOV 2025_updated.xlsx (193 rows)
    9. Study 1_Visit Projection Tracker_14NOV2025_updated.xlsx (15 rows)

ID Rules:
    - country_code: 3-letter code from Excel (AUT, FRA, USA, etc.)
    - site_id: "Study_1_{site_number}" where site_number is extracted integer
    - subject_id: "Study_1_{subject_external_id}" 
    - Deterministic IDs ensure reruns don't duplicate

Architecture: Excel Upload / Legacy Bridge → Validation → Governed Data Pods
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import logging
import re

from apps.core.models import Study, Country, Site, Subject, Visit, FormPage
from apps.monitoring.models import (
    Query, SDVStatus, PISignatureStatus, ProtocolDeviation, 
    NonConformantEvent, MissingVisit, MissingPage
)
from apps.safety.models import LabIssue, SAEDiscrepancy
from apps.medical_coding.models import CodingItem, EDRROpenIssue, InactivatedRecord


# Country code to name mapping (pycountry fallback)
COUNTRY_NAMES = {
    'AUT': 'Austria', 'CHN': 'China', 'CZE': 'Czech Republic',
    'DEU': 'Germany', 'ESP': 'Spain', 'FRA': 'France',
    'GBR': 'United Kingdom', 'ISR': 'Israel', 'KOR': 'South Korea',
    'SGP': 'Singapore', 'USA': 'United States', 'IND': 'India',
    'JPN': 'Japan', 'AUS': 'Australia', 'CAN': 'Canada',
}


class Command(BaseCommand):
    """Load Study-1 data from Excel files with dry-run, wipe, and upsert options."""
    
    help = 'Load Study-1 real data from Excel files'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {}
        self.rejected_rows = []
        self.logger = None
        self.dry_run = False
        self.study = None

    def add_arguments(self, parser):
        parser.add_argument(
            '--data_dir',
            type=str,
            default='./data/study1',
            help='Directory containing Study-1 Excel files (default: ./data/study1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate only, do not write to database'
        )
        parser.add_argument(
            '--wipe',
            action='store_true',
            help='Delete all Study-1 data before loading (safe FK order)'
        )
        parser.add_argument(
            '--log-dir',
            type=str,
            default='./logs',
            help='Directory for log files (default: ./logs)'
        )

    def handle(self, *args, **options):
        """Main entry point for the command."""
        data_dir = Path(options['data_dir'])
        self.dry_run = options['dry_run']
        wipe = options['wipe']
        log_dir = Path(options['log_dir'])
        
        # Setup logging
        self._setup_logging(log_dir)
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('STUDY-1 DATA LOADER'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Data directory: {data_dir.absolute()}')
        self.stdout.write(f'Mode: {"DRY-RUN (no writes)" if self.dry_run else "WIPE + LOAD" if wipe else "UPSERT"}')
        
        # Initialize statistics
        self._init_stats()
        
        # Validate data directory
        if not data_dir.exists():
            self._log_error(f'Data directory not found: {data_dir}')
            self._print_file_instructions()
            raise CommandError(f'Data directory does not exist: {data_dir}')
        
        # Check for required files
        required_files = self._check_required_files(data_dir)
        if not required_files['all_found']:
            self._log_error('Missing required Excel files')
            self._print_file_instructions()
            raise CommandError('Required files missing. See above for instructions.')
        
        try:
            if self.dry_run:
                # Dry-run mode: parse and validate only
                self._parse_and_validate(data_dir)
            else:
                with transaction.atomic():
                    # Wipe mode: delete existing Study-1 data first
                    if wipe:
                        self._wipe_study1_data()
                    
                    # Load data
                    self._load_all_data(data_dir)
                    
                    # Validate after load
                    self._validate_data()
        
        except Exception as e:
            self._log_error(f'Fatal error: {str(e)}')
            raise
        
        finally:
            # Print final statistics
            self._print_statistics()
            self._log_info('Load complete')

    def _setup_logging(self, log_dir):
        """Setup file logging for the load operation."""
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'study1_load_{timestamp}.log'
        
        self.logger = logging.getLogger('study1_loader')
        self.logger.setLevel(logging.DEBUG)
        
        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        
        self._log_info(f'Logging to: {log_file}')
        self.stdout.write(f'Log file: {log_file}')

    def _log_info(self, msg):
        """Log info message."""
        if self.logger:
            self.logger.info(msg)

    def _log_error(self, msg):
        """Log error message."""
        if self.logger:
            self.logger.error(msg)
        self.stdout.write(self.style.ERROR(msg))

    def _log_warning(self, msg):
        """Log warning message."""
        if self.logger:
            self.logger.warning(msg)
        self.stdout.write(self.style.WARNING(msg))

    def _init_stats(self):
        """Initialize statistics dictionary."""
        self.stats = {
            'countries': 0,
            'sites': 0,
            'subjects': 0,
            'visits': 0,
            'form_pages': 0,
            'queries': 0,
            'sdv_records': 0,
            'pi_signatures': 0,
            'protocol_deviations': 0,
            'nonconformant_events': 0,
            'missing_visits': 0,
            'missing_pages': 0,
            'lab_issues': 0,
            'sae_discrepancies': 0,
            'coding_items': 0,
            'edrr_issues': 0,
            'inactivated_records': 0,
            'crf_events': 0,
            'errors': 0,
        }
        self.rejected_rows = []

    def _check_required_files(self, data_dir):
        """Check that all required Excel files exist."""
        required_patterns = [
            'CPID_EDC_Metrics',
            'Compiled_EDRR',
            'eSAE Dashboard',
            'GlobalCodingReport_MedDRA',
            'GlobalCodingReport_WHODD',
            'Inactivated',
            'Missing_Lab',
            'Missing_Pages',
            'Visit Projection',
        ]
        
        result = {'all_found': True, 'found': [], 'missing': []}
        
        for pattern in required_patterns:
            found = self._find_file(data_dir, pattern)
            if found:
                result['found'].append((pattern, found.name))
                self.stdout.write(self.style.SUCCESS(f'✓ Found: {found.name}'))
            else:
                result['missing'].append(pattern)
                result['all_found'] = False
                self.stdout.write(self.style.ERROR(f'✗ Missing: {pattern}*.xlsx'))
        
        return result

    def _find_file(self, data_dir, pattern):
        """Find Excel file matching pattern (case-insensitive)."""
        for file in data_dir.glob('*.xlsx'):
            if pattern.lower().replace('_', ' ') in file.name.lower().replace('_', ' '):
                return file
        for file in data_dir.glob('*.xlsx'):
            if pattern.lower().replace('_', '') in file.name.lower().replace('_', '').replace(' ', ''):
                return file
        return None

    def _print_file_instructions(self):
        """Print instructions for copying files."""
        self.stdout.write(self.style.ERROR('\n' + '=' * 60))
        self.stdout.write(self.style.ERROR('MISSING FILE INSTRUCTIONS'))
        self.stdout.write(self.style.ERROR('=' * 60))
        self.stdout.write('''
Please copy the Study-1 Excel files to: ./data/study1/

Required files:
1. Study 1_CPID_EDC_Metrics_URSV2.0_14 NOV 2025_updated.xlsx
2. Study 1_Compiled_EDRR_updated.xlsx
3. Study 1_eSAE Dashboard_Standard DM_Safety Report_updated.xlsx
4. Study 1_GlobalCodingReport_MedDRA_updated.xlsx
5. Study 1_GlobalCodingReport_WHODD_updated.xlsx
6. Study 1_Inactivated Forms, Folders and Records Report_updated.xlsx
7. Study 1_Missing_Lab_Name_and_Missing_Ranges_14NOV2025_updated.xlsx
8. Study 1_Missing_Pages_Report_URSV3.0_14 NOV 2025_updated.xlsx
9. Study 1_Visit Projection Tracker_14NOV2025_updated.xlsx

These files should be in the original Novartis dataset folder:
  6932c39b908b6_detailed_problem_statements_and_datasets/
  Data_files/QC Anonymized Study Files/Study 1_CPID_Input Files - Anonymization/
''')

    def _wipe_study1_data(self):
        """Delete all Study-1 related data in safe FK order."""
        self.stdout.write('\n--- Wiping Study-1 Data ---')
        self._log_info('Wiping Study-1 data...')
        
        study_id = 'Study_1'
        
        # Delete in FK-safe order (children before parents)
        # Fact tables first
        InactivatedRecord.objects.filter(subject__study_id=study_id).delete()
        CodingItem.objects.filter(study_id=study_id).delete()
        EDRROpenIssue.objects.filter(study_id=study_id).delete()
        SAEDiscrepancy.objects.filter(study_id=study_id).delete()
        LabIssue.objects.filter(subject__study_id=study_id).delete()
        MissingPage.objects.filter(subject__study_id=study_id).delete()
        MissingVisit.objects.filter(subject__study_id=study_id).delete()
        NonConformantEvent.objects.filter(subject__study_id=study_id).delete()
        ProtocolDeviation.objects.filter(study_id=study_id).delete()
        PISignatureStatus.objects.filter(study_id=study_id).delete()
        SDVStatus.objects.filter(study_id=study_id).delete()
        Query.objects.filter(subject__study_id=study_id).delete()
        
        # Dimension tables (form_pages -> visits -> subjects -> sites -> countries)
        FormPage.objects.filter(visit__subject__study_id=study_id).delete()
        Visit.objects.filter(subject__study_id=study_id).delete()
        Subject.objects.filter(study_id=study_id).delete()
        Site.objects.filter(study_id=study_id).delete()
        Country.objects.filter(study_id=study_id).delete()
        
        # Study itself (optional - keep or delete)
        # Study.objects.filter(study_id=study_id).delete()
        
        self.stdout.write(self.style.SUCCESS('Study-1 data wiped'))
        self._log_info('Study-1 data wiped successfully')

    def _parse_and_validate(self, data_dir):
        """Dry-run: parse all files and report counts without writing."""
        self.stdout.write('\n--- DRY-RUN: Parsing and Validating ---')
        self._log_info('Starting dry-run parsing...')
        
        # Parse CPID_EDC_Metrics
        cpid_file = self._find_file(data_dir, 'CPID_EDC_Metrics')
        if cpid_file:
            self._parse_cpid_metrics(cpid_file)
        
        # Parse other files
        for pattern, parser in [
            ('Compiled_EDRR', self._parse_edrr),
            ('eSAE Dashboard', self._parse_sae),
            ('GlobalCodingReport_MedDRA', lambda f: self._parse_coding(f, 'MedDRA')),
            ('GlobalCodingReport_WHODD', lambda f: self._parse_coding(f, 'WHODD')),
            ('Inactivated', self._parse_inactivated),
            ('Missing_Lab', self._parse_lab_issues),
            ('Missing_Pages', self._parse_missing_pages),
            ('Visit Projection', self._parse_missing_visits),
        ]:
            file = self._find_file(data_dir, pattern)
            if file:
                try:
                    parser(file)
                except Exception as e:
                    self._log_error(f'Error parsing {pattern}: {e}')

    def _load_all_data(self, data_dir):
        """Load all data from Excel files."""
        self.stdout.write('\n--- Loading Study-1 Data ---')
        self._log_info('Starting data load...')
        
        # Step 1: Create Study
        self.study = self._create_study()
        
        # Step 2: Load CPID_EDC_Metrics (main file - creates subjects, queries, etc.)
        cpid_file = self._find_file(data_dir, 'CPID_EDC_Metrics')
        if cpid_file:
            self._load_cpid_metrics(cpid_file)
        
        # Step 3: Load other files
        files_to_load = [
            ('Compiled_EDRR', self._load_edrr),
            ('eSAE Dashboard', self._load_sae),
            ('GlobalCodingReport_MedDRA', lambda f: self._load_coding(f, 'MedDRA')),
            ('GlobalCodingReport_WHODD', lambda f: self._load_coding(f, 'WHODD')),
            ('Inactivated', self._load_inactivated),
            ('Missing_Lab', self._load_lab_issues),
            ('Missing_Pages', self._load_missing_pages),
            ('Visit Projection', self._load_missing_visits),
        ]
        
        for pattern, loader in files_to_load:
            file = self._find_file(data_dir, pattern)
            if file:
                self.stdout.write(f'\nLoading {file.name}...')
                try:
                    loader(file)
                except Exception as e:
                    self._log_error(f'Error loading {pattern}: {e}')
                    self.stats['errors'] += 1

    def _create_study(self):
        """Create or get Study_1."""
        study, created = Study.objects.update_or_create(
            study_id='Study_1',
            defaults={
                'study_name': 'Study 1 - Clinical Trial',
                'region': 'Multi-Regional',
                'status': 'Active',
                'snapshot_date': timezone.now().date()
            }
        )
        self._log_info(f'Study {"created" if created else "updated"}: Study_1')
        return study

    def _parse_cpid_metrics(self, file_path):
        """Parse CPID_EDC_Metrics file (dry-run)."""
        self.stdout.write(f'\nParsing {file_path.name}...')
        
        # Subject Level Metrics
        df = pd.read_excel(file_path, sheet_name='Subject Level Metrics')
        df = df.dropna(subset=['Subject ID'])
        self.stdout.write(f'  Subject Level Metrics: {len(df)} rows')
        self.stats['subjects'] = len(df)
        
        # Unique countries and sites
        countries = df['Country'].dropna().unique()
        sites = df['Site ID'].dropna().unique()
        self.stats['countries'] = len(countries)
        self.stats['sites'] = len(sites)
        self.stdout.write(f'  Countries: {len(countries)}, Sites: {len(sites)}')
        
        # Query Report - Cumulative
        try:
            df_q = pd.read_excel(file_path, sheet_name='Query Report - Cumulative')
            self.stats['queries'] = len(df_q)
            self.stdout.write(f'  Query Report - Cumulative: {len(df_q)} rows')
        except Exception as e:
            self._log_warning(f'Could not parse Query Report: {e}')
        
        # SDV
        try:
            df_sdv = pd.read_excel(file_path, sheet_name='SDV')
            self.stats['sdv_records'] = len(df_sdv)
            self.stdout.write(f'  SDV: {len(df_sdv)} rows')
        except Exception as e:
            self._log_warning(f'Could not parse SDV: {e}')
        
        # PI Signature
        try:
            df_pi = pd.read_excel(file_path, sheet_name='PI Signature Report')
            self.stats['pi_signatures'] = len(df_pi)
            self.stdout.write(f'  PI Signature Report: {len(df_pi)} rows')
        except Exception as e:
            self._log_warning(f'Could not parse PI Signature: {e}')
        
        # Protocol Deviation
        try:
            df_pd = pd.read_excel(file_path, sheet_name='Protocol Deviation')
            self.stats['protocol_deviations'] = len(df_pd)
            self.stdout.write(f'  Protocol Deviation: {len(df_pd)} rows')
        except Exception as e:
            self._log_warning(f'Could not parse Protocol Deviation: {e}')
        
        # Non conformant
        try:
            df_nc = pd.read_excel(file_path, sheet_name='Non conformant')
            self.stats['nonconformant_events'] = len(df_nc)
            self.stdout.write(f'  Non conformant: {len(df_nc)} rows')
        except Exception as e:
            self._log_warning(f'Could not parse Non conformant: {e}')

    def _parse_edrr(self, file_path):
        """Parse EDRR file (dry-run)."""
        df = pd.read_excel(file_path, sheet_name='OpenIssuesSummary')
        self.stats['edrr_issues'] = len(df)
        self.stdout.write(f'  EDRR OpenIssuesSummary: {len(df)} rows')

    def _parse_sae(self, file_path):
        """Parse SAE Dashboard file (dry-run)."""
        try:
            df_dm = pd.read_excel(file_path, sheet_name='SAE Dashboard_DM')
            df_safety = pd.read_excel(file_path, sheet_name='SAE Dashboard_Safety')
            total = len(df_dm) + len(df_safety)
            self.stats['sae_discrepancies'] = total
            self.stdout.write(f'  SAE Dashboard (DM + Safety): {total} rows')
        except Exception as e:
            self._log_warning(f'Could not parse SAE: {e}')

    def _parse_coding(self, file_path, dictionary):
        """Parse coding report file (dry-run)."""
        df = pd.read_excel(file_path)
        self.stats['coding_items'] += len(df)
        self.stdout.write(f'  {dictionary} Coding: {len(df)} rows')

    def _parse_inactivated(self, file_path):
        """Parse inactivated records file (dry-run)."""
        df = pd.read_excel(file_path)
        self.stats['inactivated_records'] = len(df)
        self.stdout.write(f'  Inactivated Records: {len(df)} rows')

    def _parse_lab_issues(self, file_path):
        """Parse lab issues file (dry-run)."""
        df = pd.read_excel(file_path)
        self.stats['lab_issues'] = len(df)
        self.stdout.write(f'  Lab Issues: {len(df)} rows')

    def _parse_missing_pages(self, file_path):
        """Parse missing pages file (dry-run)."""
        try:
            df = pd.read_excel(file_path, sheet_name='All Pages Missing')
            self.stats['missing_pages'] = len(df)
            self.stdout.write(f'  Missing Pages: {len(df)} rows')
        except Exception:
            df = pd.read_excel(file_path)
            self.stats['missing_pages'] = len(df)
            self.stdout.write(f'  Missing Pages: {len(df)} rows')

    def _parse_missing_visits(self, file_path):
        """Parse missing visits file (dry-run)."""
        try:
            df = pd.read_excel(file_path, sheet_name='Missing Visits')
            self.stats['missing_visits'] = len(df)
            self.stdout.write(f'  Missing Visits: {len(df)} rows')
        except Exception:
            df = pd.read_excel(file_path)
            self.stats['missing_visits'] = len(df)
            self.stdout.write(f'  Missing Visits: {len(df)} rows')

    def _load_cpid_metrics(self, file_path):
        """Load CPID_EDC_Metrics with all sheets."""
        self.stdout.write(f'\nLoading {file_path.name}...')
        
        # Step 1: Load subjects (creates countries and sites as needed)
        self._load_subjects(file_path)
        
        # Step 2: Load queries
        self._load_queries(file_path)
        
        # Step 3: Load SDV records
        self._load_sdv(file_path)
        
        # Step 4: Load PI Signatures
        self._load_pi_signatures(file_path)
        
        # Step 5: Load Protocol Deviations
        self._load_protocol_deviations(file_path)
        
        # Step 6: Load Non-conformant events
        self._load_nonconformant(file_path)

    # =========================================================================
    # Subject loading (creates countries/sites implicitly)
    # =========================================================================
    
    def _load_subjects(self, file_path):
        """Load subjects from Subject Level Metrics sheet."""
        self.stdout.write('  Loading subjects...')
        
        df = pd.read_excel(file_path, sheet_name='Subject Level Metrics')
        df = df.dropna(subset=['Subject ID'])
        
        countries_created = {}
        sites_created = {}
        subjects_created = 0
        
        for idx, row in df.iterrows():
            try:
                # Extract data with proper column names
                region = str(row.get('Region', 'Unknown')).strip()
                country_code = str(row.get('Country', 'XX')).strip()
                site_str = str(row.get('Site ID', 'Site 0')).strip()
                subject_str = str(row.get('Subject ID', '')).strip()
                subject_status = str(row.get('Subject Status (Source: PRIMARY Form)', 'Enrolled')).strip()
                latest_visit = str(row.get('Latest Visit (SV) (Source: Rave EDC: BO4)', '')).strip()
                
                if not subject_str or pd.isna(row.get('Subject ID')):
                    continue
                
                # Extract site number from "Site X" format
                site_match = re.search(r'Site\s*(\d+)', site_str, re.IGNORECASE)
                site_number = site_match.group(1) if site_match else site_str.replace('Site', '').strip()
                
                # Create country if not exists
                if country_code and country_code not in countries_created and country_code != 'nan':
                    country, created = Country.objects.get_or_create(
                        study=self.study,
                        country_code=country_code,
                        defaults={
                            'country_name': COUNTRY_NAMES.get(country_code, country_code),
                            'region': region if region != 'nan' else 'Unknown'
                        }
                    )
                    countries_created[country_code] = country
                    if created:
                        self.stats['countries'] += 1
                else:
                    country = countries_created.get(country_code)
                
                if not country:
                    # Create default country
                    country, _ = Country.objects.get_or_create(
                        study=self.study,
                        country_code='XX',
                        defaults={'country_name': 'Unknown', 'region': 'Unknown'}
                    )
                
                # Create site if not exists
                site_id = f"Study_1_{site_number}"
                if site_id not in sites_created:
                    site, created = Site.objects.get_or_create(
                        site_id=site_id,
                        defaults={
                            'study': self.study,
                            'country': country,
                            'site_number': site_number,
                            'status': 'Active'
                        }
                    )
                    sites_created[site_id] = site
                    if created:
                        self.stats['sites'] += 1
                else:
                    site = sites_created[site_id]
                
                # Create subject
                # Extract subject number from "Subject X" format
                subj_match = re.search(r'Subject\s*(\d+)', subject_str, re.IGNORECASE)
                subject_external_id = subject_str if not subj_match else f"Subject {subj_match.group(1)}"
                subject_id = f"Study_1_{subject_external_id.replace(' ', '_')}"
                
                # Map subject status
                status_map = {
                    'Enrolled': 'Enrolled',
                    'Screened': 'Screened',
                    'Discontinued': 'Withdrawn',
                    'Completed': 'Completed',
                    'Screen Failed': 'Screen Failed',
                }
                mapped_status = status_map.get(subject_status, 'Enrolled')
                
                subject, created = Subject.objects.update_or_create(
                    subject_id=subject_id,
                    defaults={
                        'study': self.study,
                        'site': site,
                        'subject_external_id': subject_external_id,
                        'subject_status': mapped_status,
                        'latest_visit': latest_visit if latest_visit != 'nan' else None
                    }
                )
                if created:
                    subjects_created += 1
                    
            except Exception as e:
                self._reject_row('Subject Level Metrics', idx, str(e))
        
        self.stats['subjects'] = subjects_created
        self.stdout.write(self.style.SUCCESS(f'  Created {subjects_created} subjects, {len(sites_created)} sites, {len(countries_created)} countries'))

    # =========================================================================
    # Query loading
    # =========================================================================
    
    def _load_queries(self, file_path):
        """Load queries from Query Report sheets."""
        self.stdout.write('  Loading queries...')
        
        total_queries = 0
        
        for sheet_name in ['Query Report - Cumulative', 'Query Report - Site Action', 'Query Report - CRA Action']:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                count = self._load_query_sheet(df, sheet_name)
                total_queries += count
            except Exception as e:
                self._log_warning(f'Could not load {sheet_name}: {e}')
        
        self.stats['queries'] = total_queries
        self.stdout.write(self.style.SUCCESS(f'  Loaded {total_queries} queries'))

    def _load_query_sheet(self, df, sheet_name):
        """Load queries from a single sheet."""
        count = 0
        
        for idx, row in df.iterrows():
            try:
                # Find subject
                subject_str = str(row.get('Subject Name', '')).strip()
                if not subject_str or subject_str == 'nan':
                    continue
                
                subject = self._find_subject(subject_str)
                if not subject:
                    self._reject_row(sheet_name, idx, f'Subject not found: {subject_str}')
                    continue
                
                # Extract query data
                folder_name = str(row.get('Folder Name', ''))
                form_name = str(row.get('Form', ''))
                field_oid = str(row.get('Field OID', ''))
                log_number = str(row.get('Log #', idx))
                visit_date = pd.to_datetime(row.get('Visit Date'), errors='coerce')
                query_status = str(row.get('Query Status', 'Open'))
                action_owner = str(row.get('Action Owner', 'Site'))
                marking_group = str(row.get('Marking Group Name', ''))
                query_open_date = pd.to_datetime(row.get('Query Open Date'), errors='coerce')
                query_response_date = pd.to_datetime(row.get('Query Response Date'), errors='coerce')
                days_since_open = int(row.get('# Days Since Open', 0)) if pd.notna(row.get('# Days Since Open')) else 0
                days_since_response = row.get('# Days Since Response')
                
                # Map action owner
                action_owner_map = {
                    'Site Review': 'Site',
                    'Site': 'Site',
                    'CRA': 'CRA',
                    'CRA Review': 'CRA',
                    'DM': 'DM',
                    'Sponsor': 'Sponsor',
                }
                mapped_owner = action_owner_map.get(action_owner, 'Site')
                
                # Create unique query ID
                query_key = f"{subject.subject_id}_{log_number}_{field_oid}"
                
                Query.objects.update_or_create(
                    subject=subject,
                    log_number=log_number,
                    field_oid=field_oid if field_oid != 'nan' else None,
                    defaults={
                        'folder_name': folder_name if folder_name != 'nan' else None,
                        'form_name': form_name if form_name != 'nan' else 'Unknown',
                        'query_status': query_status if query_status != 'nan' else 'Open',
                        'action_owner': mapped_owner,
                        'marking_group_name': marking_group if marking_group != 'nan' else None,
                        'query_open_date': query_open_date.date() if pd.notna(query_open_date) else timezone.now().date(),
                        'query_response_date': query_response_date.date() if pd.notna(query_response_date) else None,
                        'visit_date': visit_date.date() if pd.notna(visit_date) else None,
                        'days_since_open': days_since_open,
                        'days_since_response': int(days_since_response) if pd.notna(days_since_response) else None,
                    }
                )
                count += 1
                
            except Exception as e:
                self._reject_row(sheet_name, idx, str(e))
        
        return count

    # =========================================================================
    # SDV loading
    # =========================================================================
    
    def _load_sdv(self, file_path):
        """Load SDV records."""
        self.stdout.write('  Loading SDV records...')
        
        try:
            df = pd.read_excel(file_path, sheet_name='SDV')
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject Name', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    visit_date = pd.to_datetime(row.get('Visit Date'), errors='coerce')
                    verification_status = str(row.get('Verification Status', 'Pending'))
                    
                    SDVStatus.objects.update_or_create(
                        study=self.study,
                        subject=subject,
                        site=subject.site,
                        defaults={
                            'status': verification_status,
                            'sdv_date': visit_date.date() if pd.notna(visit_date) else None,
                        }
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('SDV', idx, str(e))
            
            self.stats['sdv_records'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} SDV records'))
            
        except Exception as e:
            self._log_warning(f'Could not load SDV: {e}')

    # =========================================================================
    # PI Signature loading
    # =========================================================================
    
    def _load_pi_signatures(self, file_path):
        """Load PI Signature records."""
        self.stdout.write('  Loading PI Signatures...')
        
        try:
            df = pd.read_excel(file_path, sheet_name='PI Signature Report')
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject Name', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    require_signature = str(row.get('Page Require Signature', 'No'))
                    audit_action = str(row.get('Audit Action', ''))
                    signed_date = pd.to_datetime(row.get('Date page entered/ Date last PI Sign'), errors='coerce')
                    num_days = row.get('No. of days', 0)
                    
                    # Determine status
                    status = 'Signed' if 'signed' in audit_action.lower() else 'Pending'
                    
                    PISignatureStatus.objects.update_or_create(
                        study=self.study,
                        subject=subject,
                        defaults={
                            'status': status,
                            'signed_date': signed_date.date() if pd.notna(signed_date) else None,
                        }
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('PI Signature Report', idx, str(e))
            
            self.stats['pi_signatures'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} PI Signature records'))
            
        except Exception as e:
            self._log_warning(f'Could not load PI Signatures: {e}')

    # =========================================================================
    # Protocol Deviation loading
    # =========================================================================
    
    def _load_protocol_deviations(self, file_path):
        """Load Protocol Deviation records."""
        self.stdout.write('  Loading Protocol Deviations...')
        
        try:
            df = pd.read_excel(file_path, sheet_name='Protocol Deviation')
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject Name', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    status = str(row.get('PD Status', 'Open'))
                    visit_date = pd.to_datetime(row.get('Visit date'), errors='coerce')
                    
                    ProtocolDeviation.objects.create(
                        study=self.study,
                        subject=subject,
                        deviation_type='Protocol Deviation',
                        status=status if status != 'nan' else 'Open',
                        deviation_date=visit_date.date() if pd.notna(visit_date) else timezone.now().date()
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Protocol Deviation', idx, str(e))
            
            self.stats['protocol_deviations'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} Protocol Deviations'))
            
        except Exception as e:
            self._log_warning(f'Could not load Protocol Deviations: {e}')

    # =========================================================================
    # Non-conformant events loading
    # =========================================================================
    
    def _load_nonconformant(self, file_path):
        """Load Non-conformant events."""
        self.stdout.write('  Loading Non-conformant events...')
        
        try:
            df = pd.read_excel(file_path, sheet_name='Non conformant')
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject Name', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    # Non-conformant requires a FormPage - create placeholder visit/page
                    folder_name = str(row.get('Folder Name', 'Unknown'))
                    page_name = str(row.get('Page', 'Unknown'))
                    visit_date = pd.to_datetime(row.get('Visit date'), errors='coerce')
                    
                    # Get or create visit
                    visit, _ = Visit.objects.get_or_create(
                        subject=subject,
                        visit_name=folder_name if folder_name != 'nan' else 'Unknown',
                        defaults={
                            'visit_date': visit_date.date() if pd.notna(visit_date) else None,
                            'status': 'Completed'
                        }
                    )
                    
                    # Get or create form page
                    page, _ = FormPage.objects.get_or_create(
                        visit=visit,
                        form_name=page_name if page_name != 'nan' else 'Unknown',
                        defaults={
                            'folder_name': folder_name if folder_name != 'nan' else None,
                            'status': 'Draft'
                        }
                    )
                    
                    audit_time = pd.to_datetime(row.get('Audit Time'), errors='coerce')
                    
                    NonConformantEvent.objects.create(
                        page=page,
                        subject=subject,
                        issue_type='Non-conformant Data',
                        severity='Medium',
                        status='Open',
                        detected_date=audit_time.date() if pd.notna(audit_time) else timezone.now().date()
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Non conformant', idx, str(e))
            
            self.stats['nonconformant_events'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} Non-conformant events'))
            
        except Exception as e:
            self._log_warning(f'Could not load Non-conformant: {e}')

    # =========================================================================
    # Other file loaders
    # =========================================================================
    
    def _load_edrr(self, file_path):
        """Load EDRR open issues."""
        try:
            df = pd.read_excel(file_path, sheet_name='OpenIssuesSummary')
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    issue_count = int(row.get('Total Open issue Count per subject', 0))
                    
                    EDRROpenIssue.objects.update_or_create(
                        study=self.study,
                        subject=subject,
                        defaults={'total_open_issue_count': issue_count}
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('OpenIssuesSummary', idx, str(e))
            
            self.stats['edrr_issues'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} EDRR issues'))
            
        except Exception as e:
            self._log_warning(f'Could not load EDRR: {e}')

    def _load_sae(self, file_path):
        """Load SAE discrepancies."""
        count = 0
        
        for sheet_name in ['SAE Dashboard_DM', 'SAE Dashboard_Safety']:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                for idx, row in df.iterrows():
                    try:
                        # Patient ID column varies
                        subject_str = str(row.get('Patient ID', row.get('Subject', ''))).strip()
                        if not subject_str or subject_str == 'nan':
                            continue
                        
                        subject = self._find_subject(subject_str)
                        if not subject:
                            continue
                        
                        discrepancy_id = str(row.get('Discrepancy ID', idx))
                        created_timestamp = pd.to_datetime(
                            row.get('Discrepancy Created Timestamp in Dashboard'),
                            errors='coerce'
                        )
                        
                        sae, created = SAEDiscrepancy.objects.update_or_create(
                            subject=subject,
                            discrepancy_id=discrepancy_id,
                            defaults={
                                'study': self.study,
                                'site': subject.site,
                                'form_name': str(row.get('Form Name', '')),
                                'review_status_dm': str(row.get('Review Status', '')) if 'DM' in sheet_name else None,
                                'action_status_dm': str(row.get('Action Status', '')) if 'DM' in sheet_name else None,
                                'case_status': str(row.get('Case Status', '')) if 'Safety' in sheet_name else None,
                                'review_status_safety': str(row.get('Review Status', '')) if 'Safety' in sheet_name else None,
                                'action_status_safety': str(row.get('Action Status', '')) if 'Safety' in sheet_name else None,
                                'discrepancy_created_timestamp': created_timestamp if pd.notna(created_timestamp) else timezone.now()
                            }
                        )
                        if created:
                            count += 1
                            
                    except Exception as e:
                        self._reject_row(sheet_name, idx, str(e))
                        
            except Exception as e:
                self._log_warning(f'Could not load {sheet_name}: {e}')
        
        self.stats['sae_discrepancies'] = count
        self.stdout.write(self.style.SUCCESS(f'  Loaded {count} SAE discrepancies'))

    def _load_coding(self, file_path, dictionary):
        """Load coding items."""
        try:
            df = pd.read_excel(file_path)
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    CodingItem.objects.create(
                        subject=subject,
                        study=self.study,
                        dictionary_name=dictionary,
                        dictionary_version=str(row.get('Dictionary Version number', '')),
                        form_oid=str(row.get('Form OID', 'Unknown')),
                        logline=str(row.get('Logline', '')),
                        field_oid=str(row.get('Field OID', '')),
                        coding_status=str(row.get('Coding Status', 'Uncoded')),
                        require_coding=str(row.get('Require Coding', 'Y')).upper() == 'Y'
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row(f'{dictionary} Coding', idx, str(e))
            
            self.stats['coding_items'] += count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} {dictionary} coding items'))
            
        except Exception as e:
            self._log_warning(f'Could not load {dictionary}: {e}')

    def _load_inactivated(self, file_path):
        """Load inactivated records."""
        try:
            df = pd.read_excel(file_path)
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    InactivatedRecord.objects.create(
                        subject=subject,
                        folder_name=str(row.get('Folder', '')),
                        form_name=str(row.get('Form ', 'Unknown')),  # Note: column has trailing space
                        data_on_form=str(row.get('Data on Form/Record', '')),
                        record_position=str(row.get('RecordPosition', '')),
                        audit_action=str(row.get('Audit Action', 'Inactivated'))
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Inactivated Records', idx, str(e))
            
            self.stats['inactivated_records'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} inactivated records'))
            
        except Exception as e:
            self._log_warning(f'Could not load Inactivated: {e}')

    def _load_lab_issues(self, file_path):
        """Load lab issues."""
        try:
            df = pd.read_excel(file_path)
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    lab_date = pd.to_datetime(row.get('Lab Date'), errors='coerce')
                    
                    LabIssue.objects.create(
                        subject=subject,
                        visit_name=str(row.get('Visit', 'Unknown')),
                        form_name=str(row.get('Form Name', 'Unknown')),
                        lab_category=str(row.get('Lab category', 'Unknown')),
                        lab_date=lab_date.date() if pd.notna(lab_date) else None,
                        test_name=str(row.get('Test Name', 'Unknown')),
                        test_description=str(row.get('Test description', '')),
                        issue=str(row.get('Issue', 'Missing Lab Name'))
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Lab Issues', idx, str(e))
            
            self.stats['lab_issues'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} lab issues'))
            
        except Exception as e:
            self._log_warning(f'Could not load Lab Issues: {e}')

    def _load_missing_pages(self, file_path):
        """Load missing pages."""
        try:
            # Try specific sheet first
            try:
                df = pd.read_excel(file_path, sheet_name='All Pages Missing')
            except Exception:
                df = pd.read_excel(file_path)
            
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject Name', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    visit_date = pd.to_datetime(row.get('Visit date'), errors='coerce')
                    days_missing = row.get('# of Days Missing', 0)
                    
                    MissingPage.objects.update_or_create(
                        subject=subject,
                        visit_name=str(row.get('Visit Name', 'Unknown')),
                        page_name=str(row.get('Page Name', 'Unknown')),
                        defaults={
                            'form_details': str(row.get('Form Details', '')),
                            'visit_date': visit_date.date() if pd.notna(visit_date) else None,
                            'days_missing': int(days_missing) if pd.notna(days_missing) else 0
                        }
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Missing Pages', idx, str(e))
            
            self.stats['missing_pages'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} missing pages'))
            
        except Exception as e:
            self._log_warning(f'Could not load Missing Pages: {e}')

    def _load_missing_visits(self, file_path):
        """Load missing visits."""
        try:
            # Try specific sheet first
            try:
                df = pd.read_excel(file_path, sheet_name='Missing Visits')
            except Exception:
                df = pd.read_excel(file_path)
            
            count = 0
            
            for idx, row in df.iterrows():
                try:
                    subject_str = str(row.get('Subject', '')).strip()
                    if not subject_str or subject_str == 'nan':
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    projected_date = pd.to_datetime(row.get('Projected Date'), errors='coerce')
                    days_outstanding = row.get('# Days Outstanding', 0)
                    
                    MissingVisit.objects.update_or_create(
                        subject=subject,
                        visit_name=str(row.get('Visit', 'Unknown')),
                        defaults={
                            'projected_date': projected_date.date() if pd.notna(projected_date) else timezone.now().date(),
                            'days_outstanding': int(days_outstanding) if pd.notna(days_outstanding) else 0
                        }
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Missing Visits', idx, str(e))
            
            self.stats['missing_visits'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} missing visits'))
            
        except Exception as e:
            self._log_warning(f'Could not load Missing Visits: {e}')

    # =========================================================================
    # Helper methods
    # =========================================================================
    
    def _find_subject(self, subject_str):
        """Find subject by external ID (handles various formats)."""
        if not subject_str or subject_str == 'nan':
            return None
        
        # Try exact match first
        subject = Subject.objects.filter(
            study=self.study,
            subject_external_id=subject_str
        ).first()
        
        if subject:
            return subject
        
        # Try normalized match (Subject X -> Subject_X)
        normalized = subject_str.replace(' ', '_')
        subject = Subject.objects.filter(
            study=self.study,
            subject_id__icontains=normalized
        ).first()
        
        if subject:
            return subject
        
        # Try extracting just the number
        match = re.search(r'Subject\s*(\d+)', subject_str, re.IGNORECASE)
        if match:
            subject_num = match.group(1)
            subject = Subject.objects.filter(
                study=self.study,
                subject_external_id__icontains=f'Subject {subject_num}'
            ).first()
        
        return subject

    def _reject_row(self, file_name, row_idx, reason):
        """Record a rejected row."""
        self.rejected_rows.append({
            'file': file_name,
            'row': row_idx + 2,  # +2 for 1-indexing and header
            'reason': reason
        })
        self.stats['errors'] += 1

    def _validate_data(self):
        """Validate loaded data - FK integrity checks."""
        self.stdout.write('\n--- Validating Data ---')
        
        # Count checks
        subject_count = Subject.objects.filter(study=self.study).count()
        site_count = Site.objects.filter(study=self.study).count()
        country_count = Country.objects.filter(study=self.study).count()
        
        self.stdout.write(f'  Subjects: {subject_count}')
        self.stdout.write(f'  Sites: {site_count}')
        self.stdout.write(f'  Countries: {country_count}')
        
        # Check expected values
        if country_count < 10:
            self._log_warning(f'Expected ~11 countries, found {country_count}')
        if site_count < 25:
            self._log_warning(f'Expected ~27 sites, found {site_count}')
        
        # FK integrity
        orphan_queries = Query.objects.filter(subject__isnull=True).count()
        if orphan_queries > 0:
            self._log_warning(f'Found {orphan_queries} queries without subjects')

    def _print_statistics(self):
        """Print final load statistics."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('LOAD STATISTICS'))
        self.stdout.write('=' * 60)
        
        for key, value in self.stats.items():
            if value > 0:
                self.stdout.write(f'  {key.replace("_", " ").title()}: {value}')
        
        if self.rejected_rows:
            self.stdout.write(self.style.WARNING(f'\n  Rejected Rows: {len(self.rejected_rows)}'))
            # Show first 10 rejections
            for rej in self.rejected_rows[:10]:
                self.stdout.write(self.style.ERROR(f'    {rej["file"]}:row {rej["row"]}: {rej["reason"][:50]}'))
            if len(self.rejected_rows) > 10:
                self.stdout.write(self.style.WARNING(f'    ... and {len(self.rejected_rows) - 10} more'))
        
        self.stdout.write('=' * 60)
