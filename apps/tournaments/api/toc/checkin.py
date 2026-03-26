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

from django.core.cache import cache
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import bump_toc_scopes, toc_cache_key
from apps.tournaments.api.toc.checkin_service import TOCCheckinService


class CheckinDashboardView(TOCBaseView):
    """Full checkin dashboard."""

    def get(self, request, slug):
        round_number = request.query_params.get("round")
        cache_bucket = int(timezone.now().timestamp() // 8)
        cache_key = toc_cache_key('checkin', self.tournament.id, 'dashboard', round_number or '', cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCCheckinService.get_checkin_dashboard(
            self.tournament,
            round_number=int(round_number) if round_number else None,
        )
        cache.set(cache_key, result, timeout=12)
        return Response(result)


class CheckinOpenView(TOCBaseView):
    """Open checkin window."""

    def post(self, request, slug):
        window = int(request.data.get("window_minutes", 15))
        result = TOCCheckinService.open_checkin(self.tournament, window_minutes=window)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        bump_toc_scopes(self.tournament.id, 'checkin', 'participants', 'matches', 'overview')
        return Response(result)


class CheckinCloseView(TOCBaseView):
    """Close checkin window."""

    def post(self, request, slug):
        result = TOCCheckinService.close_checkin(self.tournament)
        bump_toc_scopes(self.tournament.id, 'checkin', 'participants', 'matches', 'overview')
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
        bump_toc_scopes(self.tournament.id, 'checkin', 'participants', 'matches', 'overview')
        return Response(result)


class CheckinForceMatchView(TOCBaseView):
    """Force check-in for a specific match side."""

    def post(self, request, slug):
        match_id = request.data.get("match_id")
        if not match_id:
            return Response({"error": "match_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        side = str(request.data.get("side", "p1")).lower()
        if side in {"1", "p1", "participant1"}:
            side = "p1"
        elif side in {"2", "p2", "participant2"}:
            side = "p2"
        result = TOCCheckinService.force_checkin_match(
            self.tournament, match_id=int(match_id), side=side,
        )
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        bump_toc_scopes(self.tournament.id, 'checkin', 'participants', 'matches', 'overview')
        return Response(result)


class CheckinAutoDQView(TOCBaseView):
    """Auto-DQ all participants who haven't checked in."""

    def post(self, request, slug):
        result = TOCCheckinService.auto_dq(self.tournament)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        bump_toc_scopes(self.tournament.id, 'checkin', 'participants', 'matches', 'overview')
        return Response(result)


class CheckinConfigView(TOCBaseView):
    """Update checkin configuration."""

    def post(self, request, slug):
        result = TOCCheckinService.update_checkin_config(
            self.tournament, request.data,
        )
        bump_toc_scopes(self.tournament.id, 'checkin', 'overview')
        return Response(result)


class CheckinBlastReminderView(TOCBaseView):
    """Send check-in reminder to all pending participants."""

    def post(self, request, slug):
        result = TOCCheckinService.blast_reminder(self.tournament)
        bump_toc_scopes(self.tournament.id, 'checkin')
        return Response(result)


class CheckinStatsView(TOCBaseView):
    """Checkin analytics / stats."""

    def get(self, request, slug):
        cache_bucket = int(timezone.now().timestamp() // 10)
        cache_key = toc_cache_key('checkin', self.tournament.id, 'stats', cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        result = TOCCheckinService.get_checkin_stats(self.tournament)
        cache.set(cache_key, result, timeout=15)
        return Response(result)
