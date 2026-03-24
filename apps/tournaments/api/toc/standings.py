"""
TOC API Views — Sprint 28: Standings / Leaderboards tab.

GET  standings/               — Full standings dashboard
GET  standings/snapshot/      — Historical standings for a round
GET  standings/qualification/ — Qualification tracker
GET  standings/export/        — Export standings data
"""

from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import toc_cache_key
from apps.tournaments.api.toc.standings_service import TOCStandingsService


class StandingsDashboardView(TOCBaseView):
    """Full standings dashboard."""

    def get(self, request, slug):
        group_id = request.query_params.get("group_id") or ''
        stage = request.query_params.get("stage") or ''
        cache_bucket = int(timezone.now().timestamp() // 8)
        cache_key = toc_cache_key('standings', self.tournament.id, 'dashboard', group_id, stage, cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCStandingsService.get_standings(
            self.tournament,
            group_id=group_id or None,
            stage=stage or None,
        )
        cache.set(cache_key, result, timeout=12)
        return Response(result)


class StandingsSnapshotView(TOCBaseView):
    """Historical standings snapshot for a specific round."""

    def get(self, request, slug):
        round_number = request.query_params.get("round", 1)
        cache_bucket = int(timezone.now().timestamp() // 10)
        cache_key = toc_cache_key('standings', self.tournament.id, 'snapshot', round_number, cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCStandingsService.get_standings_snapshot(
            self.tournament,
            round_number=int(round_number),
        )
        cache.set(cache_key, result, timeout=15)
        return Response(result)


class QualificationTrackerView(TOCBaseView):
    """Qualification tracker — who qualifies from groups."""

    def get(self, request, slug):
        cache_bucket = int(timezone.now().timestamp() // 12)
        cache_key = toc_cache_key('standings', self.tournament.id, 'qualification', cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCStandingsService.get_qualification_tracker(self.tournament)
        cache.set(cache_key, result, timeout=18)
        return Response(result)


class StandingsExportView(TOCBaseView):
    """Export standings as flat rows."""

    def get(self, request, slug):
        fmt = request.query_params.get("format", "json")
        result = TOCStandingsService.export_standings(self.tournament, format=fmt)
        return Response(result)
