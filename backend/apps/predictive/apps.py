"""Predictive AI Platform app configuration."""

from django.apps import AppConfig


class PredictiveConfig(AppConfig):
    """Configuration for predictive AI app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.predictive'
    verbose_name = 'Predictive AI Platform'
