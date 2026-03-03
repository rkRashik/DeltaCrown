"""
Draw Director & Public Spectator Views

These views serve the standalone draw ceremony pages:
1. GroupDrawDirectorView — Organizer-only draw control panel
2. GroupDrawPublicView — Public spectator view for live draw broadcast
"""
import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.tournaments.models import Tournament, Registration
from apps.tournaments.models.group import Group

logger = logging.getLogger(__name__)


def _mint_ws_token(user):
    """
    Generate a short-lived JWT access token for WebSocket auth.

    The browser's native WebSocket API does not support custom headers
    (Authorization: Bearer), so the token is appended as a ?token= query
    parameter.  The JWTAuthMiddleware in the ASGI layer parses it.
    """
    try:
        from rest_framework_simplejwt.tokens import AccessToken
        token = AccessToken.for_user(user)
        return str(token)
    except Exception:
        logger.warning("Could not mint WS JWT for user %s", user, exc_info=True)
        return ""


class GroupDrawDirectorView(LoginRequiredMixin, TemplateView):
    """
    Organizer's Group Draw Director panel.
    URL: /tournaments/<slug>/draw/director/
    Requires login + organizer/staff permission.
    """
    template_name = "tournaments/draw_director.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        tournament = get_object_or_404(
            Tournament.objects.select_related("organizer"),
            slug=slug,
        )
        # Permission check: organizer or staff only
        user = self.request.user
        if tournament.organizer_id != user.id and not user.is_staff:
            raise Http404("Only the tournament organizer can access the Draw Director.")

        ctx["tournament"] = tournament
        ctx["tournament_id"] = tournament.id
        ctx["ws_url"] = f"/ws/tournament/{tournament.id}/group-draw/"
        ctx["ws_auth_token"] = _mint_ws_token(user)

        # ── Pre-load groups for empty-state grid ──
        groups = Group.objects.filter(
            tournament=tournament, is_deleted=False,
        ).order_by("display_order", "name")
        groups_data = []
        for g in groups:
            letter = g.name.split()[-1] if " " in g.name else g.name
            groups_data.append({
                "name": letter,
                "max_participants": g.max_participants,
            })
        ctx["groups_json"] = json.dumps(groups_data)

        # ── Pre-load confirmed participants for queue ──
        regs = Registration.objects.filter(
            tournament=tournament,
            status=Registration.CONFIRMED,
            is_deleted=False,
        ).select_related("user")
        participants = []
        for reg in regs:
            name = ""
            uid = None
            if reg.user:
                name = reg.user.username
                uid = reg.user.id
            elif reg.team_id:
                try:
                    from apps.organizations.models import Team
                    team = Team.objects.get(id=reg.team_id)
                    name = team.name
                except Exception:
                    name = f"Team #{reg.team_id}"
                uid = reg.team_id
            else:
                name = f"Registration #{reg.registration_number}"
                uid = reg.id
            participants.append({
                "registration_id": reg.id,
                "user_id": uid,
                "name": name,
                "display_name": name,
            })
        ctx["participants_json"] = json.dumps(participants)
        ctx["participant_count"] = len(participants)
        ctx["group_count"] = len(groups_data)

        return ctx


class GroupDrawPublicView(TemplateView):
    """
    Public spectator view for the live group draw broadcast.
    URL: /tournaments/<slug>/draw/live/
    No login required — anyone can watch the draw.
    """
    template_name = "tournaments/draw_spectator.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        tournament = get_object_or_404(Tournament, slug=slug)
        ctx["tournament"] = tournament
        ctx["tournament_id"] = tournament.id
        ctx["ws_url"] = f"/ws/tournament/{tournament.id}/group-draw/"
        return ctx
