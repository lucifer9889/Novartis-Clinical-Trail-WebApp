"""
URL configuration for ai_services app.
Handles GenAI assistance and predictive models (Phase 5/6).
"""

from django.urls import path
from . import views

app_name = 'ai_services'

urlpatterns = [
    # AI endpoints (will be implemented in Phase 5/6)
    # path('query-assist/', views.query_assist, name='query_assist'),
    # path('predict/site-risk/', views.predict_site_risk, name='predict_site_risk'),
]
