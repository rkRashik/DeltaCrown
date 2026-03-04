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
        """Verify user has organizer-level or staff-level access."""
        if user.is_superuser or user.is_staff:
            return True
        if tournament.organizer_id == user.id:
            return True
        # Check StaffRole assignments (Sprint 10G RBAC)
        from apps.tournaments.models.staffing import TournamentStaffAssignment
        return TournamentStaffAssignment.objects.filter(
            tournament=tournament, user=user, is_active=True,
        ).exists()

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
        ctx['game_category'] = getattr(game, 'category', 'OTHER') if game else 'OTHER'
        ctx['game_type'] = getattr(game, 'game_type', 'TEAM_VS_TEAM') if game else 'TEAM_VS_TEAM'
        ctx['tournament_mode'] = getattr(t, 'mode', 'online')
        ctx['game_colors'] = {
            'primary': getattr(game, 'primary_color', '#3B82F6') or '#3B82F6',
            'secondary': getattr(game, 'secondary_color', '#8B5CF6') or '#8B5CF6',
            'accent': getattr(game, 'accent_color', '#06B6D4') or '#06B6D4',
            'primary_rgb': getattr(game, 'primary_color_rgb', '59, 130, 246') if game else '59, 130, 246',
        }
        ctx['status'] = t.status
        ctx['is_organizer'] = (t.organizer_id == self.request.user.id)
        ctx['is_frozen'] = bool((t.config or {}).get('frozen'))
        ctx['is_official'] = getattr(t, 'is_official', False)

        # Inject user capabilities for frontend RBAC enforcement
        user = self.request.user
        if user.is_superuser or user.is_staff or t.organizer_id == user.id:
            ctx['user_capabilities'] = ['full_access']
        else:
            from apps.tournaments.models.staffing import TournamentStaffAssignment
            assignments = TournamentStaffAssignment.objects.filter(
                tournament=t, user=user, is_active=True,
            ).select_related('role')
            caps = set()
            for a in assignments:
                role_caps = getattr(a.role, 'capabilities', {}) or {}
                for cap_name, enabled in role_caps.items():
                    if enabled:
                        caps.add(cap_name)
            ctx['user_capabilities'] = sorted(caps) if caps else ['view_all']

        # Tab definitions for sidebar rendering — context-aware
        participation = getattr(t, 'participation_type', 'team')
        is_solo = participation == 'solo'
        fmt = getattr(t, 'format', '')
        has_brackets = fmt in ('single_elimination', 'double_elimination', 'group_playoff', 'swiss')
        has_groups = fmt in ('group_playoff', 'round_robin', 'swiss')
        game_has_servers = getattr(game, 'has_servers', False) if game else False

        base_tabs = [
            {'id': 'overview', 'label': 'Overview', 'icon': 'layout-dashboard', 'group': 'Management'},
            {'id': 'participants', 'label': 'Participants', 'icon': 'users', 'group': 'Management'},
            {'id': 'payments', 'label': 'Payments', 'icon': 'wallet', 'group': 'Management'},
        ]
        if not is_solo:
            base_tabs.append({'id': 'rosters', 'label': 'Rosters', 'icon': 'users-round', 'group': 'Management'})
        base_tabs.extend([
            {'id': 'checkin', 'label': 'Check-in', 'icon': 'user-check', 'group': 'Management'},
            {'id': 'analytics', 'label': 'Analytics', 'icon': 'bar-chart-3', 'group': 'Management'},
        ])
        if has_brackets:
            base_tabs.append({'id': 'brackets', 'label': 'Brackets', 'icon': 'git-branch', 'group': 'Competition'})
        base_tabs.extend([
            {'id': 'matches', 'label': 'Matches', 'icon': 'swords', 'group': 'Competition'},
            {'id': 'schedule', 'label': 'Schedule', 'icon': 'calendar', 'group': 'Competition'},
        ])
        if has_groups:
            base_tabs.append({'id': 'standings', 'label': 'Standings', 'icon': 'trophy', 'group': 'Competition'})
        base_tabs.append({'id': 'streams', 'label': 'Streams', 'icon': 'tv', 'group': 'Competition'})
        # Show Lobbies for multiplayer/team games or when game has dedicated servers
        game_category = getattr(game, 'category', 'OTHER') if game else 'OTHER'
        show_lobby = game_has_servers or (not is_solo) or game_category in ('FPS', 'MOBA', 'BR', 'SPORTS')
        if show_lobby:
            base_tabs.append({'id': 'lobby', 'label': 'Lobbies', 'icon': 'server', 'group': 'Competition'})
        base_tabs.extend([
            {'id': 'disputes', 'label': 'Disputes', 'icon': 'scale', 'group': 'Platform'},
            {'id': 'notifications', 'label': 'Notifications', 'icon': 'bell', 'group': 'Platform'},
            {'id': 'rules', 'label': 'Rules & Info', 'icon': 'book-open', 'group': 'Platform'},
            {'id': 'settings', 'label': 'Settings', 'icon': 'settings', 'group': 'Platform'},
        ])

        ctx['toc_tabs'] = base_tabs
        ctx['participation_type'] = participation
        ctx['is_solo'] = is_solo
        ctx['has_brackets'] = has_brackets
        ctx['has_groups'] = has_groups
        ctx['tournament_format'] = fmt

        return ctx
