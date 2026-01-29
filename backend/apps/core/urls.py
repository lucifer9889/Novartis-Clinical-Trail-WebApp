"""
URL configuration for core app.
Handles main dashboards, home page, and study navigation.
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Home and navigation
    path('', views.home, name='home'),

    # Dashboards (will be implemented in Phase 1/4)
    # path('dashboards/cra/', views.cra_dashboard, name='cra_dashboard'),
    # path('dashboards/dqt/', views.dqt_dashboard, name='dqt_dashboard'),
    # path('dashboards/site/<str:site_id>/', views.site_dashboard, name='site_dashboard'),
    # path('dashboards/leadership/', views.leadership_dashboard, name='leadership_dashboard'),
]
