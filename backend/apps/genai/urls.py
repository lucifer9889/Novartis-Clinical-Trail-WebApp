"""
GenAI API URL Configuration for Clinical Trial Control Tower.

This module defines URL patterns for the GenAI (AI-powered suggestions)
REST API endpoints. All routes here are prefixed with /api/v1/genai/
from the main urls.py.

API Endpoints:
- GET /api/v1/genai/suggested-actions/ - AI-generated action recommendations
- GET /api/v1/genai/query-suggestion/ - Query response suggestions
- GET /api/v1/genai/risk-assessment/ - Subject risk assessment
- GET /api/v1/genai/status/ - AI configuration status check

Integration: Uses Anthropic Claude for AI inference.
Requires ANTHROPIC_API_KEY environment variable.
AI features gracefully degrade when key is not configured.
"""

from django.urls import path
from . import views

# URL patterns for GenAI API
# Each endpoint provides AI-powered insights for clinical trial operations
urlpatterns = [
    # AI configuration status check
    path('status/', views.ai_status, name='genai-status'),
    
    # AI-generated action recommendations for CRAs/DQT
    path('suggested-actions/', views.suggested_actions, name='genai-suggested-actions'),
    
    # Query response suggestion based on query context
    path('query-suggestion/', views.query_suggestion, name='genai-query-suggestion'),
    
    # Comprehensive subject risk assessment
    path('risk-assessment/', views.risk_assessment, name='genai-risk-assessment'),
]
