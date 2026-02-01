"""
Predictive AI API Views for Clinical Trial Control Tower.

This module provides REST API endpoints for machine learning-based
predictions including dropout risk, query resolution time, enrollment
forecasting, and site performance prediction.

API Endpoints:
- GET /api/v1/predictions/dropout-risk/ - Subject dropout risk
- GET /api/v1/predictions/query-resolution-time/ - Query resolution prediction
- GET /api/v1/predictions/enrollment-forecast/ - Enrollment trend forecast
- GET /api/v1/predictions/site-performance/ - Site DQI prediction
- GET /api/v1/predictions/batch-risk/ - Batch risk predictions

Architecture Integration:
- Predictive AI Platform component
- Model Registry (trained models in ML_MODELS_DIR)
- Feature engineering from Data Pods
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .ml_models import PredictiveMLService


@api_view(['GET'])
def predict_dropout_risk(request):
    """
    Predict subject dropout risk.
    
    Purpose: Uses ML model to predict the likelihood that a subject
             will drop out of the clinical trial.
    
    Inputs (query parameters):
        - subject_id: Required. The ID of the subject to analyze
    
    Outputs: JSON object containing:
        - risk_probability: Float (0-1) dropout probability
        - risk_level: Classification (Low/Medium/High)
        - confidence: Model confidence score
        - top_drivers: Top 3 features contributing to risk
    
    Side effects:
        - Database read to fetch subject features
        - Uses pre-trained ML model (if available)
    
    Usage: GET /api/v1/predictions/dropout-risk/?subject_id=Study_1_0-001
    """
    # Extract and validate subject_id parameter
    subject_id = request.query_params.get('subject_id')

    # Subject ID is required for prediction
    if not subject_id:
        return Response(
            {'error': 'subject_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Initialize ML service and generate prediction
    service = PredictiveMLService()
    prediction = service.predict_dropout_risk(subject_id)

    return Response(prediction)


@api_view(['GET'])
def predict_query_resolution_time(request):
    """
    Predict query resolution time.
    
    Purpose: Uses ML model to predict how many days until a query
             is likely to be resolved, based on historical patterns.
    
    Inputs (query parameters):
        - query_id: Required. The ID of the query to analyze
    
    Outputs: JSON object containing:
        - predicted_resolution_days: Estimated days to resolution
        - current_days_open: Current age of query in days
        - action_owner: Who is responsible for the query
    
    Side effects:
        - Database read to fetch query details
        - Uses pre-trained ML model (if available)
    
    Usage: GET /api/v1/predictions/query-resolution-time/?query_id=123
    """
    # Extract and validate query_id parameter
    query_id = request.query_params.get('query_id')

    # Query ID is required for prediction
    if not query_id:
        return Response(
            {'error': 'query_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Initialize ML service and generate prediction
    service = PredictiveMLService()
    prediction = service.predict_query_resolution_time(int(query_id))

    return Response(prediction)


@api_view(['GET'])
def enrollment_forecast(request):
    """
    Get enrollment forecast for a study.
    
    Purpose: Generates historical enrollment analysis and projects
             future enrollment based on current trends using time-series
             analysis.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
        - months: Months to forecast ahead (default: 6)
    
    Outputs: JSON object containing:
        - historical: Array of historical enrollment data points
        - forecast: Array of forecasted monthly enrollments
        - average_monthly_rate: Average enrollment rate
        - projected_completion: Estimated completion date
    
    Side effects:
        - Database read to fetch enrollment history
    
    Usage: GET /api/v1/predictions/enrollment-forecast/?study_id=Study_1&months=6
    """
    # Extract query parameters with defaults
    study_id = request.query_params.get('study_id', 'Study_1')
    
    # Validate and parse months parameter
    try:
        months_ahead = int(request.query_params.get('months', 6))
        months_ahead = max(1, min(months_ahead, 24))  # Clamp between 1 and 24
    except ValueError:
        months_ahead = 6

    # Initialize ML service and generate forecast
    service = PredictiveMLService()
    forecast = service.forecast_enrollment(study_id, months_ahead)

    return Response(forecast)


@api_view(['GET'])
def predict_site_performance(request):
    """
    Predict site performance (DQI score).
    
    Purpose: Predicts future DQI score for a site based on current
             performance metrics and historical patterns.
    
    Inputs (query parameters):
        - site_number: Required. The site number to analyze
        - study_id: Study identifier (default: 'Study_1')
    
    Outputs: JSON object containing:
        - predicted_dqi_score: Forecasted DQI score
        - predicted_risk_band: Expected risk classification
        - current_metrics: Current site performance data
    
    Side effects:
        - Database read to fetch site metrics
        - Uses pre-trained ML model (if available)
    
    Usage: GET /api/v1/predictions/site-performance/?site_number=001&study_id=Study_1
    """
    # Extract and validate parameters
    site_number = request.query_params.get('site_number')
    study_id = request.query_params.get('study_id', 'Study_1')

    # Site number is required for prediction
    if not site_number:
        return Response(
            {'error': 'site_number required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Initialize ML service and generate prediction
    service = PredictiveMLService()
    prediction = service.predict_site_performance(site_number, study_id)

    return Response(prediction)


@api_view(['GET'])
def batch_risk_predictions(request):
    """
    Get dropout risk predictions for multiple subjects at once.
    
    Purpose: Efficiently generates risk predictions for the top N
             at-risk subjects in a study, useful for prioritization.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
        - limit: Maximum subjects to analyze (default: 10)
    
    Outputs: JSON object containing:
        - predictions: Array of subject predictions with risk scores
        - count: Number of predictions returned
    
    Side effects:
        - Database reads to fetch at-risk subjects
        - ML model invocations for each subject
    
    Usage: GET /api/v1/predictions/batch-risk/?study_id=Study_1&limit=10
    """
    # Extract query parameters with defaults
    study_id = request.query_params.get('study_id', 'Study_1')
    
    # Validate and parse limit parameter
    try:
        limit = int(request.query_params.get('limit', 10))
        limit = max(1, min(limit, 50))  # Clamp between 1 and 50
    except ValueError:
        limit = 10

    # Import models for querying (local import to avoid circular dependency)
    from apps.core.models import Subject
    from apps.metrics.models import DQIScoreSubject

    try:
        # Get subjects with highest risk (lowest DQI scores)
        # Filter for High and Critical risk bands only
        at_risk_subjects = DQIScoreSubject.objects.filter(
            subject__study_id=study_id,
            risk_band__in=['High', 'Critical']
        ).select_related('subject').order_by('composite_dqi_score')[:limit]

        # Generate predictions for each at-risk subject
        service = PredictiveMLService()
        predictions = []

        # Iterate through at-risk subjects and generate predictions
        for dqi in at_risk_subjects:
            pred = service.predict_dropout_risk(dqi.subject.subject_id)
            
            # Only include successful predictions
            if 'error' not in pred:
                predictions.append(pred)

        return Response({
            'predictions': predictions,
            'count': len(predictions)
        })

    except Exception as e:
        # Return empty data with informative message on failure
        return Response({
            'predictions': [],
            'count': 0,
            'message': 'No predictions available. Ensure models are trained and data exists.'
        })
