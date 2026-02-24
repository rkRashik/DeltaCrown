"""
TOC API — Overview Endpoint.

GET /api/toc/<slug>/overview/
Returns the full Command Center dashboard payload.

Sprint 1: S1-B2
PRD: §2.1–§2.5
"""

from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.serializers import OverviewSerializer
from apps.tournaments.api.toc.service import TOCService


class OverviewAPIView(TOCBaseView):
    """
    GET — Command Center overview payload.

    Returns: status, lifecycle progress, stat cards, alerts, upcoming events,
    valid transitions.

    Polled every 30s by the frontend for auto-refresh.
    """

    def get(self, request, slug):
        data = TOCService.get_overview(self.tournament)
        serializer = OverviewSerializer(data)
        return Response(serializer.data)
