"""
URL configuration for monitoring app.
Handles queries, SDV, PI signatures, protocol deviations.
"""

from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Monitoring endpoints (will be implemented in Phase 2/4)
    # path('queries/', views.query_list, name='query_list'),
    # path('queries/<int:query_id>/', views.query_detail, name='query_detail'),
    # path('sdv/', views.sdv_list, name='sdv_list'),
]
