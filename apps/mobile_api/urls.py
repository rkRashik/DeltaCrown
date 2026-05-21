"""URL configuration for /api/mobile/v1/."""
from django.urls import include, path

from .views import HealthView, MeView


app_name = "mobile_api_v1"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("me/", MeView.as_view(), name="me"),
    path("auth/", include(("apps.mobile_api.auth.urls", "auth"), namespace="auth")),
]
