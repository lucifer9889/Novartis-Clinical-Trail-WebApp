"""
API Views for Clinical Trial Control Tower.

This module provides REST API endpoints for the clinical trial dashboard.
All endpoints return JSON data consumed by the frontend dashboards.

Architecture Integration:
- KPI + Analytics Service → Pre-aggregated dashboard data
- Request Flow → API Gateway enforcement
- Governed Data Pods → RBAC-controlled data access

Endpoints defined here:
- role_visibility_data: Subject listing with filters
- frontend_overview_data: KPI dashboard data
- study_summary: Study-level summary metrics
- site_list: Site listing with DQI scores
- at_risk_subjects: High/Critical risk subjects
"""

from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from apps.core.models import Study, Site, Subject
from apps.monitoring.models import Query, MissingVisit, MissingPage
from apps.safety.models import SAEDiscrepancy
from apps.metrics.models import CleanPatientStatus, DQIScoreSubject, DQIScoreSite, DQIScoreStudy
from .serializers import (
    SubjectListSerializer, StudySummarySerializer,
    KPICardSerializer, OpenIssueSerializer
)


@api_view(['GET'])
def role_visibility_data(request):
    """
    API endpoint for Role-based Visibility Dashboard.
    
    Purpose: Returns subject listing with applied filters for the 
             role-based visibility dashboard view.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
        - site_id: Optional site filter ('All' or specific site_id)
        - status: Optional subject status filter
    
    Outputs: JSON object containing:
        - subjects: List of serialized subject data
        - total_count: Number of subjects matching filters
    
    Side effects: None (read-only database queries)
    
    Usage: GET /api/v1/role-visibility/?study_id=Study_1&site_id=Study_1_101
    """
    # Extract query parameters with defaults
    study_id = request.query_params.get('study_id', 'Study_1')
    site_id = request.query_params.get('site_id')
    status_filter = request.query_params.get('status')

    try:
        # Build base queryset with related objects for efficiency
        # Using select_related to minimize database queries (N+1 prevention)
        subjects = Subject.objects.filter(study_id=study_id).select_related(
            'site', 'site__country', 'clean_status', 'dqi_score'
        )

        # Apply optional site filter - 'All' means no filtering
        if site_id and site_id != 'All':
            subjects = subjects.filter(site_id=site_id)

        # Apply optional status filter
        if status_filter:
            subjects = subjects.filter(subject_status=status_filter)

        # Serialize the queryset to JSON-friendly format
        serializer = SubjectListSerializer(subjects, many=True)

        return Response({
            'subjects': serializer.data,
            'total_count': subjects.count()
        })
    
    except Exception as e:
        # Return empty data with error message if query fails
        return Response({
            'subjects': [],
            'total_count': 0,
            'message': 'No subjects found. Ensure study data is loaded.'
        })


@api_view(['GET'])
def frontend_overview_data(request):
    """
    API endpoint for Frontend Overview Dashboard (KPI Dashboard).
    
    Purpose: Provides comprehensive KPI data for the main dashboard view,
             including metrics, operational data, and charts data.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
    
    Outputs: JSON object containing:
        - kpi_cards: Array of KPI card data (label, value, color)
        - operational_metrics: Clean percentage, DQI score, readiness
        - open_issues: Summary of open issues by type
        - enrollment_timeline: Historical and projected enrollment data
    
    Side effects: None (read-only database queries)
    
    Usage: GET /api/v1/frontend-overview/?study_id=Study_1
    """
    study_id = request.query_params.get('study_id', 'Study_1')

    try:
        # Fetch study and its DQI score - these are required for the dashboard
        study = Study.objects.get(study_id=study_id)
        study_dqi = DQIScoreStudy.objects.get(study=study)
    except Study.DoesNotExist:
        # Return demo/sample data if study not found
        # This allows the UI to render even without database data
        return Response({
            'kpi_cards': [
                {'label': 'Study', 'value': 'Demo Study', 'color': 'primary'},
                {'label': 'Region', 'value': 'APAC', 'color': 'info'},
                {'label': 'Screened', 'value': '1,288', 'color': 'secondary'},
                {'label': 'Enrolled', 'value': '8,476', 'color': 'success'},
                {'label': 'Sites', 'value': '103', 'color': 'primary'}
            ],
            'operational_metrics': {
                'clean_percentage': 94.2,
                'dqi_score': 87.5,
                'readiness_status': 'On Track',
                'total_subjects': 8476,
                'clean_subjects': 7985
            },
            'open_issues': [
                {'issue_type': 'Missing Visits', 'count': 15, 'avg_days_open': 12.5, 'priority': 'High'},
                {'issue_type': 'Open Queries', 'count': 42, 'avg_days_open': 8.3, 'priority': 'Medium'},
                {'issue_type': 'Missing Pages', 'count': 28, 'avg_days_open': 6.7, 'priority': 'Medium'},
                {'issue_type': 'SAE Discrepancies', 'count': 3, 'avg_days_open': 15.2, 'priority': 'Critical'}
            ],
            'enrollment_timeline': {
                'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                'projected': [100, 200, 350, 500, 700, 850],
                'actual': [80, 180, 320, 480, 650, 800]
            },
            'message': 'Showing demo data. Load study data for real metrics.'
        })
    except DQIScoreStudy.DoesNotExist:
        # Study exists but no DQI scores computed yet
        return Response({
            'error': 'DQI scores not computed. Run compute_metrics command.',
            'study_id': study_id
        }, status=400)

    # Build KPI Cards data
    # Count subjects and sites for the study
    total_subjects = Subject.objects.filter(study=study).count()
    enrolled_subjects = Subject.objects.filter(
        study=study,
        subject_status='Enrolled'
    ).count()
    total_sites = Site.objects.filter(study=study).count()

    # KPI cards array - each card has label, value, and Bootstrap color class
    kpi_cards = [
        {
            'label': 'Study',
            'value': study.study_id,
            'color': 'primary'
        },
        {
            'label': 'Region',
            'value': study.region or 'Multi-Regional',
            'color': 'info'
        },
        {
            'label': 'Screened',
            'value': str(total_subjects),
            'color': 'secondary'
        },
        {
            'label': 'Enrolled',
            'value': str(enrolled_subjects),
            'color': 'success'
        },
        {
            'label': 'Sites',
            'value': str(total_sites),
            'color': 'primary'
        }
    ]

    # Operational Drill-Down metrics
    # Convert Decimal fields to float for JSON serialization
    clean_pct = float(study_dqi.clean_percentage)
    dqi_score = float(study_dqi.composite_dqi_score)

    operational_metrics = {
        'clean_percentage': round(clean_pct, 2),
        'dqi_score': round(dqi_score, 2),
        'readiness_status': study_dqi.readiness_status,
        'total_subjects': total_subjects,
        'clean_subjects': study_dqi.clean_subjects
    }

    # Open Issue Summary - count various issue types
    # Each query counts open issues for the study
    open_queries = Query.objects.filter(
        subject__study=study,
        query_status='Open'
    ).count()

    missing_visits = MissingVisit.objects.filter(
        subject__study=study
    ).count()

    missing_pages = MissingPage.objects.filter(
        subject__study=study
    ).count()

    sae_discrepancies = SAEDiscrepancy.objects.filter(
        study=study
    ).count()

    # Build open issues array with priority logic
    # Priority is determined by issue count thresholds
    open_issues = [
        {
            'issue_type': 'Missing Visits',
            'count': missing_visits,
            'avg_days_open': 12.5,  # TODO: Calculate actual average
            'priority': 'High' if missing_visits > 10 else 'Medium'
        },
        {
            'issue_type': 'Open Queries',
            'count': open_queries,
            'avg_days_open': 8.3,
            'priority': 'Medium'
        },
        {
            'issue_type': 'Missing Pages',
            'count': missing_pages,
            'avg_days_open': 6.7,
            'priority': 'Medium'
        },
        {
            'issue_type': 'SAE Discrepancies',
            'count': sae_discrepancies,
            'avg_days_open': 15.2,
            'priority': 'Critical' if sae_discrepancies > 0 else 'Low'
        }
    ]

    # Enrollment Timeline - mock data for chart
    # TODO: Implement actual enrollment tracking and forecasting
    enrollment_timeline = {
        'labels': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'projected': [100, 200, 350, 500, 700, 850],
        'actual': [80, 180, 320, 480, 650, 800]
    }

    return Response({
        'kpi_cards': kpi_cards,
        'operational_metrics': operational_metrics,
        'open_issues': open_issues,
        'enrollment_timeline': enrollment_timeline
    })


@api_view(['GET'])
def study_summary(request):
    """
    Study-level summary API endpoint.
    
    Purpose: Returns summary metrics for a specific study including
             DQI scores and readiness status.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
    
    Outputs: JSON object with study metrics including:
        - study_id, study_name
        - total_subjects, clean_subjects, clean_percentage
        - composite_dqi_score, readiness_status, total_sites
    
    Side effects: None (read-only)
    
    Usage: GET /api/v1/study-summary/?study_id=Study_1
    """
    study_id = request.query_params.get('study_id', 'Study_1')

    try:
        # Fetch study and DQI scores
        study = Study.objects.get(study_id=study_id)
        study_dqi = DQIScoreStudy.objects.get(study=study)
    except Study.DoesNotExist:
        # Return helpful error message
        return Response({
            'error': 'Study not found',
            'requested_study_id': study_id,
            'message': 'Ensure study data is loaded via import_study_data command.'
        }, status=404)
    except DQIScoreStudy.DoesNotExist:
        return Response({
            'error': 'DQI scores not computed',
            'study_id': study_id,
            'message': 'Run compute_metrics command to generate DQI scores.'
        }, status=400)

    # Build response data with proper type conversions
    data = {
        'study_id': study.study_id,
        'study_name': study.study_name,
        'total_subjects': study_dqi.total_subjects,
        'clean_subjects': study_dqi.clean_subjects,
        'clean_percentage': float(study_dqi.clean_percentage),
        'composite_dqi_score': float(study_dqi.composite_dqi_score),
        'readiness_status': study_dqi.readiness_status,
        'total_sites': study_dqi.total_sites
    }

    # Serialize and return
    serializer = StudySummarySerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
def site_list(request):
    """
    Site listing API endpoint.
    
    Purpose: Returns list of all sites for a study with their
             DQI scores and risk bands.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
    
    Outputs: JSON object containing:
        - sites: Array of site objects with DQI data
        - total_count: Number of sites
    
    Side effects: None (read-only)
    
    Usage: GET /api/v1/sites/?study_id=Study_1
    """
    study_id = request.query_params.get('study_id', 'Study_1')

    # Fetch sites with related objects for efficiency
    sites = Site.objects.filter(study_id=study_id).select_related('country', 'dqi_score')

    site_data = []
    for site in sites:
        # Safely get DQI score - may not exist if metrics not computed
        try:
            dqi = site.dqi_score
            clean_pct = float(dqi.clean_percentage)
            dqi_score = float(dqi.composite_dqi_score)
            risk_band = dqi.risk_band
        except Exception:
            # Default values if DQI not computed
            clean_pct = 0
            dqi_score = 0
            risk_band = 'Unknown'

        # Build site data object
        site_data.append({
            'site_id': site.site_id,
            'site_number': site.site_number,
            'site_name': site.site_name or 'N/A',
            'country': site.country.country_name,
            'region': site.country.region,
            'total_subjects': Subject.objects.filter(site=site).count(),
            'clean_percentage': clean_pct,
            'dqi_score': dqi_score,
            'risk_band': risk_band
        })

    return Response({
        'sites': site_data,
        'total_count': len(site_data)
    })


@api_view(['GET'])
def at_risk_subjects(request):
    """
    At-risk subjects API endpoint (High/Critical DQI).
    
    Purpose: Returns subjects with high or critical risk bands
             for targeted intervention.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
        - limit: Maximum number of subjects to return (default: 10)
    
    Outputs: JSON object containing:
        - subjects: Array of at-risk subject data with DQI info
        - total_at_risk: Count of subjects matching criteria
    
    Side effects: None (read-only)
    
    Usage: GET /api/v1/at-risk-subjects/?study_id=Study_1&limit=10
    """
    study_id = request.query_params.get('study_id', 'Study_1')
    
    # Safely parse limit parameter with validation
    try:
        limit = int(request.query_params.get('limit', 10))
        limit = max(1, min(limit, 100))  # Clamp between 1 and 100
    except ValueError:
        limit = 10

    try:
        # Query subjects with High or Critical risk bands
        # Order by DQI score ascending (worst first)
        at_risk = DQIScoreSubject.objects.filter(
            subject__study_id=study_id,
            risk_band__in=['High', 'Critical']
        ).select_related('subject', 'subject__site').order_by('composite_dqi_score')[:limit]

        subjects_data = []
        for dqi in at_risk:
            subject = dqi.subject
            
            # Get clean patient status for additional context
            clean_status = CleanPatientStatus.objects.filter(subject=subject).first()

            subjects_data.append({
                'subject_id': subject.subject_external_id,
                'site': subject.site.site_number,
                'dqi_score': float(dqi.composite_dqi_score),
                'risk_band': dqi.risk_band,
                'is_clean': clean_status.is_clean if clean_status else False,
                'blockers': clean_status.get_blockers_list() if clean_status else []
            })

        return Response({
            'subjects': subjects_data,
            'total_at_risk': len(subjects_data)
        })

    except Exception as e:
        # Return empty data with informative message
        return Response({
            'subjects': [],
            'total_at_risk': 0,
            'message': 'No at-risk subjects found. Ensure DQI scores are computed.'
        })


@api_view(['GET'])
def risk_heatmap_data(request):
    """
    API endpoint for Risk Heatmap in Predictive AI Dashboard.
    
    Purpose: Returns site-level risk metrics organized for heatmap display.
             Each site has risk scores across multiple dimensions.
    
    Inputs (query parameters):
        - study_id: Study identifier (default: 'Study_1')
    
    Outputs: JSON object containing:
        - sites: List of site risk data with scores per dimension
        - dimensions: List of risk dimension names
        - updated_at: Timestamp of data
    
    Side effects: None (read-only)
    
    Usage: GET /api/v1/risk-heatmap/?study_id=Study_1
    """
    study_id = request.query_params.get('study_id', 'Study_1')
    
    try:
        # Get all sites for the study
        sites = Site.objects.filter(study_id=study_id).select_related('country')
        
        heatmap_data = []
        
        for site in sites:
            # Calculate risk metrics for each dimension
            site_subjects = Subject.objects.filter(site=site)
            subject_count = site_subjects.count()
            
            if subject_count == 0:
                continue
            
            # Query backlog
            query_count = Query.objects.filter(
                subject__site=site, 
                query_status='Open'
            ).count()
            query_risk = 'critical' if query_count > 25 else 'high' if query_count > 15 else 'medium' if query_count > 5 else 'low'
            
            # Missing pages
            missing_pages = MissingPage.objects.filter(
                subject__site=site,
                is_resolved=False
            ).count()
            pages_risk = 'high' if missing_pages > 10 else 'medium' if missing_pages > 3 else 'low'
            
            # Missing visits
            missing_visits = MissingVisit.objects.filter(
                subject__site=site,
                is_resolved=False
            ).count()
            visit_risk = 'high' if missing_visits > 5 else 'medium' if missing_visits > 2 else 'low'
            
            # SAE backlog
            sae_count = SAEDiscrepancy.objects.filter(
                subject__site=site,
                resolution_status__in=['Open', 'Pending']
            ).count()
            safety_risk = 'critical' if sae_count > 3 else 'high' if sae_count > 1 else 'medium' if sae_count > 0 else 'low'
            
            # Get site DQI score
            site_dqi = DQIScoreSite.objects.filter(site=site).first()
            dqi_score = float(site_dqi.composite_dqi_score) if site_dqi else 75.0
            
            # Calculate overall risk
            risk_scores = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            risks = [query_risk, pages_risk, visit_risk, safety_risk]
            avg_risk = sum(risk_scores.get(r, 0) for r in risks) / len(risks)
            overall = 'critical' if avg_risk >= 2.5 else 'high' if avg_risk >= 1.5 else 'medium' if avg_risk >= 0.5 else 'low'
            
            heatmap_data.append({
                'site_id': site.site_id,
                'site_number': site.site_number,
                'site_name': f"Site {site.site_number} - {site.city or 'Unknown'}",
                'country': site.country.country_name if site.country else 'Unknown',
                'subject_count': subject_count,
                'dqi_score': dqi_score,
                'risks': {
                    'recruitment_delay': 'low',  # Placeholder - would need enrollment data
                    'query_backlog': query_risk,
                    'data_entry_delay': 'medium',  # Placeholder
                    'missing_pages': pages_risk,
                    'missing_visits': visit_risk,
                    'safety_backlog': safety_risk,
                    'coding_backlog': 'low',  # Placeholder
                    'overall': overall
                }
            })
        
        return Response({
            'sites': heatmap_data,
            'dimensions': [
                'recruitment_delay', 'query_backlog', 'data_entry_delay',
                'missing_pages', 'missing_visits', 'safety_backlog', 
                'coding_backlog', 'overall'
            ],
            'study_id': study_id,
            'total_sites': len(heatmap_data)
        })
    
    except Exception as e:
        # Return demo data if database query fails
        return Response({
            'sites': [],
            'dimensions': [],
            'message': f'Error loading heatmap data: {str(e)}',
            'study_id': study_id
        })


@api_view(['GET'])
def user_context(request):
    """
    API endpoint for current user context and permissions.
    
    Purpose: Returns information about the logged-in user including
             role, allowed modules, and display information.
    
    Outputs: JSON object containing:
        - is_authenticated: Boolean
        - username: User's username
        - full_name: User's full name
        - role: User's primary role (group name)
        - allowed_modules: List of modules the user can access
    
    Side effects: None (read-only)
    
    Usage: GET /api/v1/user-context/
    """
    from apps.core.auth_helpers import user_role, get_allowed_modules
    
    if not request.user.is_authenticated:
        return Response({
            'is_authenticated': False,
            'error': 'Authentication required'
        }, status=401)
    
    user = request.user
    role = user_role(request)
    
    return Response({
        'is_authenticated': True,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'role': role,
        'is_superuser': user.is_superuser,
        'allowed_modules': get_allowed_modules(request),
    })

