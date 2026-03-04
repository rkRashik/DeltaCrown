"""
TOC API Views — Sprint 28: Standings / Leaderboards tab.

GET  standings/               — Full standings dashboard
GET  standings/snapshot/      — Historical standings for a round
GET  standings/qualification/ — Qualification tracker
GET  standings/export/        — Export standings data
"""

from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.standings_service import TOCStandingsService


class StandingsDashboardView(TOCBaseView):
    """Full standings dashboard."""

    def get(self, request, slug):
        result = TOCStandingsService.get_standings(
            self.tournament,
            group_id=request.query_params.get("group_id"),
            stage=request.query_params.get("stage"),
        )
        return Response(result)


class StandingsSnapshotView(TOCBaseView):
    """Historical standings snapshot for a specific round."""

    def get(self, request, slug):
        round_number = request.query_params.get("round", 1)
        result = TOCStandingsService.get_standings_snapshot(
            self.tournament,
            round_number=int(round_number),
        )
        return Response(result)


class QualificationTrackerView(TOCBaseView):
    """Qualification tracker — who qualifies from groups."""

    def get(self, request, slug):
        result = TOCStandingsService.get_qualification_tracker(self.tournament)
        return Response(result)


class StandingsExportView(TOCBaseView):
    """Export standings as flat rows."""

    def get(self, request, slug):
        fmt = request.query_params.get("format", "json")
        result = TOCStandingsService.export_standings(self.tournament, format=fmt)
        return Response(result)
