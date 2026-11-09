"""
Public Spectator View for live tournaments.

This view provides a comprehensive spectator experience combining:
- Live bracket visualization
- Tournament leaderboard
- Group standings (if applicable)
- Match results
- Tournament information

Implementation Date: November 20, 2025
Feature: FE-T-006 (P1)
"""

from django.views.generic import TemplateView
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Prefetch

from apps.tournaments.models import Tournament, Match, Bracket
from apps.tournaments.models.group import GroupStanding
from apps.tournaments.views.leaderboard import TournamentLeaderboardView

_LIVE_STATES = (Match.LIVE, Match.PENDING_RESULT)
_UPCOMING_STATES = (Match.SCHEDULED, Match.CHECK_IN, Match.READY)


class PublicSpectatorView(TemplateView):
    """
    Public spectator view for live and completed tournaments.

    Provides a unified interface for spectators to:
    - Open the live bracket
    - Check current standings/leaderboard
    - View recent and upcoming matches

    No authentication required. Only public data is used: participant display
    names (as on the public bracket/leaderboard) and scores, never contact,
    payment or registration details. Draft and pending-approval tournaments are
    never shown.
    """

    template_name = 'tournaments/spectator/hub.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tournament = get_object_or_404(
            Tournament.objects.filter(is_deleted=False).select_related('organizer', 'game'),
            slug=self.kwargs.get('slug'),
        )

        # Only live/completed tournaments have anything to spectate.
        if tournament.status not in (Tournament.LIVE, Tournament.COMPLETED):
            raise Http404("Spectator view only available for live or completed tournaments")

        context['tournament'] = tournament
        context['active_tab'] = self.request.GET.get('tab', 'bracket')

        bracket = Bracket.objects.filter(tournament=tournament).first()
        context['bracket'] = bracket
        context['has_bracket'] = bracket is not None

        # Group stage standings (group_playoff format)
        context['has_groups'] = False
        if tournament.format == Tournament.GROUP_PLAYOFF:
            groups = list(
                tournament.groups.filter(is_deleted=False).prefetch_related(
                    Prefetch(
                        'standings',
                        queryset=GroupStanding.objects.select_related('user').order_by('rank'),
                    )
                )
            )
            context['groups'] = groups
            context['has_groups'] = bool(groups)

        # Leaderboard: same public computation as /tournaments/<slug>/leaderboard/
        leaderboard = TournamentLeaderboardView()
        leaderboard.request = self.request
        context['standings'] = leaderboard._calculate_standings(tournament)[:50]

        matches = Match.objects.filter(tournament=tournament, is_deleted=False)
        context['recent_matches'] = matches.filter(
            state=Match.COMPLETED
        ).order_by('-completed_at', '-id')[:10]
        context['upcoming_matches'] = matches.filter(
            state__in=_UPCOMING_STATES, scheduled_time__isnull=False
        ).order_by('scheduled_time', 'id')[:10]

        context['total_matches'] = matches.count()
        context['completed_matches'] = matches.filter(state=Match.COMPLETED).count()
        context['live_matches'] = matches.filter(state__in=_LIVE_STATES).count()

        return context
