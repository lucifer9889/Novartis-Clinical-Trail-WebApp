"""GenAI API views."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import ClinicalTrialAIService


@api_view(['GET'])
def suggested_actions(request):
    """
    Get AI-generated suggested actions.

    GET /api/v1/genai/suggested-actions/?study_id=Study_1&limit=3
    """
    study_id = request.query_params.get('study_id', 'Study_1')
    limit = int(request.query_params.get('limit', 3))

    ai_service = ClinicalTrialAIService()
    actions = ai_service.generate_suggested_actions(study_id, limit)

    return Response({
        'actions': actions,
        'study_id': study_id
    })


@api_view(['GET'])
def query_suggestion(request):
    """
    Get AI suggestion for query response.

    GET /api/v1/genai/query-suggestion/?query_id=123
    """
    query_id = request.query_params.get('query_id')

    if not query_id:
        return Response(
            {'error': 'query_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    ai_service = ClinicalTrialAIService()
    suggestion = ai_service.generate_query_response_suggestion(int(query_id))

    return Response(suggestion)


@api_view(['GET'])
def risk_assessment(request):
    """
    Get AI-powered risk assessment for subject.

    GET /api/v1/genai/risk-assessment/?subject_id=Study_1_0-001
    """
    subject_id = request.query_params.get('subject_id')

    if not subject_id:
        return Response(
            {'error': 'subject_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    ai_service = ClinicalTrialAIService()
    assessment = ai_service.assess_subject_risk(subject_id)

    return Response(assessment)
