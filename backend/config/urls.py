"""
URL Configuration for Clinical Trial Control Tower.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/

Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Admin site customization
admin.site.site_header = "Clinical Trial Control Tower"
admin.site.site_title = "CTCT Admin"
admin.site.index_title = "Welcome to CTCT Administration"

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Core app URLs (dashboards, home, etc.)
    path('', include('apps.core.urls')),

    # Monitoring app URLs
    path('monitoring/', include('apps.monitoring.urls')),

    # Safety app URLs
    path('safety/', include('apps.safety.urls')),

    # Medical coding app URLs
    path('medical-coding/', include('apps.medical_coding.urls')),

    # Metrics app URLs (DQI, Clean Status)
    path('metrics/', include('apps.metrics.urls')),

    # Blockchain app URLs (Phase 7)
    path('blockchain/', include('apps.blockchain.urls')),

    # AI Services URLs (Phase 5)
    path('ai/', include('apps.ai_services.urls')),

    # REST API endpoints
    path('api/v1/', include([
        path('', include('apps.core.urls')),
        path('monitoring/', include('apps.monitoring.urls')),
        path('safety/', include('apps.safety.urls')),
        path('metrics/', include('apps.metrics.urls')),
        path('blockchain/', include('apps.blockchain.urls')),
        path('ai/', include('apps.ai_services.urls')),
    ])),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
