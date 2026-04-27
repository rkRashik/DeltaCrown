"""
Tournament Creation Page — Frontend View.

Serves the modern tournament creation wizard at /tournaments/create/.
Authenticated users can create tournaments by paying a DeltaCoin hosting fee.
Staff/superuser users are exempt from the fee.

POST submission goes to the DRF API endpoint; this view only serves the GET page
with all necessary context (games, balance, pricing, suggestions).
"""

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from django.views.generic import TemplateView

from apps.games.models.game import Game
from apps.tournaments.services.game_suggestions import build_game_intelligence_payload
from apps.tournaments.services.hosting_fee import get_hosting_fee, get_user_balance

logger = logging.getLogger(__name__)


def _get_user_profile(user):
    """Safely fetch user profile for avatar display."""
    try:
        from apps.user_profile.models import UserProfile
        return UserProfile.objects.filter(user=user).first()
    except Exception:
        return None


class TournamentCreatePageView(LoginRequiredMixin, TemplateView):
    """
    Tournament Creation Wizard — page view.

    Renders a 4-step wizard UI for creating tournaments.
    All game intelligence, DeltaCoin pricing, and user balance
    are injected into the template context as JSON for the JS engine.

    URL: /tournaments/create/
    Auth: LoginRequiredMixin (redirects anonymous users)
    """

    template_name = 'tournaments/create/tournament_create.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # Load active games with related configs for intelligence
        games_qs = (
            Game.objects
            .filter(is_active=True)
            .select_related('roster_config', 'tournament_config')
            .order_by('name')
        )

        # Build game intelligence payload for JS
        game_intelligence = build_game_intelligence_payload(games_qs)

        # DeltaCoin info
        is_staff = user.is_staff or user.is_superuser
        hosting_fee = 0 if is_staff else get_hosting_fee()
        user_balance = get_user_balance(user) if not is_staff else 0
        after_balance = max(user_balance - hosting_fee, 0)

        # Tournament format choices (mirroring model)
        from apps.tournaments.models.tournament import Tournament
        format_choices = [
            {
                'value': 'single_elimination',
                'label': 'Single Elimination',
                'description': 'One loss and you\'re out. Fast-paced, high stakes.',
                'icon': 'trophy',
                'best_for': '8-64 participants',
            },
            {
                'value': 'double_elimination',
                'label': 'Double Elimination',
                'description': 'Two losses to be eliminated. More forgiving, longer event.',
                'icon': 'shield',
                'best_for': '8-32 participants',
            },
            {
                'value': 'round_robin',
                'label': 'Round Robin',
                'description': 'Everyone plays everyone. Best for Battle Royale & smaller groups.',
                'icon': 'refresh-cw',
                'best_for': '4-20 participants',
            },
            {
                'value': 'swiss',
                'label': 'Swiss System',
                'description': 'Players matched by similar record each round. Efficient ranking.',
                'icon': 'layers',
                'best_for': '8-32 participants',
            },
            {
                'value': 'group_playoff',
                'label': 'Group Stage + Playoffs',
                'description': 'Round-robin groups followed by elimination bracket. Pro-level format.',
                'icon': 'git-merge',
                'best_for': '16-64 participants',
            },
        ]

        # Platform choices
        platform_choices = [
            {'value': 'pc', 'label': 'PC', 'icon': 'monitor'},
            {'value': 'mobile', 'label': 'Mobile', 'icon': 'smartphone'},
            {'value': 'console', 'label': 'Console', 'icon': 'gamepad-2'},
            {'value': 'cross_platform', 'label': 'Cross-Platform', 'icon': 'globe'},
        ]

        ctx.update({
            # JSON data for JS engine
            'games_json': json.dumps(game_intelligence, cls=DjangoJSONEncoder),
            'format_choices_json': json.dumps(format_choices, cls=DjangoJSONEncoder),
            'platform_choices_json': json.dumps(platform_choices, cls=DjangoJSONEncoder),

            # DeltaCoin
            'is_staff': is_staff,
            'hosting_fee': hosting_fee,
            'user_balance': user_balance,
            'after_balance': after_balance,
            'can_afford': is_staff or (user_balance >= hosting_fee),

            # API endpoint for form submission
            'api_create_url': reverse('tournaments_api:tournament-list'),

            # User info
            'username': user.username,
            'user_profile': _get_user_profile(user),
        })

        return ctx
