"""GenAI API URLs."""

from django.urls import path
from . import views

urlpatterns = [
    path('suggested-actions/', views.suggested_actions, name='genai-suggested-actions'),
    path('query-suggestion/', views.query_suggestion, name='genai-query-suggestion'),
    path('risk-assessment/', views.risk_assessment, name='genai-risk-assessment'),
]
