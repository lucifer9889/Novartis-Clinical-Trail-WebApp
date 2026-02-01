"""
Django admin configuration for core models.

Provides admin interface for managing:
- Studies, Countries, Sites, Subjects
- Visits, FormPages
"""

from django.contrib import admin
from .models import Study, Country, Site, Subject, Visit, FormPage


@admin.register(Study)
class StudyAdmin(admin.ModelAdmin):
    list_display = ['study_id', 'study_name', 'status', 'region', 'snapshot_date']
    list_filter = ['status', 'region']
    search_fields = ['study_id', 'study_name']
    ordering = ['study_id']


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['country_code', 'country_name', 'region', 'study']
    list_filter = ['region', 'study']
    search_fields = ['country_code', 'country_name']
    ordering = ['region', 'country_name']


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ['site_id', 'site_number', 'site_name', 'country', 'status', 'assigned_cra']
    list_filter = ['status', 'country', 'study']
    search_fields = ['site_id', 'site_number', 'site_name']
    ordering = ['site_number']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['subject_id', 'subject_external_id', 'site', 'subject_status', 'enrollment_date']
    list_filter = ['subject_status', 'site__country', 'site__study']
    search_fields = ['subject_id', 'subject_external_id']
    ordering = ['site', 'subject_external_id']


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['visit_id', 'subject', 'visit_name', 'visit_date', 'projected_date', 'status']
    list_filter = ['status', 'subject__site']
    search_fields = ['visit_name', 'subject__subject_external_id']
    ordering = ['subject', 'projected_date']


@admin.register(FormPage)
class FormPageAdmin(admin.ModelAdmin):
    list_display = ['page_id', 'visit', 'folder_name', 'form_name', 'page_name', 'status']
    list_filter = ['status', 'folder_name']
    search_fields = ['form_name', 'page_name']
    ordering = ['visit', 'folder_name', 'form_name']
