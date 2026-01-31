"""
API Serializers for Clinical Trial Control Tower.
Convert Django models to JSON for REST API.
"""

from rest_framework import serializers
from apps.core.models import Study, Site, Subject
from apps.monitoring.models import Query, MissingVisit, MissingPage
from apps.metrics.models import CleanPatientStatus, DQIScoreSubject, DQIScoreSite, DQIScoreStudy


class SubjectListSerializer(serializers.ModelSerializer):
    """Subject list serializer for dashboard table."""

    site_number = serializers.CharField(source='site.site_number')
    country = serializers.CharField(source='site.country.country_name')
    is_clean = serializers.SerializerMethodField()
    dqi_score = serializers.SerializerMethodField()
    risk_band = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['subject_id', 'subject_external_id', 'subject_status',
                  'site_number', 'country', 'is_clean', 'dqi_score', 'risk_band']

    def get_is_clean(self, obj):
        try:
            return obj.clean_status.is_clean
        except:
            return None

    def get_dqi_score(self, obj):
        try:
            return float(obj.dqi_score.composite_dqi_score)
        except:
            return None

    def get_risk_band(self, obj):
        try:
            return obj.dqi_score.risk_band
        except:
            return None


class StudySummarySerializer(serializers.Serializer):
    """Study summary for leadership dashboard."""

    study_id = serializers.CharField()
    study_name = serializers.CharField()
    total_subjects = serializers.IntegerField()
    clean_subjects = serializers.IntegerField()
    clean_percentage = serializers.FloatField()
    composite_dqi_score = serializers.FloatField()
    readiness_status = serializers.CharField()
    total_sites = serializers.IntegerField()


class KPICardSerializer(serializers.Serializer):
    """KPI card data for frontend overview."""

    label = serializers.CharField()
    value = serializers.CharField()
    trend = serializers.CharField(required=False)
    color = serializers.CharField(required=False)


class OpenIssueSerializer(serializers.Serializer):
    """Open issue summary."""

    issue_type = serializers.CharField()
    count = serializers.IntegerField()
    avg_days_open = serializers.FloatField()
    priority = serializers.CharField()
