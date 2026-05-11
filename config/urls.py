"""Root URL configuration."""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from core.views import HealthCheckView

urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),

    # Health
    path("health/", HealthCheckView.as_view(), name="health-check"),

    # API v1
    path("api/v1/", include("config.api_router", namespace="api-v1")),

    # OpenAPI Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]
