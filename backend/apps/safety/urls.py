"""
URL configuration for safety app.
Handles SAE discrepancies, lab issues.
"""

from django.urls import path
from . import views

app_name = 'safety'

urlpatterns = [
    # Safety endpoints (will be implemented in Phase 2/4)
    # path('sae/', views.sae_list, name='sae_list'),
    # path('lab-issues/', views.lab_issue_list, name='lab_issue_list'),
]
