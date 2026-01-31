"""Predictive AI API URLs."""

from django.urls import path
from . import views

urlpatterns = [
    path('dropout-risk/', views.predict_dropout_risk, name='predict-dropout-risk'),
    path('query-resolution-time/', views.predict_query_resolution_time, name='predict-query-time'),
    path('enrollment-forecast/', views.enrollment_forecast, name='enrollment-forecast'),
    path('site-performance/', views.predict_site_performance, name='predict-site-performance'),
    path('batch-risk/', views.batch_risk_predictions, name='batch-risk'),
]
