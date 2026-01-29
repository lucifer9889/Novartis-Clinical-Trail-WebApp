"""
URL configuration for medical_coding app.
Handles MedDRA, WHODD coding, EDRR issues.
"""

from django.urls import path
from . import views

app_name = 'medical_coding'

urlpatterns = [
    # Medical coding endpoints (will be implemented in Phase 2/4)
    # path('coding-items/', views.coding_item_list, name='coding_item_list'),
    # path('edrr-issues/', views.edrr_issue_list, name='edrr_issue_list'),
]
