"""API URL Configuration."""

from django.urls import path
from . import views

urlpatterns = [
    # Dashboard data endpoints
    path('role-visibility/', views.role_visibility_data, name='api-role-visibility'),
    path('frontend-overview/', views.frontend_overview_data, name='api-frontend-overview'),
    path('study-summary/', views.study_summary, name='api-study-summary'),
    path('sites/', views.site_list, name='api-sites'),
    path('at-risk-subjects/', views.at_risk_subjects, name='api-at-risk-subjects'),
]
