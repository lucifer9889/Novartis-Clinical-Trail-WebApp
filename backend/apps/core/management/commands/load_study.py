"""
Generic Multi-Study Data Loader for Clinical Trial Control Tower.

This command loads clinical trial data from Excel files for any study.

Usage:
    python manage.py load_study --study "Study 1" --data_dir ./data/study1 --dry-run
    python manage.py load_study --study "Study 1" --data_dir ./data/study1 --wipe
    python manage.py load_study --study "Study 1" --data_dir ./data/study1 --mode upsert

    python manage.py load_study --study "Study 2" --data_dir ./data/study2 --dry-run
    python manage.py load_study --study "Study 2" --data_dir ./data/study2 --wipe
    python manage.py load_study --study "Study 2" --data_dir ./data/study2 --mode upsert

Options:
    --dry-run: Parse and validate only, no database writes
    --wipe: Delete all data for this study, then reload
    --mode upsert: Idempotent merge (default)

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
import json

from apps.core.models import Study, Country, Site, Subject, Visit, FormPage
from apps.monitoring.models import (
    Query, SDVStatus, PISignatureStatus, ProtocolDeviation,
    NonConformantEvent, MissingVisit, MissingPage
)
from apps.safety.models import LabIssue, SAEDiscrepancy
from apps.medical_coding.models import CodingItem, EDRROpenIssue, InactivatedRecord


# Country code to name mapping
COUNTRY_NAMES = {
    'AUT': 'Austria', 'CHN': 'China', 'CZE': 'Czech Republic',
    'DEU': 'Germany', 'ESP': 'Spain', 'FRA': 'France',
    'GBR': 'United Kingdom', 'ISR': 'Israel', 'KOR': 'South Korea',
    'SGP': 'Singapore', 'USA': 'United States', 'IND': 'India',
    'JPN': 'Japan', 'AUS': 'Australia', 'CAN': 'Canada',
    'NLD': 'Netherlands', 'BEL': 'Belgium', 'CHE': 'Switzerland',
    'ITA': 'Italy', 'POL': 'Poland', 'RUS': 'Russia', 'BRA': 'Brazil',
    'MEX': 'Mexico', 'ARG': 'Argentina', 'TWN': 'Taiwan', 'HKG': 'Hong Kong',
    'THA': 'Thailand', 'MYS': 'Malaysia', 'PHL': 'Philippines', 'VNM': 'Vietnam',
}


class Command(BaseCommand):
    """Generic multi-study data loader with dry-run, wipe, and upsert modes."""
    
    help = 'Load clinical trial data from Excel files for a specific study'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {}
        self.rejected_rows = []
        self.logger = None
        self.dry_run = False
        self.study = None
        self.study_id = None
        self.mapping_doc = []

    def add_arguments(self, parser):
        parser.add_argument(
            '--study',
            type=str,
            required=True,
            help='Study name (e.g., "Study 1", "Study 2")'
        )
        parser.add_argument(
            '--data_dir',
            type=str,
            required=True,
            help='Directory containing Excel files for this study'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate only, do not write to database'
        )
        parser.add_argument(
            '--wipe',
            action='store_true',
            help='Delete all data for this study before loading'
        )
        parser.add_argument(
            '--mode',
            type=str,
            choices=['upsert', 'insert'],
            default='upsert',
            help='Load mode: upsert (default, idempotent) or insert'
        )
        parser.add_argument(
            '--log-dir',
            type=str,
            default='./logs',
            help='Directory for log files (default: ./logs)'
        )

    def handle(self, *args, **options):
        """Main entry point for the command."""
        study_name = options['study']
        data_dir = Path(options['data_dir'])
        self.dry_run = options['dry_run']
        wipe = options['wipe']
        mode = options['mode']
        log_dir = Path(options['log_dir'])
        
        # Normalize study ID (e.g., "Study 1" -> "Study_1")
        self.study_id = study_name.replace(' ', '_')
        
        # Setup logging
        self._setup_logging(log_dir, study_name)
        
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS(f'MULTI-STUDY DATA LOADER: {study_name}'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Data directory: {data_dir.absolute()}')
        self.stdout.write(f'Mode: {"DRY-RUN" if self.dry_run else "WIPE + LOAD" if wipe else mode.upper()}')
        
        # Initialize
        self._init_stats()
        self.mapping_doc = [f"# Data Ingestion Mapping: {study_name}\n"]
        self.mapping_doc.append(f"Generated: {datetime.now().isoformat()}\n")
        
        # Validate data directory
        if not data_dir.exists():
            self._log_error(f'Data directory not found: {data_dir}')
            self._print_file_instructions(study_name, data_dir)
            raise CommandError(f'Data directory does not exist: {data_dir}')
        
        # Profile Excel files
        self._profile_excel_files(data_dir)
        
        try:
            if self.dry_run:
                self._parse_and_validate(data_dir)
            else:
                with transaction.atomic():
                    if wipe:
                        self._wipe_study_data()
                    self._load_all_data(data_dir)
                    self._validate_data()
        
        except Exception as e:
            self._log_error(f'Fatal error: {str(e)}')
            import traceback
            self._log_error(traceback.format_exc())
            raise
        
        finally:
            self._print_statistics()
            self._save_mapping_doc(log_dir)
            self._log_info('Load complete')

    def _setup_logging(self, log_dir, study_name):
        """Setup file logging."""
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = study_name.replace(' ', '_').lower()
        log_file = log_dir / f'load_{safe_name}_{timestamp}.log'
        
        self.logger = logging.getLogger(f'{safe_name}_loader')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []  # Clear existing handlers
        
        fh = logging.FileHandler(log_file)
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        
        self._log_info(f'Logging to: {log_file}')
        self.stdout.write(f'Log file: {log_file}')

    def _log_info(self, msg):
        if self.logger:
            self.logger.info(msg)

    def _log_error(self, msg):
        if self.logger:
            self.logger.error(msg)
        self.stdout.write(self.style.ERROR(msg))

    def _log_warning(self, msg):
        if self.logger:
            self.logger.warning(msg)
        self.stdout.write(self.style.WARNING(msg))

    def _init_stats(self):
        self.stats = {
            'countries': 0, 'sites': 0, 'subjects': 0, 'visits': 0,
            'form_pages': 0, 'queries': 0, 'sdv_records': 0,
            'pi_signatures': 0, 'protocol_deviations': 0,
            'nonconformant_events': 0, 'missing_visits': 0,
            'missing_pages': 0, 'lab_issues': 0, 'sae_discrepancies': 0,
            'coding_items': 0, 'edrr_issues': 0, 'inactivated_records': 0,
            'errors': 0,
        }
        self.rejected_rows = []

    def _profile_excel_files(self, data_dir):
        """Profile all Excel files in the directory."""
        self.stdout.write('\n--- Profiling Excel Files ---')
        self.mapping_doc.append("\n## Excel Files Profiled\n")
        
        for fname in sorted(os.listdir(data_dir)):
            if not fname.endswith('.xlsx'):
                continue
            fpath = data_dir / fname
            try:
                xl = pd.ExcelFile(fpath)
                self.stdout.write(f'\n{fname}:')
                self.mapping_doc.append(f"\n### {fname}\n")
                self.mapping_doc.append(f"| Sheet | Rows | Columns |\n|-------|------|--------|\n")
                
                for sheet in xl.sheet_names:
                    try:
                        df = pd.read_excel(fpath, sheet_name=sheet)
                        df = df.dropna(how='all')  # Remove completely empty rows
                        cols = list(df.columns)[:6]
                        self.stdout.write(f'  [{sheet}] {len(df)} rows: {cols}...')
                        self.mapping_doc.append(f"| {sheet} | {len(df)} | {', '.join(cols[:4])}... |\n")
                    except Exception as e:
                        self.stdout.write(f'  [{sheet}] Error: {e}')
            except Exception as e:
                self._log_warning(f'Could not read {fname}: {e}')

    def _print_file_instructions(self, study_name, data_dir):
        """Print instructions for missing files."""
        self.stdout.write(self.style.ERROR(f'\nMissing files for {study_name}'))
        self.stdout.write(f'Expected directory: {data_dir}')

    def _wipe_study_data(self):
        """Delete all data for this study in FK-safe order."""
        self.stdout.write(f'\n--- Wiping {self.study_id} Data ---')
        self._log_info(f'Wiping {self.study_id} data...')
        
        # Delete in FK-safe order
        InactivatedRecord.objects.filter(subject__study_id=self.study_id).delete()
        CodingItem.objects.filter(study_id=self.study_id).delete()
        EDRROpenIssue.objects.filter(study_id=self.study_id).delete()
        SAEDiscrepancy.objects.filter(study_id=self.study_id).delete()
        LabIssue.objects.filter(subject__study_id=self.study_id).delete()
        MissingPage.objects.filter(subject__study_id=self.study_id).delete()
        MissingVisit.objects.filter(subject__study_id=self.study_id).delete()
        NonConformantEvent.objects.filter(subject__study_id=self.study_id).delete()
        ProtocolDeviation.objects.filter(study_id=self.study_id).delete()
        PISignatureStatus.objects.filter(study_id=self.study_id).delete()
        SDVStatus.objects.filter(study_id=self.study_id).delete()
        Query.objects.filter(subject__study_id=self.study_id).delete()
        FormPage.objects.filter(visit__subject__study_id=self.study_id).delete()
        Visit.objects.filter(subject__study_id=self.study_id).delete()
        Subject.objects.filter(study_id=self.study_id).delete()
        Site.objects.filter(study_id=self.study_id).delete()
        Country.objects.filter(study_id=self.study_id).delete()
        
        self.stdout.write(self.style.SUCCESS(f'{self.study_id} data wiped'))

    def _parse_and_validate(self, data_dir):
        """Dry-run mode: parse and report counts."""
        self.stdout.write('\n--- DRY-RUN: Parsing and Validating ---')
        
        # Find and parse the main EDC metrics file
        cpid_file = self._find_file(data_dir, 'CPID', 'EDC_Metrics')
        if cpid_file:
            self._parse_cpid_metrics(cpid_file)
        
        # Parse other files
        for pattern, parser in [
            ('Compiled_EDRR', self._parse_edrr),
            (('eSAE', 'SAE Dashboard'), self._parse_sae),
            (('MedDRA', 'Medra'), lambda f: self._parse_coding(f, 'MedDRA')),
            (('WHODD', 'WHOdra'), lambda f: self._parse_coding(f, 'WHODD')),
            ('Inactivated', self._parse_inactivated),
            (('Missing_Lab', 'Missing Lab'), self._parse_lab_issues),
            (('Missing_Pages', 'Missing Pages'), self._parse_missing_pages),
            (('Visit Projection', 'Visit_Projection'), self._parse_missing_visits),
        ]:
            file = self._find_file(data_dir, *pattern) if isinstance(pattern, tuple) else self._find_file(data_dir, pattern)
            if file:
                try:
                    parser(file)
                except Exception as e:
                    self._log_warning(f'Error parsing {file.name}: {e}')

    def _load_all_data(self, data_dir):
        """Load all data from Excel files."""
        self.stdout.write(f'\n--- Loading {self.study_id} Data ---')
        
        # Step 1: Create Study
        self.study = self._create_study()
        
        # Step 2: Load main EDC metrics (creates subjects, queries, etc.)
        cpid_file = self._find_file(data_dir, 'CPID', 'EDC_Metrics')
        if cpid_file:
            self._load_cpid_metrics(cpid_file)
        
        # Step 3: Load other files
        files_to_load = [
            ('Compiled_EDRR', self._load_edrr),
            (('eSAE', 'SAE Dashboard'), self._load_sae),
            (('MedDRA', 'Medra'), lambda f: self._load_coding(f, 'MedDRA')),
            (('WHODD', 'WHOdra'), lambda f: self._load_coding(f, 'WHODD')),
            ('Inactivated', self._load_inactivated),
            (('Missing_Lab', 'Missing Lab'), self._load_lab_issues),
            (('Missing_Pages', 'Missing Pages'), self._load_missing_pages),
            (('Visit Projection', 'Visit_Projection'), self._load_missing_visits),
        ]
        
        for pattern, loader in files_to_load:
            file = self._find_file(data_dir, *pattern) if isinstance(pattern, tuple) else self._find_file(data_dir, pattern)
            if file:
                self.stdout.write(f'\nLoading {file.name}...')
                try:
                    loader(file)
                except Exception as e:
                    self._log_error(f'Error loading {file.name}: {e}')
                    self.stats['errors'] += 1

    def _find_file(self, data_dir, *patterns):
        """Find Excel file matching any of the patterns."""
        for file in data_dir.glob('*.xlsx'):
            fname_lower = file.name.lower().replace('_', ' ').replace('-', ' ')
            for pattern in patterns:
                if pattern.lower().replace('_', ' ') in fname_lower:
                    return file
        return None

    def _create_study(self):
        """Create or update the study."""
        study, created = Study.objects.update_or_create(
            study_id=self.study_id,
            defaults={
                'study_name': f'{self.study_id.replace("_", " ")} - Clinical Trial',
                'region': 'Multi-Regional',
                'status': 'Active',
                'snapshot_date': timezone.now().date()
            }
        )
        self._log_info(f'Study {"created" if created else "updated"}: {self.study_id}')
        return study

    # =========================================================================
    # CPID/EDC Metrics Parsing and Loading
    # =========================================================================
    
    def _parse_cpid_metrics(self, file_path):
        """Parse CPID/EDC metrics file (dry-run)."""
        self.stdout.write(f'\nParsing {file_path.name}...')
        
        xl = pd.ExcelFile(file_path)
        self.stdout.write(f'  Sheets: {xl.sheet_names}')
        
        for sheet in ['Subject Level Metrics', 'Query Report - Cumulative', 'SDV', 
                      'PI Signature Report', 'Protocol Deviation', 'Non conformant']:
            if sheet in xl.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    df = df.dropna(how='all')
                    self.stdout.write(f'  [{sheet}]: {len(df)} rows')
                except Exception as e:
                    self._log_warning(f'  [{sheet}]: Error - {e}')

    def _load_cpid_metrics(self, file_path):
        """Load CPID/EDC metrics with all sheets."""
        self.stdout.write(f'\nLoading {file_path.name}...')
        
        # Load subjects first
        self._load_subjects(file_path)
        
        # Load queries
        self._load_queries(file_path)
        
        # Load SDV
        self._load_sdv(file_path)
        
        # Load PI Signatures
        self._load_pi_signatures(file_path)
        
        # Load Protocol Deviations
        self._load_protocol_deviations(file_path)
        
        # Load Non-conformant events
        self._load_nonconformant(file_path)

    def _load_subjects(self, file_path):
        """Load subjects from Subject Level Metrics sheet."""
        self.stdout.write('  Loading subjects...')
        
        try:
            df = pd.read_excel(file_path, sheet_name='Subject Level Metrics')
        except Exception as e:
            self._log_warning(f'Could not read Subject Level Metrics: {e}')
            return
        
        # Find the subject ID column (varies between studies)
        subj_col = None
        for col in ['Subject ID', 'Subject', 'Subject Name']:
            if col in df.columns:
                subj_col = col
                break
        
        if not subj_col:
            self._log_warning('Could not find Subject ID column')
            return
        
        df = df.dropna(subset=[subj_col])
        
        countries_cache = {}
        sites_cache = {}
        subjects_created = 0
        
        for idx, row in df.iterrows():
            try:
                region = self._clean_str(row.get('Region', 'Unknown'))
                country_code = self._clean_str(row.get('Country', 'XX'))
                site_str = self._clean_str(row.get('Site ID', row.get('Site', 'Site 0')))
                subject_str = self._clean_str(row.get(subj_col, ''))
                
                # Find status column
                status = 'Enrolled'
                for col in df.columns:
                    if 'status' in col.lower():
                        status = self._clean_str(row.get(col, 'Enrolled'))
                        break
                
                if not subject_str:
                    continue
                
                # Extract site number
                site_match = re.search(r'Site\s*(\d+)', site_str, re.IGNORECASE)
                site_number = site_match.group(1) if site_match else re.sub(r'\D', '', site_str) or '0'
                
                # Create country
                if country_code and country_code not in countries_cache:
                    country, created = Country.objects.get_or_create(
                        study=self.study,
                        country_code=country_code,
                        defaults={
                            'country_name': COUNTRY_NAMES.get(country_code, country_code),
                            'region': region if region != 'nan' else 'Unknown'
                        }
                    )
                    countries_cache[country_code] = country
                    if created:
                        self.stats['countries'] += 1
                
                country = countries_cache.get(country_code)
                if not country:
                    country, _ = Country.objects.get_or_create(
                        study=self.study, country_code='XX',
                        defaults={'country_name': 'Unknown', 'region': 'Unknown'}
                    )
                    countries_cache['XX'] = country
                
                # Create site with study-scoped ID
                site_id = f"{self.study_id}__SITE_{site_number}"
                if site_id not in sites_cache:
                    site, created = Site.objects.get_or_create(
                        site_id=site_id,
                        defaults={
                            'study': self.study,
                            'country': country,
                            'site_number': site_number,
                            'status': 'Active'
                        }
                    )
                    sites_cache[site_id] = site
                    if created:
                        self.stats['sites'] += 1
                
                site = sites_cache[site_id]
                
                # Create subject with study-scoped ID
                subj_match = re.search(r'Subject\s*(\d+)', subject_str, re.IGNORECASE)
                subj_num = subj_match.group(1) if subj_match else re.sub(r'\D', '', subject_str) or subject_str
                subject_id = f"{self.study_id}__SITE_{site_number}__SUBJECT_{subj_num}"
                
                status_map = {
                    'Enrolled': 'Enrolled', 'Screened': 'Screened',
                    'Discontinued': 'Withdrawn', 'Completed': 'Completed',
                    'Screen Failed': 'Screen Failed',
                }
                mapped_status = status_map.get(status, 'Enrolled')
                
                subject, created = Subject.objects.update_or_create(
                    subject_id=subject_id,
                    defaults={
                        'study': self.study,
                        'site': site,
                        'subject_external_id': subject_str,
                        'subject_status': mapped_status,
                    }
                )
                if created:
                    subjects_created += 1
                    
            except Exception as e:
                self._reject_row('Subject Level Metrics', idx, str(e), subject_str if 'subject_str' in dir() else 'N/A')
        
        self.stats['subjects'] = subjects_created
        self.stdout.write(self.style.SUCCESS(f'  Created {subjects_created} subjects'))

    def _load_queries(self, file_path):
        """Load queries from Query Report sheets."""
        self.stdout.write('  Loading queries...')
        
        total = 0
        xl = pd.ExcelFile(file_path)
        
        for sheet in ['Query Report - Cumulative', 'Query Report - Site Action', 'Query Report - CRA Action']:
            if sheet not in xl.sheet_names:
                continue
            
            try:
                df = pd.read_excel(file_path, sheet_name=sheet)
                count = self._load_query_sheet(df, sheet)
                total += count
            except Exception as e:
                self._log_warning(f'Could not load {sheet}: {e}')
        
        self.stats['queries'] = total
        self.stdout.write(self.style.SUCCESS(f'  Loaded {total} queries'))

    def _load_query_sheet(self, df, sheet_name):
        """Load queries from a dataframe."""
        count = 0
        
        # Find subject column
        subj_col = None
        for col in ['Subject Name', 'Subject', 'Subject ID']:
            if col in df.columns:
                subj_col = col
                break
        
        if not subj_col:
            return 0
        
        for idx, row in df.iterrows():
            try:
                subject_str = self._clean_str(row.get(subj_col, ''))
                if not subject_str:
                    continue
                
                subject = self._find_subject(subject_str)
                if not subject:
                    continue
                
                folder_name = self._clean_str(row.get('Folder Name', ''))
                form_name = self._clean_str(row.get('Form', row.get('Form Name', '')))
                field_oid = self._clean_str(row.get('Field OID', ''))
                log_number = str(row.get('Log #', row.get('Log Number', idx)))
                visit_date = pd.to_datetime(row.get('Visit Date'), errors='coerce')
                query_status = self._clean_str(row.get('Query Status', 'Open'))
                action_owner = self._clean_str(row.get('Action Owner', 'Site'))
                query_open_date = pd.to_datetime(row.get('Query Open Date'), errors='coerce')
                days_since_open = row.get('# Days Since Open', row.get('Days Since Open', 0))
                
                # Map action owner
                owner_map = {'Site Review': 'Site', 'CRA Review': 'CRA', 'DM Review': 'DM'}
                mapped_owner = owner_map.get(action_owner, action_owner) if action_owner else 'Site'
                if mapped_owner not in ['Site', 'CRA', 'DM', 'Sponsor']:
                    mapped_owner = 'Site'
                
                Query.objects.update_or_create(
                    subject=subject,
                    log_number=log_number,
                    field_oid=field_oid if field_oid else None,
                    defaults={
                        'folder_name': folder_name if folder_name else None,
                        'form_name': form_name if form_name else 'Unknown',
                        'query_status': query_status if query_status else 'Open',
                        'action_owner': mapped_owner,
                        'query_open_date': query_open_date.date() if pd.notna(query_open_date) else timezone.now().date(),
                        'visit_date': visit_date.date() if pd.notna(visit_date) else None,
                        'days_since_open': int(days_since_open) if pd.notna(days_since_open) else 0,
                    }
                )
                count += 1
                
            except Exception as e:
                self._reject_row(sheet_name, idx, str(e), subject_str if 'subject_str' in dir() else 'N/A')
        
        return count

    def _load_sdv(self, file_path):
        """Load SDV records."""
        self.stdout.write('  Loading SDV records...')
        
        try:
            xl = pd.ExcelFile(file_path)
            if 'SDV' not in xl.sheet_names:
                return
            
            df = pd.read_excel(file_path, sheet_name='SDV')
            count = 0
            
            subj_col = None
            for col in ['Subject Name', 'Subject', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    visit_date = pd.to_datetime(row.get('Visit Date'), errors='coerce')
                    status = self._clean_str(row.get('Verification Status', 'Pending'))
                    
                    SDVStatus.objects.update_or_create(
                        study=self.study,
                        subject=subject,
                        site=subject.site,
                        defaults={
                            'status': status,
                            'sdv_date': visit_date.date() if pd.notna(visit_date) else None,
                        }
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('SDV', idx, str(e), '')
            
            self.stats['sdv_records'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} SDV records'))
            
        except Exception as e:
            self._log_warning(f'Could not load SDV: {e}')

    def _load_pi_signatures(self, file_path):
        """Load PI Signature records."""
        self.stdout.write('  Loading PI Signatures...')
        
        try:
            xl = pd.ExcelFile(file_path)
            if 'PI Signature Report' not in xl.sheet_names:
                return
            
            df = pd.read_excel(file_path, sheet_name='PI Signature Report')
            count = 0
            
            subj_col = None
            for col in ['Subject Name', 'Subject', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    audit_action = self._clean_str(row.get('Audit Action', ''))
                    status = 'Signed' if 'signed' in audit_action.lower() else 'Pending'
                    
                    PISignatureStatus.objects.update_or_create(
                        study=self.study,
                        subject=subject,
                        defaults={'status': status}
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('PI Signature Report', idx, str(e), '')
            
            self.stats['pi_signatures'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} PI Signature records'))
            
        except Exception as e:
            self._log_warning(f'Could not load PI Signatures: {e}')

    def _load_protocol_deviations(self, file_path):
        """Load Protocol Deviation records."""
        self.stdout.write('  Loading Protocol Deviations...')
        
        try:
            xl = pd.ExcelFile(file_path)
            if 'Protocol Deviation' not in xl.sheet_names:
                return
            
            df = pd.read_excel(file_path, sheet_name='Protocol Deviation')
            count = 0
            
            subj_col = None
            for col in ['Subject Name', 'Subject', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    status = self._clean_str(row.get('PD Status', 'Open'))
                    visit_date = pd.to_datetime(row.get('Visit date', row.get('Visit Date')), errors='coerce')
                    
                    ProtocolDeviation.objects.create(
                        study=self.study,
                        subject=subject,
                        deviation_type='Protocol Deviation',
                        status=status if status else 'Open',
                        deviation_date=visit_date.date() if pd.notna(visit_date) else timezone.now().date()
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Protocol Deviation', idx, str(e), '')
            
            self.stats['protocol_deviations'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} Protocol Deviations'))
            
        except Exception as e:
            self._log_warning(f'Could not load Protocol Deviations: {e}')

    def _load_nonconformant(self, file_path):
        """Load Non-conformant events."""
        self.stdout.write('  Loading Non-conformant events...')
        
        try:
            xl = pd.ExcelFile(file_path)
            if 'Non conformant' not in xl.sheet_names:
                return
            
            df = pd.read_excel(file_path, sheet_name='Non conformant')
            count = 0
            
            subj_col = None
            for col in ['Subject Name', 'Subject', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    folder_name = self._clean_str(row.get('Folder Name', 'Unknown'))
                    page_name = self._clean_str(row.get('Page', 'Unknown'))
                    visit_date = pd.to_datetime(row.get('Visit date'), errors='coerce')
                    
                    # Get or create visit
                    visit, _ = Visit.objects.get_or_create(
                        subject=subject,
                        visit_name=folder_name if folder_name else 'Unknown',
                        defaults={
                            'visit_date': visit_date.date() if pd.notna(visit_date) else None,
                            'status': 'Completed'
                        }
                    )
                    
                    # Get or create form page
                    page, _ = FormPage.objects.get_or_create(
                        visit=visit,
                        form_name=page_name if page_name else 'Unknown',
                        defaults={'folder_name': folder_name, 'status': 'Draft'}
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
                    self._reject_row('Non conformant', idx, str(e), '')
            
            self.stats['nonconformant_events'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} Non-conformant events'))
            
        except Exception as e:
            self._log_warning(f'Could not load Non-conformant: {e}')

    # =========================================================================
    # Other File Loaders
    # =========================================================================
    
    def _parse_edrr(self, file_path):
        df = pd.read_excel(file_path)
        self.stdout.write(f'  EDRR: {len(df)} rows')
        self.stats['edrr_issues'] = len(df)

    def _load_edrr(self, file_path):
        """Load EDRR open issues."""
        try:
            xl = pd.ExcelFile(file_path)
            sheet = xl.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet)
            count = 0
            
            subj_col = None
            for col in ['Subject', 'Subject Name', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                self._log_warning('EDRR: No subject column found')
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    issue_count = 0
                    for col in df.columns:
                        if 'issue' in col.lower() and 'count' in col.lower():
                            issue_count = int(row.get(col, 0)) if pd.notna(row.get(col)) else 0
                            break
                    
                    EDRROpenIssue.objects.update_or_create(
                        study=self.study,
                        subject=subject,
                        defaults={'total_open_issue_count': issue_count}
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('EDRR', idx, str(e), '')
            
            self.stats['edrr_issues'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} EDRR issues'))
            
        except Exception as e:
            self._log_warning(f'Could not load EDRR: {e}')

    def _parse_sae(self, file_path):
        xl = pd.ExcelFile(file_path)
        total = sum(len(pd.read_excel(file_path, sheet_name=s)) for s in xl.sheet_names[:2])
        self.stdout.write(f'  SAE: {total} rows')
        self.stats['sae_discrepancies'] = total

    def _load_sae(self, file_path):
        """Load SAE discrepancies."""
        count = 0
        xl = pd.ExcelFile(file_path)
        
        for sheet in xl.sheet_names:
            if 'dashboard' not in sheet.lower() and 'sae' not in sheet.lower():
                continue
            
            try:
                df = pd.read_excel(file_path, sheet_name=sheet)
                
                subj_col = None
                for col in ['Patient ID', 'Subject', 'Subject Name', 'Subject ID']:
                    if col in df.columns:
                        subj_col = col
                        break
                
                if not subj_col:
                    continue
                
                for idx, row in df.iterrows():
                    try:
                        subject_str = self._clean_str(row.get(subj_col, ''))
                        if not subject_str:
                            continue
                        
                        subject = self._find_subject(subject_str)
                        if not subject:
                            continue
                        
                        discrepancy_id = str(row.get('Discrepancy ID', idx))
                        created_timestamp = pd.to_datetime(
                            row.get('Discrepancy Created Timestamp in Dashboard',
                                   row.get('Created Date', row.get('Timestamp'))),
                            errors='coerce'
                        )
                        
                        SAEDiscrepancy.objects.update_or_create(
                            subject=subject,
                            discrepancy_id=discrepancy_id,
                            defaults={
                                'study': self.study,
                                'site': subject.site,
                                'form_name': self._clean_str(row.get('Form Name', '')),
                                'review_status_dm': self._clean_str(row.get('Review Status', '')),
                                'action_status_dm': self._clean_str(row.get('Action Status', '')),
                                'case_status': self._clean_str(row.get('Case Status', '')),
                                'discrepancy_created_timestamp': created_timestamp if pd.notna(created_timestamp) else timezone.now()
                            }
                        )
                        count += 1
                        
                    except Exception as e:
                        self._reject_row(sheet, idx, str(e), '')
                        
            except Exception as e:
                self._log_warning(f'Could not load SAE sheet {sheet}: {e}')
        
        self.stats['sae_discrepancies'] = count
        self.stdout.write(self.style.SUCCESS(f'  Loaded {count} SAE discrepancies'))

    def _parse_coding(self, file_path, dictionary):
        df = pd.read_excel(file_path)
        self.stdout.write(f'  {dictionary}: {len(df)} rows')
        self.stats['coding_items'] += len(df)

    def _load_coding(self, file_path, dictionary):
        """Load coding items."""
        try:
            df = pd.read_excel(file_path)
            count = 0
            
            subj_col = None
            for col in ['Subject', 'Subject Name', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                self._log_warning(f'{dictionary}: No subject column found')
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    CodingItem.objects.create(
                        subject=subject,
                        study=self.study,
                        dictionary_name=dictionary,
                        dictionary_version=self._clean_str(row.get('Dictionary Version number', '')),
                        form_oid=self._clean_str(row.get('Form OID', 'Unknown')),
                        logline=self._clean_str(row.get('Logline', '')),
                        field_oid=self._clean_str(row.get('Field OID', '')),
                        coding_status=self._clean_str(row.get('Coding Status', 'Uncoded')),
                        require_coding=str(row.get('Require Coding', 'Y')).upper() == 'Y'
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row(f'{dictionary} Coding', idx, str(e), '')
            
            self.stats['coding_items'] += count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} {dictionary} coding items'))
            
        except Exception as e:
            self._log_warning(f'Could not load {dictionary}: {e}')

    def _parse_inactivated(self, file_path):
        df = pd.read_excel(file_path)
        self.stdout.write(f'  Inactivated: {len(df)} rows')
        self.stats['inactivated_records'] = len(df)

    def _load_inactivated(self, file_path):
        """Load inactivated records."""
        try:
            df = pd.read_excel(file_path)
            count = 0
            
            subj_col = None
            for col in ['Subject', 'Subject Name', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    InactivatedRecord.objects.create(
                        subject=subject,
                        folder_name=self._clean_str(row.get('Folder', '')),
                        form_name=self._clean_str(row.get('Form ', row.get('Form', 'Unknown'))),
                        data_on_form=self._clean_str(row.get('Data on Form/Record', '')),
                        record_position=self._clean_str(row.get('RecordPosition', '')),
                        audit_action=self._clean_str(row.get('Audit Action', 'Inactivated'))
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Inactivated', idx, str(e), '')
            
            self.stats['inactivated_records'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} inactivated records'))
            
        except Exception as e:
            self._log_warning(f'Could not load Inactivated: {e}')

    def _parse_lab_issues(self, file_path):
        df = pd.read_excel(file_path)
        self.stdout.write(f'  Lab Issues: {len(df)} rows')
        self.stats['lab_issues'] = len(df)

    def _load_lab_issues(self, file_path):
        """Load lab issues."""
        try:
            df = pd.read_excel(file_path)
            count = 0
            
            subj_col = None
            for col in ['Subject', 'Subject Name', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    lab_date = pd.to_datetime(row.get('Lab Date'), errors='coerce')
                    
                    LabIssue.objects.create(
                        subject=subject,
                        visit_name=self._clean_str(row.get('Visit', 'Unknown')),
                        form_name=self._clean_str(row.get('Form Name', 'Unknown')),
                        lab_category=self._clean_str(row.get('Lab category', 'Unknown')),
                        lab_date=lab_date.date() if pd.notna(lab_date) else None,
                        test_name=self._clean_str(row.get('Test Name', 'Unknown')),
                        test_description=self._clean_str(row.get('Test description', '')),
                        issue=self._clean_str(row.get('Issue', 'Missing Lab Name'))
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Lab Issues', idx, str(e), '')
            
            self.stats['lab_issues'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} lab issues'))
            
        except Exception as e:
            self._log_warning(f'Could not load Lab Issues: {e}')

    def _parse_missing_pages(self, file_path):
        df = pd.read_excel(file_path)
        self.stdout.write(f'  Missing Pages: {len(df)} rows')
        self.stats['missing_pages'] = len(df)

    def _load_missing_pages(self, file_path):
        """Load missing pages."""
        try:
            xl = pd.ExcelFile(file_path)
            sheet = 'All Pages Missing' if 'All Pages Missing' in xl.sheet_names else xl.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet)
            count = 0
            
            subj_col = None
            for col in ['Subject Name', 'Subject', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    visit_date = pd.to_datetime(row.get('Visit date', row.get('Visit Date')), errors='coerce')
                    days_missing = row.get('# of Days Missing', row.get('Days Missing', 0))
                    
                    MissingPage.objects.update_or_create(
                        subject=subject,
                        visit_name=self._clean_str(row.get('Visit Name', 'Unknown')),
                        page_name=self._clean_str(row.get('Page Name', 'Unknown')),
                        defaults={
                            'form_details': self._clean_str(row.get('Form Details', '')),
                            'visit_date': visit_date.date() if pd.notna(visit_date) else None,
                            'days_missing': int(days_missing) if pd.notna(days_missing) else 0
                        }
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Missing Pages', idx, str(e), '')
            
            self.stats['missing_pages'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} missing pages'))
            
        except Exception as e:
            self._log_warning(f'Could not load Missing Pages: {e}')

    def _parse_missing_visits(self, file_path):
        df = pd.read_excel(file_path)
        self.stdout.write(f'  Missing Visits: {len(df)} rows')
        self.stats['missing_visits'] = len(df)

    def _load_missing_visits(self, file_path):
        """Load missing visits."""
        try:
            xl = pd.ExcelFile(file_path)
            sheet = 'Missing Visits' if 'Missing Visits' in xl.sheet_names else xl.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet)
            count = 0
            
            subj_col = None
            for col in ['Subject', 'Subject Name', 'Subject ID']:
                if col in df.columns:
                    subj_col = col
                    break
            
            if not subj_col:
                return
            
            for idx, row in df.iterrows():
                try:
                    subject_str = self._clean_str(row.get(subj_col, ''))
                    if not subject_str:
                        continue
                    
                    subject = self._find_subject(subject_str)
                    if not subject:
                        continue
                    
                    projected_date = pd.to_datetime(row.get('Projected Date'), errors='coerce')
                    days_outstanding = row.get('# Days Outstanding', row.get('Days Outstanding', 0))
                    
                    MissingVisit.objects.update_or_create(
                        subject=subject,
                        visit_name=self._clean_str(row.get('Visit', 'Unknown')),
                        defaults={
                            'projected_date': projected_date.date() if pd.notna(projected_date) else timezone.now().date(),
                            'days_outstanding': int(days_outstanding) if pd.notna(days_outstanding) else 0
                        }
                    )
                    count += 1
                    
                except Exception as e:
                    self._reject_row('Missing Visits', idx, str(e), '')
            
            self.stats['missing_visits'] = count
            self.stdout.write(self.style.SUCCESS(f'  Loaded {count} missing visits'))
            
        except Exception as e:
            self._log_warning(f'Could not load Missing Visits: {e}')

    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _clean_str(self, value):
        """Clean string value."""
        if pd.isna(value):
            return ''
        s = str(value).strip()
        return '' if s.lower() == 'nan' else s

    def _find_subject(self, subject_str):
        """Find subject by external ID."""
        if not subject_str:
            return None
        
        # Exact match
        subject = Subject.objects.filter(
            study=self.study,
            subject_external_id=subject_str
        ).first()
        
        if subject:
            return subject
        
        # Try extracting number
        match = re.search(r'Subject\s*(\d+)', subject_str, re.IGNORECASE)
        if match:
            subject = Subject.objects.filter(
                study=self.study,
                subject_external_id__icontains=f'Subject {match.group(1)}'
            ).first()
            if subject:
                return subject
            
            # Try with subject_id pattern
            subject = Subject.objects.filter(
                study=self.study,
                subject_id__icontains=f'SUBJECT_{match.group(1)}'
            ).first()
        
        return subject

    def _reject_row(self, file_name, row_idx, reason, key=''):
        """Record a rejected row."""
        self.rejected_rows.append({
            'file': file_name,
            'row': row_idx + 2,
            'reason': reason[:100],
            'key': key[:50]
        })
        self.stats['errors'] += 1

    def _validate_data(self):
        """Validate loaded data."""
        self.stdout.write(f'\n--- Validating {self.study_id} Data ---')
        
        subject_count = Subject.objects.filter(study=self.study).count()
        site_count = Site.objects.filter(study=self.study).count()
        country_count = Country.objects.filter(study=self.study).count()
        
        self.stdout.write(f'  Subjects: {subject_count}')
        self.stdout.write(f'  Sites: {site_count}')
        self.stdout.write(f'  Countries: {country_count}')
        
        # FK checks
        orphan_queries = Query.objects.filter(subject__isnull=True).count()
        if orphan_queries > 0:
            self._log_warning(f'Found {orphan_queries} queries without subjects')

    def _print_statistics(self):
        """Print final statistics."""
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS(f'LOAD STATISTICS: {self.study_id}'))
        self.stdout.write('=' * 60)
        
        for key, value in self.stats.items():
            if value > 0:
                self.stdout.write(f'  {key.replace("_", " ").title()}: {value}')
        
        if self.rejected_rows:
            self.stdout.write(self.style.WARNING(f'\n  Rejected Rows: {len(self.rejected_rows)}'))
            for rej in self.rejected_rows[:10]:
                self.stdout.write(self.style.ERROR(f'    {rej["file"]}:row {rej["row"]}: {rej["reason"][:40]}'))
            if len(self.rejected_rows) > 10:
                self.stdout.write(f'    ... and {len(self.rejected_rows) - 10} more')

    def _save_mapping_doc(self, log_dir):
        """Save the mapping documentation."""
        try:
            docs_dir = Path('docs')
            docs_dir.mkdir(exist_ok=True)
            
            mapping_file = docs_dir / 'study_ingestion_mapping.md'
            
            # Check if file exists and append
            mode = 'a' if mapping_file.exists() else 'w'
            if mode == 'w':
                self.mapping_doc.insert(0, "# Clinical Trial Data Ingestion Mapping\n\n")
            
            with open(mapping_file, mode) as f:
                f.write('\n'.join(self.mapping_doc))
            
            self.stdout.write(f'Mapping doc: {mapping_file}')
        except Exception as e:
            self._log_warning(f'Could not save mapping doc: {e}')
