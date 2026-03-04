"""
TOC API Views — Sprint 28: Teams / Roster Management tab.

GET   rosters/                     — Full roster dashboard
POST  rosters/lock/                — Lock rosters
POST  rosters/unlock/              — Unlock rosters
POST  rosters/captain/             — Set team captain
POST  rosters/remove-player/       — Remove player from roster
POST  rosters/add-player/          — Add player to roster
POST  rosters/config/              — Update roster config
POST  rosters/lineup/              — Submit match-day lineup
GET   rosters/eligibility/<team>/  — Check team eligibility
"""

from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.rosters_service import TOCRostersService


class RostersDashboardView(TOCBaseView):
    """Full roster management dashboard."""

    def get(self, request, slug):
        result = TOCRostersService.get_rosters_dashboard(self.tournament)
        return Response(result)


class RostersLockView(TOCBaseView):
    """Lock all rosters."""

    def post(self, request, slug):
        result = TOCRostersService.lock_rosters(self.tournament)
        return Response(result)


class RostersUnlockView(TOCBaseView):
    """Unlock all rosters."""

    def post(self, request, slug):
        result = TOCRostersService.unlock_rosters(self.tournament)
        return Response(result)


class RostersCaptainView(TOCBaseView):
    """Set team captain."""

    def post(self, request, slug):
        team_id = request.data.get("team_id")
        user_id = request.data.get("user_id")
        if not team_id or not user_id:
            return Response({"error": "team_id and user_id are required"}, status=status.HTTP_400_BAD_REQUEST)
        result = TOCRostersService.set_captain(
            self.tournament, team_id=int(team_id), user_id=int(user_id),
        )
        return Response(result)


class RostersRemovePlayerView(TOCBaseView):
    """Remove a player from a team roster."""

    def post(self, request, slug):
        team_id = request.data.get("team_id")
        user_id = request.data.get("user_id")
        if not team_id or not user_id:
            return Response({"error": "team_id and user_id are required"}, status=status.HTTP_400_BAD_REQUEST)
        result = TOCRostersService.remove_player(
            self.tournament, team_id=int(team_id), user_id=int(user_id),
        )
        return Response(result)


class RostersAddPlayerView(TOCBaseView):
    """Add a player to a team roster."""

    def post(self, request, slug):
        team_id = request.data.get("team_id")
        if not team_id:
            return Response({"error": "team_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        result = TOCRostersService.add_player(
            self.tournament, team_id=int(team_id), data=request.data,
        )
        return Response(result)


class RostersConfigView(TOCBaseView):
    """Update roster configuration."""

    def post(self, request, slug):
        result = TOCRostersService.update_roster_config(self.tournament, request.data)
        return Response(result)


class RostersLineupView(TOCBaseView):
    """Submit a match-day lineup."""

    def post(self, request, slug):
        team_id = request.data.get("team_id")
        if not team_id:
            return Response({"error": "team_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        result = TOCRostersService.submit_lineup(
            self.tournament, team_id=int(team_id), data=request.data,
        )
        return Response(result)


class RostersEligibilityView(TOCBaseView):
    """Check team eligibility."""

    def get(self, request, slug, team_id):
        result = TOCRostersService.check_eligibility(
            self.tournament, team_id=int(team_id),
        )
        return Response(result)
