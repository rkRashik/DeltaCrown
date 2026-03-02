"""
Draw Director & Public Spectator Views

These views serve the standalone draw ceremony pages:
1. GroupDrawDirectorView — Organizer-only draw control panel
2. GroupDrawPublicView — Public spectator view for live draw broadcast
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from apps.tournaments.models import Tournament


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
