"""
Tournament Operations Center (TOC) — Main Entry View.

Single entry-point CBV that renders the SPA shell.
All subsequent data loading happens via AJAX (TOC API, future sprints).

Sprint 0 — Foundation Shell
PRD: §1.2, §1.3 (TOC Architecture, Tab Structure)
Tracker: S0-B3
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import TemplateView

from apps.tournaments.models.tournament import Tournament


class TOCView(LoginRequiredMixin, TemplateView):
    """
    Tournament Operations Center — organizer SPA shell.

    Permissions:
    - User must be authenticated (LoginRequiredMixin)
    - User must be the tournament organizer OR a staff/superuser
    - Future sprints add granular RBAC (S10)

    Context:
    - tournament: The Tournament object
    - game: The Game object (for theming)
    - game_slug: Game slug for [data-game] attribute
    - game_colors: Dict of primary/secondary/accent colors
    - status: Tournament status string
    - is_organizer: True if current user owns the tournament
    - toc_tabs: Ordered list of tab definitions for sidebar
    """

    template_name = 'tournaments/toc/base.html'

    def get_tournament(self):
        slug = self.kwargs.get('slug')
        try:
            return Tournament.objects.select_related('game', 'organizer').get(
                slug=slug
            )
        except Tournament.DoesNotExist:
            raise Http404(f'Tournament not found: {slug}')

    def check_permission(self, tournament, user):
        """Verify user has organizer-level access."""
        if user.is_superuser or user.is_staff:
            return True
        if tournament.organizer_id == user.id:
            return True
        # Future: check StaffRole assignments (Sprint 10)
        return False

    def get(self, request, *args, **kwargs):
        tournament = self.get_tournament()
        if not self.check_permission(tournament, request.user):
            raise Http404('Not authorized')
        self.tournament = tournament
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        t = self.tournament
        game = t.game

        ctx['tournament'] = t
        ctx['game'] = game
        ctx['game_slug'] = game.slug if game else 'default'
        ctx['game_colors'] = {
            'primary': getattr(game, 'primary_color', '#3B82F6') or '#3B82F6',
            'secondary': getattr(game, 'secondary_color', '#8B5CF6') or '#8B5CF6',
            'accent': getattr(game, 'accent_color', '#06B6D4') or '#06B6D4',
            'primary_rgb': getattr(game, 'primary_color_rgb', '59, 130, 246') if game else '59, 130, 246',
        }
        ctx['status'] = t.status
        ctx['is_organizer'] = (t.organizer_id == self.request.user.id)
        ctx['is_frozen'] = bool((t.config or {}).get('frozen'))

        # Tab definitions for sidebar rendering
        ctx['toc_tabs'] = [
            {'id': 'overview', 'label': 'Overview', 'icon': 'layout-dashboard', 'group': 'Management'},
            {'id': 'participants', 'label': 'Participants', 'icon': 'users', 'group': 'Management'},
            {'id': 'payments', 'label': 'Payments', 'icon': 'wallet', 'group': 'Management'},
            {'id': 'brackets', 'label': 'Brackets', 'icon': 'git-branch', 'group': 'Competition'},
            {'id': 'matches', 'label': 'Matches', 'icon': 'swords', 'group': 'Competition'},
            {'id': 'schedule', 'label': 'Schedule', 'icon': 'calendar', 'group': 'Competition'},
            {'id': 'disputes', 'label': 'Disputes', 'icon': 'scale', 'group': 'Platform'},
            {'id': 'announcements', 'label': 'Announcements', 'icon': 'megaphone', 'group': 'Platform'},
            {'id': 'settings', 'label': 'Settings', 'icon': 'settings', 'group': 'Platform'},
        ]

        return ctx
