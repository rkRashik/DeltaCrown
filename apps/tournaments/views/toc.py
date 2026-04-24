"""
Tournament Operations Center (TOC) — Main Entry View.

Single entry-point CBV that renders the SPA shell.
All subsequent data loading happens via AJAX (TOC API, future sprints).

Sprint 0 — Foundation Shell
PRD: §1.2, §1.3 (TOC Architecture, Tab Structure)
Tracker: S0-B3
"""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.http import Http404
from django.urls import reverse
from django.views.generic import TemplateView

from apps.tournaments.api.toc.settings_service import TOCSettingsService
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.lifecycle_service import TournamentLifecycleService


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
            tournament = Tournament.objects.select_related('game', 'organizer').get(
                slug=slug
            )
            try:
                TournamentLifecycleService.auto_advance(tournament)
                tournament.refresh_from_db(fields=['status'])
            except Exception:
                pass
            return tournament
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
        ctx['game_id_label'] = getattr(game, 'game_id_label', 'Game ID') if game else 'Game ID'
        ctx['tournament_mode'] = getattr(t, 'mode', 'online')
        ctx['game_colors'] = {
            'primary': getattr(game, 'primary_color', '#3B82F6') or '#3B82F6',
            'secondary': getattr(game, 'secondary_color', '#8B5CF6') or '#8B5CF6',
            'accent': getattr(game, 'accent_color', '#06B6D4') or '#06B6D4',
            'primary_rgb': getattr(game, 'primary_color_rgb', '59, 130, 246') if game else '59, 130, 246',
        }
        ctx['status'] = getattr(t, 'get_effective_status', lambda: t.status)()
        ctx['effective_status_display'] = dict(Tournament.STATUS_CHOICES).get(
            ctx['status'], t.get_status_display()
        )
        ctx['is_organizer'] = (t.organizer_id == self.request.user.id)
        ctx['is_frozen'] = bool((t.config or {}).get('frozen'))
        ctx['is_official'] = getattr(t, 'is_official', False)
        ctx['can_view_logs'] = bool(
            self.request.user.is_superuser
            or self.request.user.is_staff
            or t.organizer_id == self.request.user.id
        )

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
        # Tree-style brackets only — Swiss has rounds + standings, no bracket tree.
        has_brackets = fmt in ('single_elimination', 'double_elimination', 'group_playoff')
        # Standings tab applies to any non-tree format (RR, Swiss, group play).
        has_standings = fmt in ('group_playoff', 'round_robin', 'swiss')
        # Backwards compatibility for templates/JS that still read has_groups.
        has_groups = has_standings
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
        if has_standings:
            base_tabs.append({'id': 'standings', 'label': 'Standings', 'icon': 'trophy', 'group': 'Competition'})
        base_tabs.append({'id': 'streams', 'label': 'Streams', 'icon': 'tv', 'group': 'Competition'})
        # Show Lobbies for multiplayer/team games or when game has dedicated servers
        game_category = getattr(game, 'category', 'OTHER') if game else 'OTHER'
        show_lobby = game_has_servers or (not is_solo) or game_category in ('FPS', 'MOBA', 'BR', 'SPORTS')
        if show_lobby:
            base_tabs.append({'id': 'lobby', 'label': 'Lobbies', 'icon': 'server', 'group': 'Competition'})
        base_tabs.extend([
            {'id': 'disputes', 'label': 'Disputes', 'icon': 'scale', 'group': 'Platform'},
            {'id': 'announcements', 'label': 'Announcements', 'icon': 'megaphone', 'group': 'Platform'},
            {'id': 'notifications', 'label': 'Notifications', 'icon': 'bell', 'group': 'Platform'},
        ])
        if ctx['can_view_logs']:
            base_tabs.append({'id': 'logs', 'label': 'Logs', 'icon': 'activity', 'group': 'Platform'})
        base_tabs.extend([
            {'id': 'rules', 'label': 'Rules & Info', 'icon': 'book-open', 'group': 'Platform'},
            {'id': 'settings', 'label': 'Settings', 'icon': 'settings', 'group': 'Platform'},
            {'id': 'prizes', 'label': 'Prizes & Awards', 'icon': 'trophy', 'group': 'Engagement'},
            {'id': 'public-hub-config', 'label': 'Public Hub Config', 'icon': 'monitor-smartphone', 'group': 'Engagement'},
            {'id': 'fan-predictions', 'label': 'Fan Predictions', 'icon': 'pie-chart', 'group': 'Engagement'},
            {'id': 'match-center', 'label': 'Match Center', 'icon': 'monitor-play', 'group': 'Engagement'},
        ])

        ctx['toc_tabs'] = base_tabs
        ctx['participation_type'] = participation
        ctx['is_solo'] = is_solo
        ctx['has_brackets'] = has_brackets
        ctx['has_groups'] = has_groups
        ctx['has_standings'] = has_standings
        ctx['tournament_format'] = fmt
        ctx['current_stage'] = t.get_current_stage() if hasattr(t, 'get_current_stage') else ''

        # Provide initial settings payload so Settings tab can hydrate even if
        # runtime API calls fail due transient client/network issues.
        try:
            initial_settings = TOCSettingsService.get_settings(t)
        except Exception:
            initial_settings = {}
        ctx['toc_initial_settings_json'] = json.dumps(initial_settings, cls=DjangoJSONEncoder)

        config = t.config if isinstance(t.config, dict) else {}
        detail_widgets = config.get('detail_widgets') if isinstance(config.get('detail_widgets'), dict) else {}
        ctx['toc_initial_detail_widgets_json'] = json.dumps(detail_widgets, cls=DjangoJSONEncoder)
        ctx['toc_detail_page_url'] = reverse('tournaments:detail', kwargs={'slug': t.slug})
        ctx['toc_tournament_hub_url'] = reverse('tournaments:tournament_hub', kwargs={'slug': t.slug})
        ctx['toc_detail_widgets_save_url'] = reverse('tournaments:detail_widgets_save', kwargs={'slug': t.slug})
        ctx['toc_match_center_api_url'] = reverse('toc_api:match-center-config', kwargs={'slug': t.slug})
        ctx['toc_match_center_public_url_template'] = reverse(
            'tournaments:match_detail',
            kwargs={'slug': t.slug, 'match_id': 0},
        ).replace('/0/', '/__MATCH_ID__/')

        return ctx


class TOCFormConfigurationView(TOCView):
    """Dedicated modern page for organizer form configuration management."""

    template_name = 'tournaments/toc/form_configuration.html'
