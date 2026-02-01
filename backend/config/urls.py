"""
URL Configuration for Clinical Trial Control Tower.

This module defines all URL routes for the application including:
- Admin panel access
- REST API endpoints (v1)
- Frontend template rendering routes
- Health check endpoint for monitoring
- Static/Media file serving in development mode

Reference: Django URL dispatcher docs
https://docs.djangoproject.com/en/5.0/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.http import JsonResponse


def health_check(request):
    """
    Health check endpoint for monitoring and load balancers.
    
    Purpose: Returns a simple JSON response indicating the server is running.
    Inputs: HTTP GET request (no parameters required)
    Outputs: JSON object with status='ok' and HTTP 200
    Side effects: None (read-only operation)
    
    Usage: GET /health/
    """
    return JsonResponse({
        'status': 'ok',
        'service': 'Clinical Trial Control Tower',
        'version': '1.0.0'
    })


# Admin site customization - branding for Django admin interface
admin.site.site_header = "Clinical Trial Control Tower"
admin.site.site_title = "CTCT Admin"
admin.site.index_title = "Welcome to CTCT Administration"


urlpatterns = [
    # =========================================
    # Health Check Endpoint
    # Used by monitoring tools and load balancers
    # =========================================
    path('health/', health_check, name='health-check'),
    path('api/health/', health_check, name='api-health-check'),
    
    # =========================================
    # Django Admin Panel
    # Accessible at /admin/
    # =========================================
    path('admin/', admin.site.urls),

    # =========================================
    # REST API Endpoints (versioned)
    # All API routes are prefixed with /api/v1/
    # =========================================
    
    # Core data API - studies, sites, subjects, metrics
    path('api/v1/', include('apps.api.urls')),
    
    # GenAI service API - AI-powered suggestions and analysis
    path('api/v1/genai/', include('apps.genai.urls')),
    
    # Predictive ML API - risk predictions and forecasting
    path('api/v1/predictions/', include('apps.predictive.urls')),
    
    # Blockchain API - audit trails and integrity verification
    path('api/v1/blockchain/', include('apps.blockchain.urls')),

    # =========================================
    # Frontend Template Routes
    # Server-rendered HTML pages
    # =========================================
    
    # Homepage / Landing page - main entry point
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Dashboard routes - main operational views
    path('dashboards/role-visibility/', 
         TemplateView.as_view(template_name='dashboards/role-visibility.html'), 
         name='role-visibility'),
    path('dashboards/frontend-overview/', 
         TemplateView.as_view(template_name='dashboards/frontend-overview.html'), 
         name='frontend-overview'),
    
    # Component routes - modular UI components
    path('components/predictions-panel.html', 
         TemplateView.as_view(template_name='components/predictions-panel.html'), 
         name='predictions'),
    path('components/blockchain-audit.html', 
         TemplateView.as_view(template_name='components/blockchain-audit.html'), 
         name='blockchain'),
    path('components/genai-assistant.html', 
         TemplateView.as_view(template_name='components/genai-assistant.html'), 
         name='genai-assistant'),
]


# =========================================
# Static and Media File Serving (Development Only)
# In production, these are served by nginx/Apache
# =========================================
if settings.DEBUG:
    # Serve uploaded media files during development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Serve static files (CSS, JS, images) during development
    # Note: In production, run `collectstatic` and serve via web server
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
