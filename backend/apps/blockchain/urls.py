"""
URL configuration for blockchain app.
Handles data verification, audit trails (Phase 7).
"""

from django.urls import path
from . import views

app_name = 'blockchain'

urlpatterns = [
    # Blockchain endpoints (will be implemented in Phase 7)
    # path('verify/<str:entity_type>/<str:entity_id>/', views.verify_data, name='verify_data'),
    # path('audit-trail/<str:entity_id>/', views.audit_trail, name='audit_trail'),
]
