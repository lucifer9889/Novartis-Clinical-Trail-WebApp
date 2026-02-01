"""
Monitoring and compliance fact models for Clinical Trial Control Tower.

Architecture Integration:
- Maps to Trial Ops Pod (CRA/Monitoring activities)
- Query/DM Pod (query lifecycle tracking)
- Feeds into KPI + Analytics Service for operational metrics
- Status changes flow through Validation + Workflow Engine

Models:
- FACT_QUERY_EVENT
- FACT_SDV_STATUS
- FACT_PI_SIGNATURE_STATUS
- FACT_PROTOCOL_DEVIATION
- FACT_NONCONFORMANT_EVENT
- FACT_MISSING_VISIT
- FACT_MISSING_PAGE
- FACT_OPEN_ISSUE_SUMMARY
- FACT_CRF_EVENT

Reference: NEST2 Project Document Section 7.3, Backend Architecture
Source: CPID_EDC_Metrics, Visit Projection Tracker, Missing Pages Report
"""

from django.db import models
from django.utils import timezone
from apps.core.models import Study, Site, Subject, Visit, FormPage, Country
import hashlib
import json


class OpenIssueSummary(models.Model):
    """
    FACT_OPEN_ISSUE_SUMMARY - Aggregated open issue counts per subject.

    Architecture Integration:
    - Pre-computed counts for dashboard performance
    - Updated incrementally when issues change
    - Part of KPI + Analytics Service cache layer
    """

    id = models.AutoField(primary_key=True)
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='open_issue_summaries'
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='open_issue_summary'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='open_issue_summaries',
        null=True,
        blank=True
    )

    # Issue counts
    open_query_count = models.IntegerField(default=0)
    missing_page_count = models.IntegerField(default=0)
    missing_visit_count = models.IntegerField(default=0)
    sae_discrepancy_count = models.IntegerField(default=0)
    protocol_deviation_count = models.IntegerField(default=0)
    total_open_issue_count = models.IntegerField(default=0)

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_open_issue_summary'
        verbose_name = 'Open Issue Summary'
        verbose_name_plural = 'Open Issue Summaries'
        unique_together = [['study', 'subject']]
        indexes = [
            models.Index(fields=['study', 'total_open_issue_count']),
        ]


class CRFEvent(models.Model):
    """
    FACT_CRF_EVENT - CRF freeze/unfreeze/lock/unlock events.

    Architecture Integration:
    - Part of Clinical Data Pod (form status lifecycle)
    - Events recorded on blockchain for regulatory audit trail
    - Feeds database lock status tracking
    """

    EVENT_TYPE_CHOICES = [
        ('freeze', 'Freeze'),
        ('unfreeze', 'Unfreeze'),
        ('lock', 'Lock'),
        ('unlock', 'Unlock'),
        ('sign', 'Sign'),
        ('unsign', 'Unsign'),
    ]

    crf_event_id = models.AutoField(primary_key=True)
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='crf_events'
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='crf_events',
        null=True,
        blank=True
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='crf_events',
        null=True,
        blank=True
    )

    # Event details
    event_type = models.CharField(
        max_length=20,
        choices=EVENT_TYPE_CHOICES,
        help_text="Type of CRF event"
    )
    event_time = models.DateTimeField(
        help_text="When the event occurred"
    )
    folder_name = models.CharField(max_length=200, null=True, blank=True)
    page_name = models.CharField(max_length=200, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    # Blockchain proof
    blockchain_tx_hash = models.CharField(max_length=66, null=True, blank=True)

    # Audit
    performed_by = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_crf_event'
        verbose_name = 'CRF Event'
        verbose_name_plural = 'CRF Events'
        ordering = ['-event_time']
        indexes = [
            models.Index(fields=['study', 'event_type']),
            models.Index(fields=['subject', 'event_time']),
        ]


class Query(models.Model):
    """
    FACT_QUERY_EVENT - Data queries raised during monitoring.

    Architecture Integration:
    - Core entity in Query/DM Pod (query lifecycle)
    - CRA action items driven by action_owner field
    - Feeds "Open Query Queue" in CRA dashboard
    - Days_since_open tracked for SLA monitoring via Tasking + Workflow Automation

    Access Control:
    - CRAs see queries where action_owner='CRA' OR assigned to their sites
    - DQT sees all queries
    - Sites see only their own queries

    Data Governance:
    - Query responses stored in Audit Artifacts Store
    - Query resolution events can trigger blockchain proof (Phase 7)
    - GenAI Orchestrator provides suggested responses (Phase 5)

    Business Rules:
    - Natural grain: one row per query (unique log_number per subject)
    - Query lifecycle: Open → Answered → Closed/Cancelled
    - action_owner determines who needs to resolve (Site/CRA/DM)
    - days_since_open tracks query aging for SLA monitoring

    Source: CPID_EDC_Metrics 'Query Report - Cumulative' sheet
    """

    QUERY_STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Answered', 'Answered'),
        ('Closed', 'Closed'),
        ('Cancelled', 'Cancelled'),
    ]

    ACTION_OWNER_CHOICES = [
        ('Site', 'Site'),
        ('CRA', 'CRA'),
        ('DM', 'Data Management'),
        ('Sponsor', 'Sponsor'),
    ]

    # Primary key
    query_id = models.AutoField(primary_key=True)

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='queries',
        null=True,
        blank=True,
        help_text="Parent study"
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='queries',
        null=True,
        blank=True,
        help_text="Site this query belongs to"
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='queries',
        help_text="Subject this query belongs to"
    )

    visit = models.ForeignKey(
        Visit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='queries',
        help_text="Visit this query belongs to"
    )

    page = models.ForeignKey(
        FormPage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='queries',
        help_text="Form page where query was raised"
    )

    # Denormalized location fields (for faster filtering)
    region = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Region (denormalized from country)"
    )

    country_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        help_text="Country code (denormalized from site)"
    )

    site_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Site number (denormalized from site)"
    )

    # Query identification
    folder_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="EDC folder name"
    )

    form_name = models.CharField(
        max_length=200,
        help_text="EDC form name where query exists"
    )

    field_oid = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Field OID (unique field identifier in EDC)"
    )

    log_number = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="Query log number from EDC system"
    )

    # Query attributes
    query_status = models.CharField(
        max_length=50,
        choices=QUERY_STATUS_CHOICES,
        help_text="Current query status"
    )

    action_owner = models.CharField(
        max_length=100,
        choices=ACTION_OWNER_CHOICES,
        help_text="Who is responsible for resolving this query"
    )

    marking_group_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="Query marking group (query type categorization)"
    )

    # Dates and aging
    query_open_date = models.DateField(
        help_text="Date query was opened"
    )

    query_response_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date site responded to query"
    )

    visit_date = models.DateField(
        null=True,
        blank=True,
        help_text="Visit date related to this query"
    )

    days_since_open = models.IntegerField(
        default=0,
        help_text="Number of days query has been open (for SLA tracking)"
    )

    days_since_response = models.IntegerField(
        null=True,
        blank=True,
        help_text="Days since site responded (waiting DM closure)"
    )

    # Query iteration tracking (per ER diagram)
    query_iters = models.IntegerField(
        null=True,
        blank=True,
        help_text="Number of query iterations/reopens"
    )

    query_repair_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when query was repaired/fixed"
    )

    # GenAI integration (Phase 5)
    suggested_response = models.TextField(
        null=True,
        blank=True,
        help_text="AI-generated suggested response (GenAI Orchestrator)"
    )

    # Blockchain integration (Phase 7)
    resolution_tx_hash = models.CharField(
        max_length=66,
        null=True,
        blank=True,
        help_text="Blockchain transaction hash for query resolution event"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)
    updated_by = models.CharField(max_length=100, null=True, blank=True)
    resolved_by = models.CharField(max_length=100, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'fact_query_event'
        verbose_name = 'Query'
        verbose_name_plural = 'Queries'
        ordering = ['-query_open_date']
        indexes = [
            models.Index(fields=['study', 'query_status']),
            models.Index(fields=['site', 'query_status']),
            models.Index(fields=['subject', 'query_status']),
            models.Index(fields=['query_status', 'action_owner']),
            models.Index(fields=['action_owner', 'query_open_date']),
        ]
        permissions = [
            ("view_assigned_queries", "Can view queries for assigned sites only"),
        ]


    def __str__(self):
        return f"Query {self.log_number} - {self.subject.subject_id}"


class SDVStatus(models.Model):
    """
    FACT_SDV_STATUS - Source Data Verification status.

    Architecture Integration:
    - Part of Trial Ops Pod (CRA monitoring activities)
    - Tracks SDV completion for monitoring readiness
    - Feeds into DQI calculation (sdv_incomplete_pct component)

    Business Rules:
    - One row per subject (can be multiple if tracking visits separately)
    - completion_percentage drives "SDV incomplete" blocker in Clean Patient Status
    - CRAs track SDV completion as part of monitoring activities

    Source: CPID_EDC_Metrics 'SDV' sheet
    """

    sdv_id = models.AutoField(primary_key=True)

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='sdv_records'
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='sdv_records'
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='sdv_records'
    )

    # SDV attributes
    sdv_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date SDV was performed"
    )

    status = models.CharField(
        max_length=50,
        help_text="SDV status: Pending, In Progress, Complete"
    )

    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of forms SDV-verified (0-100)"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    verified_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'fact_sdv_status'
        verbose_name = 'SDV Status'
        verbose_name_plural = 'SDV Statuses'


class PISignatureStatus(models.Model):
    """
    FACT_PI_SIGNATURE_STATUS - Principal Investigator signature status.

    Architecture Integration:
    - Part of Clinical Data Pod (form completion tracking)
    - Signature events recorded on blockchain (Phase 7)
    - Feeds into DQI calculation (pi_signature_incomplete_pct)

    Blockchain Integration:
    - PI signature is critical event → recorded as "PI/A approval signed"
    - Transaction hash stored in signature_tx_hash field

    Business Rules:
    - Tracks PI signature completion for regulatory compliance
    - 100% completion required for database lock
    - Feeds "PI signature incomplete" blocker in Clean Patient Status

    Source: CPID_EDC_Metrics 'PI Signature Report' sheet
    """

    signature_id = models.AutoField(primary_key=True)

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='pi_signatures'
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='pi_signatures'
    )

    # Signature attributes
    signed_by = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text="PI username who signed"
    )

    signed_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date signature was completed"
    )

    status = models.CharField(
        max_length=50,
        help_text="Signature status: Pending, Signed"
    )

    completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of required signatures completed (0-100)"
    )

    # Blockchain integration (Phase 7)
    signature_tx_hash = models.CharField(
        max_length=66,
        null=True,
        blank=True,
        help_text="Blockchain transaction hash for PI signature event"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_pi_signature_status'
        verbose_name = 'PI Signature Status'
        verbose_name_plural = 'PI Signature Statuses'


class ProtocolDeviation(models.Model):
    """
    FACT_PROTOCOL_DEVIATION - Protocol deviations and violations.

    Architecture Integration:
    - Part of Trial Ops Pod (compliance tracking)
    - GenAI analyzes deviation severity and suggests corrective actions (Phase 5)
    - Serious deviations trigger blockchain proof recording

    Business Rules:
    - Tracks protocol non-compliance events
    - Severity determines regulatory impact
    - Resolution required before database lock

    Source: CPID_EDC_Metrics 'Protocol Deviation' sheet
    """

    deviation_id = models.AutoField(primary_key=True)

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='protocol_deviations'
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='protocol_deviations'
    )

    # Deviation attributes
    deviation_type = models.CharField(
        max_length=200,
        help_text="Type of protocol deviation"
    )

    status = models.CharField(
        max_length=50,
        help_text="Status: Open, Under Review, Resolved"
    )

    severity = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Severity: Minor, Major, Critical"
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text="Detailed description of deviation"
    )

    # Dates
    deviation_date = models.DateField(
        help_text="Date deviation occurred"
    )

    resolution_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date deviation was resolved"
    )

    # GenAI integration (Phase 5)
    ai_severity_assessment = models.TextField(
        null=True,
        blank=True,
        help_text="AI-generated severity assessment and recommendations"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reported_by = models.CharField(max_length=100, null=True, blank=True)
    resolved_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'fact_protocol_deviation'
        verbose_name = 'Protocol Deviation'
        verbose_name_plural = 'Protocol Deviations'


class NonConformantEvent(models.Model):
    """
    FACT_NONCONFORMANT_EVENT - Non-conformant data events.

    Architecture Integration:
    - Detected by Validation + Workflow Engine (data quality rules)
    - Feeds into DQI calculation (non_conformant_count component)
    - Resolution tracked in Audit Artifacts Store

    Business Rules:
    - Represents data that doesn't conform to edit checks/validation rules
    - Must be resolved before form lock
    - Feeds "non-conformant" blocker in Clean Patient Status

    Source: CPID_EDC_Metrics 'Non conformant' sheet
    """

    event_id = models.AutoField(primary_key=True)

    # Foreign keys
    page = models.ForeignKey(
        FormPage,
        on_delete=models.CASCADE,
        related_name='nonconformant_events'
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='nonconformant_events'
    )

    # Event attributes
    issue_type = models.CharField(
        max_length=200,
        help_text="Type of non-conformance (e.g., 'Out of range', 'Missing required')"
    )

    severity = models.CharField(
        max_length=50,
        help_text="Severity: Low, Medium, High"
    )

    status = models.CharField(
        max_length=50,
        help_text="Status: Open, Resolved, Overridden"
    )

    description = models.TextField(
        null=True,
        blank=True,
        help_text="Description of non-conformance"
    )

    # Dates
    detected_date = models.DateField(
        help_text="Date non-conformance was detected"
    )

    resolution_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date issue was resolved"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'fact_nonconformant_event'
        verbose_name = 'Non-Conformant Event'
        verbose_name_plural = 'Non-Conformant Events'


class MissingVisit(models.Model):
    """
    FACT_MISSING_VISIT - Projected visits that have not occurred.

    Architecture Integration:
    - Calculated by Validation + Workflow Engine (projected vs actual)
    - Feeds "Overdue Visit Queue" in CRA dashboard
    - Feeds into DQI calculation (missing_visits_days_overdue component)
    - Tasking + Workflow Automation creates follow-up tasks

    Business Rules:
    - Represents visits that are past projected date but not completed
    - Days_outstanding tracks urgency for follow-up
    - Feeds "missing visits" blocker in Clean Patient Status

    Source: Visit Projection Tracker
    """

    missing_visit_id = models.AutoField(primary_key=True)

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='missing_visits',
        null=True,
        blank=True
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='missing_visits',
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='missing_visits'
    )

    # Visit identification
    visit_name = models.CharField(
        max_length=200,
        help_text="Name of missing visit (e.g., 'Week 4', 'Month 6')"
    )

    projected_date = models.DateField(
        help_text="Date visit was originally projected/scheduled"
    )

    days_outstanding = models.IntegerField(
        default=0,
        help_text="Number of days past projected date (urgency metric)"
    )

    # Resolution tracking
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this missing visit has been resolved"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_missing_visit'
        verbose_name = 'Missing Visit'
        verbose_name_plural = 'Missing Visits'
        unique_together = [['subject', 'visit_name']]
        ordering = ['-days_outstanding']
        indexes = [
            models.Index(fields=['subject', 'days_outstanding']),
            models.Index(fields=['site', 'is_resolved']),
        ]


class MissingPage(models.Model):
    """
    FACT_MISSING_PAGE - Missing CRF pages at visit/page level.

    Architecture Integration:
    - Calculated by Validation + Workflow Engine
    - Feeds "Missing Page Queue" in CRA dashboard
    - Feeds into DQI calculation (missing_pages_count component)

    Business Rules:
    - Represents CRF pages expected but not entered
    - Days_missing tracks data entry delay
    - Feeds "missing pages" blocker in Clean Patient Status

    Source: Missing Pages Report (URSV3.0)
    """

    missing_page_id = models.AutoField(primary_key=True)

    # Foreign keys
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='missing_pages',
        null=True,
        blank=True
    )

    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='missing_pages',
        null=True,
        blank=True
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='missing_pages'
    )

    # Page identification
    visit_name = models.CharField(
        max_length=200,
        help_text="Visit where page is missing"
    )

    page_name = models.CharField(
        max_length=200,
        help_text="Name of missing CRF page"
    )

    form_details = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Additional form details from source report"
    )

    visit_date = models.DateField(
        null=True,
        blank=True,
        help_text="Visit date when page was expected"
    )

    subject_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Subject status at time of missing page"
    )

    days_missing = models.IntegerField(
        default=0,
        help_text="Number of days page has been missing (urgency metric)"
    )

    # Resolution tracking
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this missing page has been resolved"
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_missing_page'
        verbose_name = 'Missing Page'
        verbose_name_plural = 'Missing Pages'
        ordering = ['-days_missing']
        indexes = [
            models.Index(fields=['subject', 'days_missing']),
            models.Index(fields=['site', 'is_resolved']),
        ]

