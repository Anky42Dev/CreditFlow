"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.urls import include, path

from common.metrics import metrics_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.products.urls')),
    path('api/v1/', include('apps.applications.urls')),
    path('api/v1/', include('apps.lending.urls')),
    path('api/v1/', include('apps.notifications.urls')),
    path('api/v1/', include('apps.adminpanel.urls')),
    path('api/v1/', include('apps.audit.urls')),
    path('api/v1/', include('apps.feature_flags.urls')),
    # DOC 5 §13: unprefixed, matching the K8s liveness/readiness/startup
    # probe convention (not versioned API surface).
    path('', include('apps.health.urls')),
    # DOC 5 §12.1: Prometheus scrape target.
    path('metrics', metrics_view, name='metrics'),
]
