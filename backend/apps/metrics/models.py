"""
Metrics and mart models for DQI and Clean Patient Status.

Architecture Integration:
- KPI + Analytics Service → Computes DQI and Clean Status
- Pre-aggregated dashboards → Fast performance via caching
- Feeds all role-based dashboards (CRA, DQT, Site, Leadership)

Reference: NEST2 Project Document Section 9 (DQI and Clean Patient Status)
"""

from django.db import models
from apps.core.models import Study, Site, Subject
import json


class DQIWeightConfig(models.Model):
    """
    DQI_WEIGHT_CONFIG - Data Quality Index weight configuration.

    Stores configurable weights for DQI calculation.

    Default weights from Project Document Section 9.3:
    - sae_unresolved_count: 0.25 (highest - hard blocker)
    - missing_visits_days_overdue: 0.15
    - open_queries_count: 0.15
    - missing_pages_count: 0.10
    - non_conformant_count: 0.10
    - sdv_incomplete_pct: 0.10
    - pi_signature_incomplete_pct: 0.05
    - coding_uncoded_count: 0.05
    - edrr_open_issue_count: 0.05
    Total: 1.00
    """

    config_id = models.AutoField(primary_key=True)
    metric_name = models.CharField(max_length=100, unique=True)
    weight = models.DecimalField(max_digits=5, decimal_places=3)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'dqi_weight_config'
        verbose_name = 'DQI Weight Configuration'
        verbose_name_plural = 'DQI Weight Configurations'


class CleanPatientStatus(models.Model):
    """
    MART_CLEAN_PATIENT_STATUS - Clean patient status with blockers.

    Architecture: Computed by KPI + Analytics Service

    Clean Patient Criteria (ALL must be satisfied):
    1. has_missing_visits = False (0 missing visits)
    2. has_missing_pages = False (0 missing pages)
    3. has_open_queries = False (0 open queries)
    4. has_non_conformant = False (0 non-conformant events)
    5. has_sae_discrepancies = False (0 unresolved SAE)
    6. sdv_incomplete = False (100% SDV complete)
    7. pi_signature_incomplete = False (100% PI signed)
    8. (Optional) has_coding_backlog = False
    9. (Optional) has_edrr_issues = False

    If ANY blocker is True → is_clean = False
    blockers_json contains structured list for dashboard display
    """

    clean_status_id = models.AutoField(primary_key=True)
    subject = models.OneToOneField(Subject, on_delete=models.CASCADE, related_name='clean_status')

    # Overall status
    is_clean = models.BooleanField(default=False)

    # Blocker flags
    has_missing_visits = models.BooleanField(default=False)
    missing_visits_count = models.IntegerField(default=0)

    has_missing_pages = models.BooleanField(default=False)
    missing_pages_count = models.IntegerField(default=0)

    has_open_queries = models.BooleanField(default=False)
    open_queries_count = models.IntegerField(default=0)

    has_non_conformant = models.BooleanField(default=False)
    non_conformant_count = models.IntegerField(default=0)

    has_sae_discrepancies = models.BooleanField(default=False)
    sae_discrepancy_count = models.IntegerField(default=0)

    sdv_incomplete = models.BooleanField(default=False)
    sdv_completion_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    pi_signature_incomplete = models.BooleanField(default=False)
    pi_signature_completion_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    has_coding_backlog = models.BooleanField(default=False)
    coding_uncoded_count = models.IntegerField(default=0)

    has_edrr_issues = models.BooleanField(default=False)
    edrr_open_issue_count = models.IntegerField(default=0)

    # Structured blockers JSON for UI
    blockers_json = models.TextField(null=True, blank=True)

    # Metadata
    last_computed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mart_clean_patient_status'
        verbose_name = 'Clean Patient Status'
        verbose_name_plural = 'Clean Patient Statuses'

    def get_blockers_list(self):
        """Parse blockers_json and return Python list."""
        if self.blockers_json:
            try:
                return json.loads(self.blockers_json)
            except:
                return []
        return []


class DQIScoreSubject(models.Model):
    """
    MART_DQI_SCORE_SUBJECT - Data Quality Index at subject level.

    Architecture: Computed by KPI + Analytics Service

    DQI Calculation Process:
    1. For each component, calculate raw score (normalized 0-100)
    2. Multiply by weight from DQI_WEIGHT_CONFIG
    3. Sum weighted scores → composite_dqi_score
    4. Assign risk_band based on thresholds

    Risk Bands (from Project Document Section 9):
    - Low: composite_dqi_score < 25
    - Medium: 25 ≤ composite_dqi_score < 50
    - High: 50 ≤ composite_dqi_score < 75
    - Critical: composite_dqi_score ≥ 75
    """

    RISK_BAND_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
        ('Critical', 'Critical'),
    ]

    dqi_subject_id = models.AutoField(primary_key=True)
    subject = models.OneToOneField(Subject, on_delete=models.CASCADE, related_name='dqi_score')

    # Component scores (0-100, lower is better)
    sae_unresolved_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    missing_visits_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    missing_pages_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    open_queries_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    non_conformant_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    sdv_incomplete_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pi_signature_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    coding_backlog_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    edrr_issue_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Weighted composite DQI (0-100, lower is better)
    composite_dqi_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    risk_band = models.CharField(max_length=20, choices=RISK_BAND_CHOICES, default='Low')

    # Metadata
    last_computed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mart_dqi_score_subject'
        verbose_name = 'DQI Score (Subject)'
        verbose_name_plural = 'DQI Scores (Subject)'


class DQIScoreSite(models.Model):
    """
    MART_DQI_SCORE_SITE - Aggregated DQI at site level.

    Architecture: Rolled up from subject-level DQI scores
    Feeds site leaderboard in DQT dashboard
    """

    dqi_site_id = models.AutoField(primary_key=True)
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name='dqi_score')
    total_subjects = models.IntegerField(default=0)
    clean_subjects = models.IntegerField(default=0)
    clean_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    composite_dqi_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    risk_band = models.CharField(max_length=20, default='Low')
    last_computed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mart_dqi_score_site'
        verbose_name = 'DQI Score (Site)'
        verbose_name_plural = 'DQI Scores (Site)'


class DQIScoreStudy(models.Model):
    """
    MART_DQI_SCORE_STUDY - Aggregated DQI at study level.

    Architecture: Rolled up from site-level DQI scores
    Feeds leadership dashboard with study readiness
    """

    dqi_study_id = models.AutoField(primary_key=True)
    study = models.OneToOneField(Study, on_delete=models.CASCADE, related_name='dqi_score')
    total_sites = models.IntegerField(default=0)
    total_subjects = models.IntegerField(default=0)
    clean_subjects = models.IntegerField(default=0)
    clean_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    composite_dqi_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    readiness_status = models.CharField(max_length=50, default='Not Ready')
    last_computed = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mart_dqi_score_study'
        verbose_name = 'DQI Score (Study)'
        verbose_name_plural = 'DQI Scores (Study)'
