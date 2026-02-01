"""
Django admin configuration for safety models.
"""

from django.contrib import admin
from .models import LabIssue, SAEDiscrepancy


@admin.register(LabIssue)
class LabIssueAdmin(admin.ModelAdmin):
    list_display = ['lab_issue_id', 'subject', 'visit_name', 'test_name', 'issue', 'lab_date']
    list_filter = ['issue', 'study', 'site']
    search_fields = ['subject__subject_external_id', 'test_name']


@admin.register(SAEDiscrepancy)
class SAEDiscrepancyAdmin(admin.ModelAdmin):
    list_display = ['sae_id', 'subject', 'discrepancy_id', 'resolution_status', 'case_status', 'discrepancy_created_timestamp']
    list_filter = ['resolution_status', 'case_status', 'study', 'site']
    search_fields = ['discrepancy_id', 'subject__subject_external_id']
