"""
Medical coding and EDRR models.

Architecture Integration:
- Medical coding feeds downstream analysis readiness
- EDRR tracks external data reconciliation issues
"""

from django.db import models
from apps.core.models import Study, Subject


class CodingItem(models.Model):
    """
    FACT_CODING_ITEM - MedDRA/WHODD coding status.

    Tracks medical terminology coding backlog.
    """

    DICTIONARY_CHOICES = [
        ('MedDRA', 'MedDRA'),
        ('WHODD', 'WHODD'),
    ]

    coding_id = models.AutoField(primary_key=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='coding_items')
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='coding_items')
    dictionary_name = models.CharField(max_length=50, choices=DICTIONARY_CHOICES)
    dictionary_version = models.CharField(max_length=50, null=True, blank=True)
    form_oid = models.CharField(max_length=200)
    logline = models.CharField(max_length=200, null=True, blank=True)
    field_oid = models.CharField(max_length=200, null=True, blank=True)
    coding_status = models.CharField(max_length=50)
    require_coding = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_coding_item'
        verbose_name = 'Coding Item'
        verbose_name_plural = 'Coding Items'


class EDRROpenIssue(models.Model):
    """
    FACT_EDRR_OPEN_ISSUE - External Data Reconciliation Report issues.

    Tracks open issues from 3rd-party data reconciliation.
    """

    edrr_id = models.AutoField(primary_key=True)
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='edrr_issues')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='edrr_issues')
    total_open_issue_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_edrr_open_issue'
        unique_together = [['study', 'subject']]
        verbose_name = 'EDRR Open Issue'
        verbose_name_plural = 'EDRR Open Issues'


class InactivatedRecord(models.Model):
    """
    FACT_INACTIVATED_RECORD - Inactivated forms/folders/records.

    Audit log of inactivated data for cleanup context.
    """

    inactivated_id = models.AutoField(primary_key=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='inactivated_records')
    folder_name = models.CharField(max_length=200, null=True, blank=True)
    form_name = models.CharField(max_length=200)
    data_on_form = models.CharField(max_length=500, null=True, blank=True)
    record_position = models.CharField(max_length=50, null=True, blank=True)
    audit_action = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'fact_inactivated_record'
        verbose_name = 'Inactivated Record'
        verbose_name_plural = 'Inactivated Records'
