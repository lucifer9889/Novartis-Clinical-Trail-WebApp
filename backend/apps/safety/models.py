"""
Safety and lab issue models.

Architecture Integration:
- Safety Pod → SAE discrepancy tracking (Pg/Pg-reports only)
- Lab Pod → Lab test issues (LIMS outputs)
- Both feed into DQI calculation via KPI + Analytics Service
"""

from django.db import models
from apps.core.models import Study, Site, Subject


class LabIssue(models.Model):
    """
    FACT_LAB_ISSUE - Lab name/range/unit issues.

    Architecture: Lab Pod (LIMS outputs)
    Tracks lab test data quality issues requiring resolution.
    """

    ISSUE_CHOICES = [
        ('Missing Lab Name', 'Missing Lab Name'),
        ('Missing Ranges', 'Missing Ranges'),
        ('Missing Units', 'Missing Units'),
    ]

    lab_issue_id = models.AutoField(primary_key=True)
    
    # Foreign keys (per ER diagram)
    study = models.ForeignKey(
        Study,
        on_delete=models.CASCADE,
        related_name='lab_issues',
        null=True,
        blank=True
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name='lab_issues',
        null=True,
        blank=True
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='lab_issues'
    )
    
    visit_name = models.CharField(max_length=200)
    form_name = models.CharField(max_length=200)
    lab_category = models.CharField(max_length=200)
    lab_date = models.DateField(null=True, blank=True)
    test_name = models.CharField(max_length=200)
    test_description = models.CharField(max_length=500, null=True, blank=True)
    issue = models.CharField(max_length=100, choices=ISSUE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = 'fact_lab_issue'
        verbose_name = 'Lab Issue'
        verbose_name_plural = 'Lab Issues'


class SAEDiscrepancy(models.Model):
    """
    FACT_SAE_DISCREPANCY - Serious Adverse Event discrepancies.

    Architecture: Safety Pod (Pg/Pg-reports only)
    HIGHEST SEVERITY BLOCKER - Unresolved SAE discrepancies have weight 0.25 in DQI.
    """

    RESOLUTION_STATUS_CHOICES = [
        ('Open', 'Open'),
        ('Pending', 'Pending'),
        ('Resolved', 'Resolved'),
        ('Closed', 'Closed'),
    ]

    sae_id = models.AutoField(primary_key=True)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='sae_discrepancies')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='sae_discrepancies')
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='sae_discrepancies')

    discrepancy_id = models.CharField(max_length=100)
    form_name = models.CharField(max_length=200, null=True, blank=True)
    
    # Resolution tracking (per ER diagram)
    resolution_status = models.CharField(
        max_length=50,
        choices=RESOLUTION_STATUS_CHOICES,
        default='Open',
        help_text="Current resolution status"
    )
    
    review_status_dm = models.CharField(max_length=50, null=True, blank=True)
    action_status_dm = models.CharField(max_length=50, null=True, blank=True)
    case_status = models.CharField(max_length=50, null=True, blank=True)
    review_status_safety = models.CharField(max_length=50, null=True, blank=True)
    action_status_safety = models.CharField(max_length=50, null=True, blank=True)
    discrepancy_created_timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_sae_discrepancy'
        unique_together = [['discrepancy_id', 'subject']]
        verbose_name = 'SAE Discrepancy'
        verbose_name_plural = 'SAE Discrepancies'
        indexes = [
            models.Index(fields=['site', 'resolution_status']),
        ]

