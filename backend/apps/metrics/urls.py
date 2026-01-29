"""
URL configuration for metrics app.
Handles DQI scores, clean patient status, risk assessments.
"""

from django.urls import path
from . import views

app_name = 'metrics'

urlpatterns = [
    # Metrics endpoints (will be implemented in Phase 2/4)
    # path('dqi/subject/<str:subject_id>/', views.subject_dqi, name='subject_dqi'),
    # path('dqi/site/<str:site_id>/', views.site_dqi, name='site_dqi'),
    # path('clean-status/', views.clean_status_list, name='clean_status_list'),
]
