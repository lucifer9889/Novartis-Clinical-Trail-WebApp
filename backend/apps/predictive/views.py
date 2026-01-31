"""
Predictive AI API Views.

Endpoints:
- /api/v1/predictions/dropout-risk/
- /api/v1/predictions/query-resolution-time/
- /api/v1/predictions/enrollment-forecast/
- /api/v1/predictions/site-performance/
- /api/v1/predictions/batch-risk/
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .ml_models import PredictiveMLService


@api_view(['GET'])
def predict_dropout_risk(request):
    """
    Predict subject dropout risk.

    GET /api/v1/predictions/dropout-risk/?subject_id=Study_1_0-001

    Returns:
        - risk_probability (0-1)
        - risk_level (Low/Medium/High)
        - confidence score
        - top_drivers (top 3 features)
    """
    subject_id = request.query_params.get('subject_id')

    if not subject_id:
        return Response(
            {'error': 'subject_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service = PredictiveMLService()
    prediction = service.predict_dropout_risk(subject_id)

    return Response(prediction)


@api_view(['GET'])
def predict_query_resolution_time(request):
    """
    Predict query resolution time.

    GET /api/v1/predictions/query-resolution-time/?query_id=123

    Returns:
        - predicted_resolution_days
        - current_days_open
        - action_owner
    """
    query_id = request.query_params.get('query_id')

    if not query_id:
        return Response(
            {'error': 'query_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service = PredictiveMLService()
    prediction = service.predict_query_resolution_time(int(query_id))

    return Response(prediction)


@api_view(['GET'])
def enrollment_forecast(request):
    """
    Get enrollment forecast.

    GET /api/v1/predictions/enrollment-forecast/?study_id=Study_1&months=6

    Returns:
        - historical enrollment data
        - forecast for next N months
        - average monthly rate
    """
    study_id = request.query_params.get('study_id', 'Study_1')
    months_ahead = int(request.query_params.get('months', 6))

    service = PredictiveMLService()
    forecast = service.forecast_enrollment(study_id, months_ahead)

    return Response(forecast)


@api_view(['GET'])
def predict_site_performance(request):
    """
    Predict site performance.

    GET /api/v1/predictions/site-performance/?site_number=001&study_id=Study_1

    Returns:
        - predicted_dqi_score
        - predicted_risk_band
        - current_metrics
    """
    site_number = request.query_params.get('site_number')
    study_id = request.query_params.get('study_id', 'Study_1')

    if not site_number:
        return Response(
            {'error': 'site_number required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    service = PredictiveMLService()
    prediction = service.predict_site_performance(site_number, study_id)

    return Response(prediction)


@api_view(['GET'])
def batch_risk_predictions(request):
    """
    Get dropout risk predictions for multiple subjects at once.

    GET /api/v1/predictions/batch-risk/?study_id=Study_1&limit=10

    Returns top N at-risk subjects with predictions.
    """
    study_id = request.query_params.get('study_id', 'Study_1')
    limit = int(request.query_params.get('limit', 10))

    from apps.core.models import Subject
    from apps.metrics.models import DQIScoreSubject

    # Get subjects with highest risk (lowest DQI scores)
    try:
        at_risk_subjects = DQIScoreSubject.objects.filter(
            subject__study_id=study_id,
            risk_band__in=['High', 'Critical']
        ).select_related('subject').order_by('composite_dqi_score')[:limit]

        service = PredictiveMLService()
        predictions = []

        for dqi in at_risk_subjects:
            pred = service.predict_dropout_risk(dqi.subject.subject_id)
            if 'error' not in pred:
                predictions.append(pred)

        return Response({
            'predictions': predictions,
            'count': len(predictions)
        })

    except Exception as e:
        return Response({
            'predictions': [],
            'count': 0,
            'message': 'No predictions available. Ensure models are trained and data exists.'
        })
