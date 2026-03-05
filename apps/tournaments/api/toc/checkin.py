"""
TOC API Views — Sprint 28: Check-in Hub tab.

GET   checkin/                — Full checkin dashboard
POST  checkin/open/           — Open checkin window
POST  checkin/close/          — Close checkin window
POST  checkin/force/          — Force-checkin a participant
POST  checkin/force-match/    — Force-checkin for a specific match
POST  checkin/auto-dq/        — Auto-DQ no-shows
POST  checkin/config/         — Update checkin config
GET   checkin/stats/          — Checkin analytics
"""

from rest_framework.response import Response
from rest_framework import status

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.checkin_service import TOCCheckinService


class CheckinDashboardView(TOCBaseView):
    """Full checkin dashboard."""

    def get(self, request, slug):
        round_number = request.query_params.get("round")
        result = TOCCheckinService.get_checkin_dashboard(
            self.tournament,
            round_number=int(round_number) if round_number else None,
        )
        return Response(result)


class CheckinOpenView(TOCBaseView):
    """Open checkin window."""

    def post(self, request, slug):
        window = int(request.data.get("window_minutes", 15))
        result = TOCCheckinService.open_checkin(self.tournament, window_minutes=window)
        return Response(result)


class CheckinCloseView(TOCBaseView):
    """Close checkin window."""

    def post(self, request, slug):
        result = TOCCheckinService.close_checkin(self.tournament)
        return Response(result)


class CheckinForceView(TOCBaseView):
    """Force-checkin a participant (admin override)."""

    def post(self, request, slug):
        participant_id = request.data.get("participant_id")
        if not participant_id:
            return Response({"error": "participant_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        result = TOCCheckinService.force_checkin(
            self.tournament, participant_id=int(participant_id),
        )
        return Response(result)


class CheckinForceMatchView(TOCBaseView):
    """Force check-in for a specific match side."""

    def post(self, request, slug):
        match_id = request.data.get("match_id")
        if not match_id:
            return Response({"error": "match_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        side = request.data.get("side", 1)
        result = TOCCheckinService.force_checkin_match(
            self.tournament, match_id=int(match_id), side=int(side),
        )
        return Response(result)


class CheckinAutoDQView(TOCBaseView):
    """Auto-DQ all participants who haven't checked in."""

    def post(self, request, slug):
        result = TOCCheckinService.auto_dq(self.tournament)
        return Response(result)


class CheckinConfigView(TOCBaseView):
    """Update checkin configuration."""

    def post(self, request, slug):
        result = TOCCheckinService.update_checkin_config(
            self.tournament, request.data,
        )
        return Response(result)


class CheckinBlastReminderView(TOCBaseView):
    """Send check-in reminder to all pending participants."""

    def post(self, request, slug):
        result = TOCCheckinService.blast_reminder(self.tournament)
        return Response(result)


class CheckinStatsView(TOCBaseView):
    """Checkin analytics / stats."""

    def get(self, request, slug):
        result = TOCCheckinService.get_checkin_stats(self.tournament)
        return Response(result)
