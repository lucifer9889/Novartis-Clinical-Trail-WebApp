"""
GenAI API Views for Clinical Trial Control Tower.

This module provides REST API endpoints for AI-powered suggestions
and analysis features. These endpoints integrate with Claude AI
to provide intelligent recommendations for clinical trial operations.

API Endpoints:
- GET /api/v1/genai/suggested-actions/ - Priority action suggestions
- GET /api/v1/genai/query-suggestion/ - Query response suggestions
- GET /api/v1/genai/risk-assessment/ - Subject risk assessment

Architecture Integration:
- GenAI Orchestrator (Governed) component
- Policy-aware retrieval + RAG
- Evidence-based recommendations
"""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .services import ClinicalTrialAIService, is_ai_configured


@api_view(['GET'])
def suggested_actions(request):
    """
    Get AI-generated suggested actions for CRAs.
    
    Purpose: Returns prioritized action recommendations based on
             current study data and AI analysis.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
        - limit: Maximum number of actions to return (default: 3)
    
    Outputs: JSON object containing:
        - actions: Array of suggested actions with title, description,
                   priority, category, and estimated impact
        - study_id: The study for which actions were generated
        - ai_enabled: Whether AI is configured (if False, using fallbacks)
    
    Side effects: May call external AI API (Anthropic/Claude) if configured
    
    Usage: GET /api/v1/genai/suggested-actions/?study_id=Study_1&limit=3
    """
    # Extract query parameters with defaults
    study_id = request.query_params.get('study_id', 'Study_1')
    
    # Validate and parse limit parameter
    try:
        limit = int(request.query_params.get('limit', 3))
        limit = max(1, min(limit, 10))  # Clamp between 1 and 10
    except ValueError:
        limit = 3

    # Initialize AI service and generate actions
    ai_service = ClinicalTrialAIService()
    actions = ai_service.generate_suggested_actions(study_id, limit)

    response_data = {
        'actions': actions,
        'study_id': study_id,
        'ai_enabled': ai_service.is_configured
    }
    
    # Add helpful message if AI is disabled
    if not ai_service.is_configured:
        response_data['message'] = 'AI features disabled. Set ANTHROPIC_API_KEY in .env to enable.'
    
    return Response(response_data)


@api_view(['GET'])
def query_suggestion(request):
    """
    Get AI suggestion for query response.
    
    Purpose: Analyzes a specific query and generates a suggested
             response that follows clinical trial documentation standards.
    
    Inputs (query parameters):
        - query_id: Required. The ID of the query to analyze
    
    Outputs: JSON object containing:
        - query_id: The analyzed query ID
        - suggested_response: AI-generated response text
        - confidence: Confidence level of the suggestion
        - requires_review: Boolean indicating if human review is needed
    
    Side effects: 
        - May call external AI API (Anthropic/Claude)
        - Database read to fetch query details
    
    Usage: GET /api/v1/genai/query-suggestion/?query_id=123
    """
    # Extract and validate query_id parameter
    query_id = request.query_params.get('query_id')

    # Query ID is required for this endpoint
    if not query_id:
        return Response(
            {'error': 'query_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Initialize AI service and generate suggestion
    ai_service = ClinicalTrialAIService()
    suggestion = ai_service.generate_query_response_suggestion(int(query_id))

    return Response(suggestion)


@api_view(['GET'])
def risk_assessment(request):
    """
    Get AI-powered risk assessment for a specific subject.
    
    Purpose: Analyzes all blockers and data quality issues for a subject
             and provides prioritized recommendations for resolution.
    
    Inputs (query parameters):
        - subject_id: Required. The ID of the subject to analyze
    
    Outputs: JSON object containing:
        - subject_id: The analyzed subject ID
        - risk_assessment: AI-generated assessment text
        - dqi_score: Current DQI score for the subject
        - risk_band: Risk classification (Low/Medium/High/Critical)
        - is_clean: Whether subject has clean patient status
    
    Side effects:
        - May call external AI API (Anthropic/Claude)
        - Database read to fetch subject data and metrics
    
    Usage: GET /api/v1/genai/risk-assessment/?subject_id=Study_1_0-001
    """
    # Extract and validate subject_id parameter
    subject_id = request.query_params.get('subject_id')

    # Subject ID is required for this endpoint
    if not subject_id:
        return Response(
            {'error': 'subject_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Initialize AI service and generate assessment
    ai_service = ClinicalTrialAIService()
    assessment = ai_service.assess_subject_risk(subject_id)

    return Response(assessment)


@api_view(['GET'])
def ai_status(request):
    """
    Check AI service configuration status.
    
    Purpose: Returns whether AI features are enabled and provides guidance
             for configuration if not.
    
    Outputs: JSON object containing:
        - ai_enabled: Whether ANTHROPIC_API_KEY is configured
        - message: Status message
        - features: List of AI features and their availability
    
    Usage: GET /api/v1/genai/status/
    """
    ai_configured = is_ai_configured()
    
    response_data = {
        'ai_enabled': ai_configured,
        'features': {
            'suggested_actions': ai_configured,
            'query_suggestions': ai_configured,
            'risk_assessment': ai_configured,
        }
    }
    
    if ai_configured:
        response_data['message'] = 'AI features are enabled and ready.'
    else:
        response_data['message'] = 'AI features disabled. Set ANTHROPIC_API_KEY in your environment or .env file.'
        response_data['setup_instructions'] = 'See README.md section "AI API Keys Setup" for configuration instructions.'
    
    return Response(response_data)
