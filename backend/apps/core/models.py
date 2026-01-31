"""
Core dimension models for Clinical Trial Control Tower.

Architecture Context:
- These models represent entities in the "Core Backend Services" layer
- Data flows from Excel Upload → Validation → These tables → Governed Data Pods
- Support both OFF-chain storage and Blockchain proof generation

Models:
- DIM_STUDY
- DIM_COUNTRY
- DIM_SITE
- DIM_SUBJECT
- DIM_VISIT
- DIM_FORM_PAGE

Reference: NEST2 Project Document Section 7.3, Backend Architecture Diagram
"""

from django.db import models
from django.utils import timezone
import hashlib
import json


class Study(models.Model):
    """
    DIM_STUDY - Clinical trial study dimension.

    Top-level entity in the hierarchy. Maps to "Clinical Data Pod" in architecture.

    Architecture Integration:
    - Feeds into Clinical Data Pod (EDC/CTMS-audited)
    - Subject to SSO + Identity authentication
    - Row/Column security via Policy Engine (RBAC + ABAC)

    Business Rules:
    - study_id is the natural key and primary key
    - Each study can have multiple countries, sites, and subjects
    - snapshot_date tracks when this data was captured for reproducibility
    - Blockchain: Study creation events recorded as "Trial Event Ledger"

    Data Governance:
    - Access controlled via Policy Engine
    - Changes tracked in Audit Log (immutable)
    - Data fingerprints (hashes) stored for integrity verification

    Source: Derived from CPID_EDC_Metrics file metadata
    """

    # Primary key
    study_id = models.CharField(
        max_length=100,
        primary_key=True,
        help_text="Unique study identifier (e.g., 'Study_1', 'NYS-GRE-293')"
    )

    # Study attributes
    study_name = models.CharField(
        max_length=500,
        help_text="Full name of the clinical trial study"
    )

    region = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Primary geographic region (e.g., 'APAC', 'EMEA', 'Americas')"
    )

    status = models.CharField(
        max_length=50,
        default='Active',
        help_text="Study status: Active, Completed, On-Hold"
    )

    # Reproducibility metadata
    snapshot_date = models.DateField(
        default=timezone.now,
        help_text="Date when this study snapshot was created"
    )

    # Blockchain integration fields (Phase 7)
    blockchain_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        help_text="SHA-256 hash of study data for blockchain verification"
    )

    blockchain_tx_hash = models.CharField(
        max_length=66,
        null=True,
        blank=True,
        help_text="Blockchain transaction hash where study creation was recorded"
    )

    # Audit fields (feeds Audit Log)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'dim_study'
        verbose_name = 'Study'
        verbose_name_plural = 'Studies'
        ordering = ['study_id']
        permissions = [
            ("view_study_leadership", "Can view study as leadership"),
            ("view_study_cra", "Can view study as CRA"),
        ]

    def __str__(self):
        return f"{self.study_id} - {self.study_name}"

    def generate_data_fingerprint(self):
        """
        Generate SHA-256 hash of study data for blockchain integrity.

        This hash can be stored on blockchain to prove data hasn't been tampered with.
        Called during: Study creation, major updates, before submission.

        Returns:
            str: 64-character hexadecimal hash
        """
        data = {
            'study_id': self.study_id,
            'study_name': self.study_name,
            'region': self.region,
            'status': self.status,
            'snapshot_date': str(self.snapshot_date),
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


class Country(models.Model):
    """
    DIM_COUNTRY - Country dimension for multi-national studies.

    Represents countries participating in a clinical trial.

    Architecture Integration:
    - Part of federated data model (Partner Data Pods)
    - Subject to Row/Column security
    - CRO/Vendor access controlled via API Gateway

    Business Rules:
    - country_code is the natural key (e.g., 'IND', 'USA', 'CHN')
    - Each country belongs to exactly one study
    - Multiple sites can exist within one country
    - Unique constraint: (study, country_code) combination

    Data Governance:
    - Region-based access control (RBAC)
    - Regulators may have country-specific view permissions

    Source: Derived from CPID_EDC_Metrics 'Region_Country View' sheet
    """

    country_code = models.CharField(
        max_length=10,
        help_text="ISO country code or custom code (e.g., 'IND', 'USA')"
    )

    country_name = models.CharField(
        max_length=200,
        help_text="Full country name (e.g., 'India', 'United States')"
    )

    region = models.CharField(
        max_length=100,
        help_text="Geographic region (e.g., 'APAC', 'EMEA', 'Americas')"
    )

    # Foreign key to Study
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='countries',
        help_text="Parent study this country belongs to"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dim_country'
        verbose_name = 'Country'
        verbose_name_plural = 'Countries'
        unique_together = [['study', 'country_code']]
        ordering = ['region', 'country_name']

    def __str__(self):
        return f"{self.country_name} ({self.country_code})"


class Site(models.Model):
    """
    DIM_SITE - Clinical trial site dimension.

    Represents investigational sites where subjects are enrolled.

    Architecture Integration:
    - Primary entity for CRA role-based access
    - Feeds into Trial Ops Pod (CRA/Monitoring)
    - Site-level DQI scores computed in KPI + Analytics Service

    Access Control:
    - CRAs see only assigned sites
    - Site staff see only their own site
    - Leadership sees all sites

    Blockchain Integration:
    - Site activation/deactivation events recorded on blockchain
    - Monitoring visit approvals signed and stored

    Business Rules:
    - site_id is composite: study_id + site_number (e.g., "Study_1_101")
    - Each site belongs to exactly one country and study
    - Sites are the primary operational unit for CRAs and monitoring

    Source: Derived from CPID_EDC_Metrics 'Subject Level Metrics' sheet
    """

    site_id = models.CharField(
        max_length=100,
        primary_key=True,
        help_text="Unique site identifier: {study_id}_{site_number}"
    )

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='sites',
        help_text="Parent study"
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name='sites',
        help_text="Country where site is located"
    )

    # Site attributes
    site_number = models.CharField(
        max_length=50,
        help_text="Site number within study (e.g., '101', '102')"
    )

    site_name = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Full site name or hospital name (optional)"
    )

    status = models.CharField(
        max_length=50,
        default='Active',
        help_text="Site status: Active, Inactive, Closed"
    )

    # Assigned CRA for access control
    assigned_cra = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="CRA username assigned to this site for RBAC"
    )

    # Blockchain fields
    blockchain_hash = models.CharField(max_length=64, null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'dim_site'
        verbose_name = 'Site'
        verbose_name_plural = 'Sites'
        ordering = ['site_number']
        permissions = [
            ("view_assigned_sites", "Can view only assigned sites (CRA)"),
        ]
        indexes = [
            models.Index(fields=['assigned_cra', 'status']),
        ]

    def __str__(self):
        return f"Site {self.site_number} - {self.country.country_name}"


class Subject(models.Model):
    """
    DIM_SUBJECT - Clinical trial subject/patient dimension.

    Represents individual participants. PRIMARY GRAIN for operational metrics.

    Architecture Integration:
    - Core entity in Clinical Data Pod
    - Subject to strictest access controls (pseudonymization, role/attributes)
    - Feeds all fact tables and metrics calculations
    - Clean Patient Status and DQI computed at subject level

    Data Privacy & Security:
    - subject_external_id is pseudonymized identifier
    - Real PII never stored in this system
    - Access controlled via Policy Engine (RBAC + ABAC)
    - API Gateway enforces access rules for CRO/Vendors

    Blockchain Integration:
    - Enrollment events recorded as "Trial Event Ledger"
    - Status changes (Withdrawn, Completed) require signatures
    - Data fingerprints for regulatory submissions

    Business Rules:
    - subject_id is composite: study_id + subject identifier
    - Each subject belongs to exactly one site
    - Subject status tracks lifecycle: Screened → Enrolled → Completed/Withdrawn
    - This is the primary entity for Clean Patient Status and DQI calculations

    Source: CPID_EDC_Metrics 'Subject Level Metrics' sheet
    """

    STATUS_CHOICES = [
        ('Screened', 'Screened'),
        ('Enrolled', 'Enrolled'),
        ('Completed', 'Completed'),
        ('Withdrawn', 'Withdrawn'),
        ('Screen Failed', 'Screen Failed'),
        ('Suspended', 'Suspended'),
    ]

    # Primary key
    subject_id = models.CharField(
        max_length=100,
        primary_key=True,
        help_text="Unique subject identifier: {study_id}_{subject_number}"
    )

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='subjects',
        help_text="Parent study"
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='subjects',
        help_text="Site where subject is enrolled"
    )

    # Subject attributes (pseudonymized)
    subject_external_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="External subject ID visible in source files (e.g., '0-005') - PSEUDONYMIZED"
    )

    subject_status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        help_text="Current subject lifecycle status"
    )

    enrollment_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date subject was enrolled (if applicable)"
    )

    latest_visit = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Most recent visit completed (for quick reference)"
    )

    # Blockchain fields (Phase 7)
    blockchain_hash = models.CharField(max_length=64, null=True, blank=True)
    enrollment_tx_hash = models.CharField(max_length=66, null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'dim_subject'
        verbose_name = 'Subject'
        verbose_name_plural = 'Subjects'
        ordering = ['site', 'subject_external_id']
        indexes = [
            models.Index(fields=['site', 'subject_status']),
            models.Index(fields=['subject_status']),
            models.Index(fields=['enrollment_date']),
        ]

    def __str__(self):
        return f"{self.subject_external_id} ({self.subject_status})"

    def generate_data_fingerprint(self):
        """Generate SHA-256 hash for blockchain integrity verification."""
        data = {
            'subject_id': self.subject_id,
            'subject_status': self.subject_status,
            'enrollment_date': str(self.enrollment_date) if self.enrollment_date else None,
            'site_id': self.site_id,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


class Visit(models.Model):
    """
    DIM_VISIT - Subject visit dimension.

    Protocol-defined timepoints where data is collected.

    Architecture Integration:
    - Part of Clinical Data Pod
    - Drives "Visit Projection Tracker" operational reports
    - Missing visits calculated via Validation + Workflow Engine

    Business Rules:
    - Each visit belongs to exactly one subject
    - visit_name is protocol-defined (e.g., 'Screening', 'Week 4', 'EOS')
    - Unique constraint: (subject, visit_name)
    - Used to track missing visits (projected but not occurred)

    Source: Visit Projection Tracker, CPID_EDC_Metrics
    """

    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Completed', 'Completed'),
        ('Missed', 'Missed'),
        ('Cancelled', 'Cancelled'),
    ]

    visit_id = models.AutoField(primary_key=True)

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='visits',
        help_text="Subject this visit belongs to"
    )

    visit_name = models.CharField(
        max_length=200,
        help_text="Protocol-defined visit name (e.g., 'Screening', 'Week 4')"
    )

    visit_date = models.DateField(
        null=True,
        blank=True,
        help_text="Actual visit date (when visit occurred)"
    )

    projected_date = models.DateField(
        null=True,
        blank=True,
        help_text="Projected/scheduled visit date"
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Scheduled',
        help_text="Visit status"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dim_visit'
        verbose_name = 'Visit'
        verbose_name_plural = 'Visits'
        unique_together = [['subject', 'visit_name']]
        ordering = ['subject', 'projected_date', 'visit_date']
        indexes = [
            models.Index(fields=['subject', 'status']),
        ]

    def __str__(self):
        return f"{self.subject.subject_external_id} - {self.visit_name}"


class FormPage(models.Model):
    """
    DIM_FORM_PAGE - CRF form and page dimension.

    Individual CRF pages within visits. Tracks data entry completion.

    Architecture Integration:
    - Part of Clinical Data Pod (EDC/CTMS-audited)
    - Status changes flow through Validation + Workflow Engine
    - Lock/Sign events recorded on blockchain (Phase 7)

    Blockchain Integration:
    - Form lock events → "Lock event signed"
    - PI signature → "PI/A approval signed"
    - Database lock → "Database lock signed"

    Business Rules:
    - Each form/page belongs to a visit
    - Hierarchy: Folder → Form → Page (typical EDC structure)
    - Status tracks data entry lifecycle: Draft → Submitted → Locked → Signed
    - Used to track missing pages and completion status

    Source: Missing Pages Report, CPID_EDC_Metrics
    """

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Submitted', 'Submitted'),
        ('Locked', 'Locked'),
        ('Signed', 'Signed'),
        ('Frozen', 'Frozen'),
    ]

    page_id = models.AutoField(primary_key=True)

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        related_name='form_pages',
        help_text="Visit this form/page belongs to"
    )

    # Form/Page hierarchy
    folder_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="EDC folder name (top level)"
    )

    form_name = models.CharField(
        max_length=200,
        help_text="EDC form name"
    )

    form_oid = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="EDC form OID (object identifier)"
    )

    page_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="EDC page name (if form has multiple pages)"
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='Draft',
        help_text="Current data entry status"
    )

    # Blockchain fields (Phase 7)
    lock_tx_hash = models.CharField(max_length=66, null=True, blank=True)
    signature_tx_hash = models.CharField(max_length=66, null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    locked_by = models.CharField(max_length=100, null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.CharField(max_length=100, null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'dim_form_page'
        verbose_name = 'Form Page'
        verbose_name_plural = 'Form Pages'
        ordering = ['visit', 'folder_name', 'form_name', 'page_name']
        indexes = [
            models.Index(fields=['visit', 'status']),
        ]

    def __str__(self):
        if self.page_name:
            return f"{self.form_name} - {self.page_name}"
        return self.form_name
