"""
TOC API — Overview Endpoint.

GET /api/toc/<slug>/overview/
Returns the full Command Center dashboard payload.

Sprint 1: S1-B2
PRD: §2.1–§2.5
"""

from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import toc_cache_key
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
        # 8-second micro-cache smooths burst refreshes while keeping data fresh.
        cache_bucket = int(timezone.now().timestamp() // 8)
        cache_key = toc_cache_key('overview', self.tournament.id, cache_bucket)
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return Response(cached_payload)

        data = TOCService.get_overview(self.tournament)
        serializer = OverviewSerializer(data)
        payload = serializer.data
        cache.set(cache_key, payload, timeout=10)
        return Response(payload)
