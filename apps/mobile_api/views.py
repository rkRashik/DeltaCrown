"""Views for /api/mobile/v1/ chassis endpoints."""
from __future__ import annotations

from rest_framework.permissions import AllowAny, IsAuthenticated

from .base import MobileApiView
from .responses import success_response
from .serializers import HealthSerializer, MobileMeSerializer


SERVICE_NAME = "DeltaCrown Mobile API"
API_VERSION = "v1"


class HealthView(MobileApiView):
    """Public health probe for the mobile API namespace."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        payload = HealthSerializer({
            "service": SERVICE_NAME,
            "version": API_VERSION,
            "status": "ok",
        }).data
        return success_response(payload)


class MeView(MobileApiView):
    """Compact current-user summary for the authenticated mobile client."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = MobileMeSerializer(request.user).data
        return success_response(payload)
