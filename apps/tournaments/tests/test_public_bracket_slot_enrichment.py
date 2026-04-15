from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Bracket, BracketNode, Game, Match, Tournament
from apps.tournaments.views.live import TournamentBracketView


User = get_user_model()
pytestmark = pytest.mark.django_db


def test_public_bracket_view_enriches_placeholder_slots_from_bracket_nodes():
    organizer = User.objects.create_user(
        username='public-bracket-organizer',
        email='public-bracket-organizer@test.com',
        password='pass123',
    )

    game = Game.objects.create(
        name='Public Bracket Game',
        slug='public-bracket-game',
        is_active=True,
    )

    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Public Bracket Tournament',
        slug='public-bracket-tournament',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIMINATION,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=2),
        registration_end=now - timedelta(days=1),
        tournament_start=now - timedelta(hours=3),
        tournament_end=now + timedelta(days=1),
        status=Tournament.LIVE,
    )

    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=2,
        total_matches=3,
        is_finalized=True,
        generated_at=now - timedelta(hours=2),
        bracket_structure={
            'rounds': [
                {'round_number': 1, 'round_name': 'Semi Finals', 'matches': 2},
                {'round_number': 2, 'round_name': 'Finals', 'matches': 1},
            ]
        },
    )

    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=101,
        participant1_name='Alpha',
        participant2_id=102,
        participant2_name='Bravo',
        state=Match.COMPLETED,
        participant1_score=2,
        participant2_score=0,
        winner_id=101,
        loser_id=102,
    )

    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=2,
        participant1_id=103,
        participant1_name='Charlie',
        participant2_id=104,
        participant2_name='Delta',
        state=Match.SCHEDULED,
    )

    BracketNode.objects.create(
        bracket=bracket,
        position=3,
        round_number=2,
        match_number_in_round=1,
        participant1_id=101,
        participant1_name='Alpha',
        participant2_id=None,
        participant2_name='',
    )

    request = RequestFactory().get(reverse('tournaments:bracket', kwargs={'slug': tournament.slug}))
    view = TournamentBracketView()
    view.setup(request, slug=tournament.slug)
    view.object = tournament
    context = view.get_context_data(object=tournament)

    rounds = context['matches_by_round']
    finals_round = next(row for row in rounds if row['round_number'] == 2)
    finals_match = next(row for row in finals_round['matches'] if row['match_number'] == 1)

    assert finals_match['id'] is None
    assert finals_match['participant1_id'] == 101
    assert finals_match['team1_name'] == 'Alpha'
    assert finals_match['team2_name'] == 'TBD'
