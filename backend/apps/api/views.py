"""
API Views for Clinical Trial Control Tower.

Architecture Integration:
- KPI + Analytics Service → Pre-aggregated dashboard data
- Request Flow → API Gateway enforcement
- Governed Data Pods → RBAC-controlled data access
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

    GET /api/v1/role-visibility/?study_id=Study_1&site_id=Study_1_101

    Returns subject listing with filters applied.
    """
    study_id = request.query_params.get('study_id', 'Study_1')
    site_id = request.query_params.get('site_id')
    status_filter = request.query_params.get('status')

    # Build queryset with filters
    subjects = Subject.objects.filter(study_id=study_id).select_related(
        'site', 'site__country', 'clean_status', 'dqi_score'
    )

    if site_id and site_id != 'All':
        subjects = subjects.filter(site_id=site_id)

    if status_filter:
        subjects = subjects.filter(subject_status=status_filter)

    # Serialize data
    serializer = SubjectListSerializer(subjects, many=True)

    return Response({
        'subjects': serializer.data,
        'total_count': subjects.count()
    })


@api_view(['GET'])
def frontend_overview_data(request):
    """
    API endpoint for Frontend Overview Dashboard (KPI Dashboard).

    GET /api/v1/frontend-overview/?study_id=Study_1

    Returns:
    - KPI cards (Study, Region, Screened, Enrolled, Sites)
    - Operational drill-down metrics
    - Enrollment timeline data
    - Open issue summary
    """
    study_id = request.query_params.get('study_id', 'Study_1')

    try:
        study = Study.objects.get(study_id=study_id)
        study_dqi = DQIScoreStudy.objects.get(study=study)
    except:
        return Response({'error': 'Study not found'}, status=404)

    # KPI Cards
    total_subjects = Subject.objects.filter(study=study).count()
    enrolled_subjects = Subject.objects.filter(
        study=study,
        subject_status='Enrolled'
    ).count()
    total_sites = Site.objects.filter(study=study).count()

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

    # Operational Drill-Down
    clean_pct = float(study_dqi.clean_percentage)
    dqi_score = float(study_dqi.composite_dqi_score)

    operational_metrics = {
        'clean_percentage': round(clean_pct, 2),
        'dqi_score': round(dqi_score, 2),
        'readiness_status': study_dqi.readiness_status,
        'total_subjects': total_subjects,
        'clean_subjects': study_dqi.clean_subjects
    }

    # Open Issue Summary
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

    open_issues = [
        {
            'issue_type': 'Missing Visits',
            'count': missing_visits,
            'avg_days_open': 12.5,
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

    # Enrollment Timeline (mock data for now)
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
    Study-level summary API.

    GET /api/v1/study-summary/?study_id=Study_1
    """
    study_id = request.query_params.get('study_id', 'Study_1')

    try:
        study = Study.objects.get(study_id=study_id)
        study_dqi = DQIScoreStudy.objects.get(study=study)
    except:
        return Response({'error': 'Study not found'}, status=404)

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

    serializer = StudySummarySerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
def site_list(request):
    """
    Site listing API.

    GET /api/v1/sites/?study_id=Study_1
    """
    study_id = request.query_params.get('study_id', 'Study_1')

    sites = Site.objects.filter(study_id=study_id).select_related('country', 'dqi_score')

    site_data = []
    for site in sites:
        try:
            dqi = site.dqi_score
            clean_pct = float(dqi.clean_percentage)
            dqi_score = float(dqi.composite_dqi_score)
            risk_band = dqi.risk_band
        except:
            clean_pct = 0
            dqi_score = 0
            risk_band = 'Unknown'

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
    At-risk subjects API (High/Critical DQI).

    GET /api/v1/at-risk-subjects/?study_id=Study_1&limit=10
    """
    study_id = request.query_params.get('study_id', 'Study_1')
    limit = int(request.query_params.get('limit', 10))

    at_risk = DQIScoreSubject.objects.filter(
        subject__study_id=study_id,
        risk_band__in=['High', 'Critical']
    ).select_related('subject', 'subject__site').order_by('-composite_dqi_score')[:limit]

    subjects_data = []
    for dqi in at_risk:
        subject = dqi.subject
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
        'total_at_risk': at_risk.count()
    })
