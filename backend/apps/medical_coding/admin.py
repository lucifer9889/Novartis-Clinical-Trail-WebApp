"""
Django admin configuration for medical_coding models.
"""

from django.contrib import admin
from .models import CodingItem, EDRROpenIssue, InactivatedRecord


@admin.register(CodingItem)
class CodingItemAdmin(admin.ModelAdmin):
    list_display = ['coding_id', 'subject', 'dictionary_name', 'coding_status', 'require_coding']
    list_filter = ['dictionary_name', 'coding_status', 'require_coding', 'study']
    search_fields = ['subject__subject_external_id', 'form_oid']


@admin.register(EDRROpenIssue)
class EDRROpenIssueAdmin(admin.ModelAdmin):
    list_display = ['edrr_id', 'study', 'subject', 'total_open_issue_count', 'updated_at']
    list_filter = ['study']
    search_fields = ['subject__subject_external_id']


@admin.register(InactivatedRecord)
class InactivatedRecordAdmin(admin.ModelAdmin):
    list_display = ['inactivated_id', 'subject', 'folder_name', 'form_name', 'audit_action']
    list_filter = ['study', 'site']
    search_fields = ['subject__subject_external_id', 'form_name']
