"""
API URL Configuration for Clinical Trial Control Tower.

This module defines the URL patterns for the core REST API endpoints.
All routes here are prefixed with /api/v1/ from the main urls.py.

Endpoints:
- GET /api/v1/role-visibility/ - Subject listing with filters
- GET /api/v1/frontend-overview/ - KPI dashboard data
- GET /api/v1/study-summary/ - Study-level summary
- GET /api/v1/sites/ - Site listing
- GET /api/v1/at-risk-subjects/ - High/Critical risk subjects
- GET /api/v1/risk-heatmap/ - Site risk heatmap data
- GET /api/v1/user-context/ - Current user context with role/permissions
- GET /api/v1/health/ - API health check
"""

from django.urls import path
from . import views

# URL patterns for the core API
# Each path maps to a view function in views.py
urlpatterns = [
    # Dashboard data endpoints - provide data for frontend dashboards
    path('role-visibility/', views.role_visibility_data, name='api-role-visibility'),
    path('frontend-overview/', views.frontend_overview_data, name='api-frontend-overview'),
    
    # Study and site data endpoints
    path('study-summary/', views.study_summary, name='api-study-summary'),
    path('sites/', views.site_list, name='api-sites'),
    
    # Risk analysis endpoints
    path('at-risk-subjects/', views.at_risk_subjects, name='api-at-risk-subjects'),
    path('risk-heatmap/', views.risk_heatmap_data, name='api-risk-heatmap'),
    
    # User context endpoint (role-based visibility data)
    path('user-context/', views.user_context, name='api-user-context'),
]

