"""
Views for core app.
Handles main dashboards and navigation.
"""

from django.shortcuts import render
from django.http import HttpResponse


def home(request):
    """
    Home page view.

    Displays study selection and navigation to dashboards.
    Will be fully implemented in Phase 4.
    """
    return HttpResponse("Clinical Trial Control Tower - Phase 0 Setup Complete")


# Additional views will be implemented in Phase 1/4:
# - cra_dashboard
# - dqt_dashboard
# - site_dashboard
# - leadership_dashboard
