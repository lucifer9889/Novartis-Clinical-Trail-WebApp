"""
Django admin configuration for monitoring models.
"""

from django.contrib import admin
from .models import (
    OpenIssueSummary, CRFEvent, Query, SDVStatus, PISignatureStatus,
    ProtocolDeviation, NonConformantEvent, MissingVisit, MissingPage
)


@admin.register(OpenIssueSummary)
class OpenIssueSummaryAdmin(admin.ModelAdmin):
    list_display = ['id', 'study', 'subject', 'total_open_issue_count', 'updated_at']
    list_filter = ['study']
    search_fields = ['subject__subject_external_id']


@admin.register(CRFEvent)
class CRFEventAdmin(admin.ModelAdmin):
    list_display = ['crf_event_id', 'study', 'event_type', 'event_time', 'subject', 'folder_name']
    list_filter = ['event_type', 'study']
    search_fields = ['subject__subject_external_id', 'folder_name', 'page_name']
    ordering = ['-event_time']


@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ['query_id', 'subject', 'query_status', 'action_owner', 'query_open_date', 'form_name']
    list_filter = ['query_status', 'action_owner', 'study', 'site']
    search_fields = ['log_number', 'subject__subject_external_id', 'form_name']
    ordering = ['-query_open_date']


@admin.register(SDVStatus)
class SDVStatusAdmin(admin.ModelAdmin):
    list_display = ['sdv_id', 'subject', 'site', 'status', 'completion_percentage']
    list_filter = ['status', 'study', 'site']
    search_fields = ['subject__subject_external_id']


@admin.register(PISignatureStatus)
class PISignatureStatusAdmin(admin.ModelAdmin):
    list_display = ['signature_id', 'subject', 'status', 'completion_percentage', 'signed_date']
    list_filter = ['status', 'study']
    search_fields = ['subject__subject_external_id']


@admin.register(ProtocolDeviation)
class ProtocolDeviationAdmin(admin.ModelAdmin):
    list_display = ['deviation_id', 'subject', 'deviation_type', 'severity', 'status']
    list_filter = ['status', 'severity', 'study']
    search_fields = ['subject__subject_external_id', 'deviation_type']


@admin.register(NonConformantEvent)
class NonConformantEventAdmin(admin.ModelAdmin):
    list_display = ['event_id', 'subject', 'issue_type', 'severity', 'status', 'detected_date']
    list_filter = ['severity', 'status']
    search_fields = ['subject__subject_external_id', 'issue_type']



@admin.register(MissingVisit)
class MissingVisitAdmin(admin.ModelAdmin):
    list_display = ['missing_visit_id', 'subject', 'visit_name', 'projected_date', 'days_outstanding', 'is_resolved']
    list_filter = ['is_resolved', 'study', 'site']
    search_fields = ['subject__subject_external_id', 'visit_name']
    ordering = ['-days_outstanding']


@admin.register(MissingPage)
class MissingPageAdmin(admin.ModelAdmin):
    list_display = ['missing_page_id', 'subject', 'visit_name', 'page_name', 'days_missing', 'is_resolved']
    list_filter = ['is_resolved', 'study', 'site']
    search_fields = ['subject__subject_external_id', 'visit_name', 'page_name']
    ordering = ['-days_missing']

