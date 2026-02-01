"""
Django admin configuration for metrics models.
"""

from django.contrib import admin
from .models import DQIWeightConfig, CleanPatientStatus, DQIScoreSubject, DQIScoreSite, DQIScoreStudy


@admin.register(DQIWeightConfig)
class DQIWeightConfigAdmin(admin.ModelAdmin):
    list_display = ['config_id', 'metric_name', 'weight', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['metric_name', 'description']


@admin.register(CleanPatientStatus)
class CleanPatientStatusAdmin(admin.ModelAdmin):
    list_display = ['clean_status_id', 'subject', 'is_clean', 'last_computed']
    list_filter = ['is_clean']
    search_fields = ['subject__subject_external_id']


@admin.register(DQIScoreSubject)
class DQIScoreSubjectAdmin(admin.ModelAdmin):
    list_display = ['dqi_subject_id', 'subject', 'composite_dqi_score', 'risk_band', 'last_computed']
    list_filter = ['risk_band']
    search_fields = ['subject__subject_external_id']


@admin.register(DQIScoreSite)
class DQIScoreSiteAdmin(admin.ModelAdmin):
    list_display = ['dqi_site_id', 'site', 'composite_dqi_score', 'risk_band', 'last_computed']
    list_filter = ['risk_band']
    search_fields = ['site__site_number']


@admin.register(DQIScoreStudy)
class DQIScoreStudyAdmin(admin.ModelAdmin):
    list_display = ['dqi_study_id', 'study', 'composite_dqi_score', 'readiness_status', 'last_computed']
    list_filter = ['readiness_status']
    search_fields = ['study__study_name']

