"""
URL Configuration for Clinical Trial Control Tower.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

# Admin site customization
admin.site.site_header = "Clinical Trial Control Tower"
admin.site.site_title = "CTCT Admin"
admin.site.index_title = "Welcome to CTCT Administration"

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # REST API endpoints
    path('api/v1/', include('apps.api.urls')),
    path('api/v1/genai/', include('apps.genai.urls')),
    path('api/v1/predictions/', include('apps.predictive.urls')),
    path('api/v1/blockchain/', include('apps.blockchain.urls')),

    # Frontend template routes
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    path('dashboards/role-visibility/', TemplateView.as_view(template_name='dashboards/role-visibility.html'), name='role-visibility'),
    path('dashboards/frontend-overview/', TemplateView.as_view(template_name='dashboards/frontend-overview.html'), name='frontend-overview'),
    path('components/predictions-panel.html', TemplateView.as_view(template_name='components/predictions-panel.html'), name='predictions'),
    path('components/blockchain-audit.html', TemplateView.as_view(template_name='components/blockchain-audit.html'), name='blockchain'),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
