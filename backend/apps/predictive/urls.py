"""
Predictive AI API URL Configuration for Clinical Trial Control Tower.

This module defines URL patterns for the Predictive AI (ML-based forecasting)
REST API endpoints. All routes here are prefixed with /api/v1/predictions/
from the main urls.py.

API Endpoints:
- GET /api/v1/predictions/dropout-risk/ - Predict subject dropout probability
- GET /api/v1/predictions/query-resolution-time/ - Predict query resolution days
- GET /api/v1/predictions/enrollment-forecast/ - Forecast enrollment trends
- GET /api/v1/predictions/site-performance/ - Predict site DQI scores
- GET /api/v1/predictions/batch-risk/ - Batch risk predictions

Integration: Uses trained ML models stored in ML_MODELS_DIR.
"""

from django.urls import path
from . import views

# URL patterns for Predictive AI API
# Each endpoint provides ML-powered predictions for clinical trial operations
urlpatterns = [
    # Subject dropout risk prediction (PNN model)
    path('dropout-risk/', views.predict_dropout_risk, name='predict-dropout-risk'),
    
    # Query resolution time prediction (RNN model)
    path('query-resolution-time/', views.predict_query_resolution_time, name='predict-query-time'),
    
    # Enrollment forecast using time-series analysis (LSTM model)
    path('enrollment-forecast/', views.enrollment_forecast, name='enrollment-forecast'),
    
    # Site performance prediction (CNN model)
    path('site-performance/', views.predict_site_performance, name='predict-site-performance'),
    
    # Batch processing for multiple subject risk predictions
    path('batch-risk/', views.batch_risk_predictions, name='batch-risk'),
]
