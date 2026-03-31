from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.models import Match, Registration, Tournament
from apps.tournaments.models.group import Group, GroupStanding
from apps.tournaments.services.bracket_service import BracketService


User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def sync_game(db):
    return Game.objects.create(
        name='Sync Test Game',
        slug='sync-test-game',
        default_team_size=1,
        profile_id_field='ingame_id',
        default_result_type='map_score',
        is_active=True,
    )


@pytest.fixture
def sync_users(db):
    organizer = User.objects.create_user(
        username='sync-organizer',
        email='sync-organizer@test.com',
        password='pass123',
    )
    player_one = User.objects.create_user(
        username='sync-player-one',
        email='sync-player-one@test.com',
        password='pass123',
    )
    player_two = User.objects.create_user(
        username='sync-player-two',
        email='sync-player-two@test.com',
        password='pass123',
    )
    return organizer, player_one, player_two


@pytest.fixture
def sync_tournament(db, sync_game, sync_users):
    organizer, _, _ = sync_users
    now = timezone.now()
    return Tournament.objects.create(
        name='Completion Sync Tournament',
        slug='completion-sync-tournament',
        organizer=organizer,
        game=sync_game,
        format=Tournament.GROUP_PLAYOFF,
        participation_type=Tournament.SOLO,
        max_participants=8,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(hours=3),
        tournament_end=now + timedelta(days=2),
        status=Tournament.LIVE,
    )


def test_update_bracket_after_match_uses_state_field(sync_tournament, sync_users):
    _, player_one, player_two = sync_users
    match = Match.objects.create(
        tournament=sync_tournament,
        round_number=1,
        match_number=1,
        participant1_id=player_one.id,
        participant1_name='Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        state=Match.COMPLETED,
        participant1_score=4,
        participant2_score=0,
        winner_id=player_one.id,
        loser_id=player_two.id,
    )

    # No BracketNode link should safely no-op instead of failing on missing match.status.
    result = BracketService.update_bracket_after_match(match)
    assert result is None


def test_match_completion_signal_recalculates_group_standings(sync_tournament, sync_users):
    _, player_one, player_two = sync_users

    Registration.objects.create(
        tournament=sync_tournament,
        user=player_one,
        status=Registration.CONFIRMED,
        registration_data={},
    )
    Registration.objects.create(
        tournament=sync_tournament,
        user=player_two,
        status=Registration.CONFIRMED,
        registration_data={},
    )

    group = Group.objects.create(
        tournament=sync_tournament,
        name='Group A',
        display_order=0,
        max_participants=4,
        advancement_count=1,
    )

    standing_one = GroupStanding.objects.create(
        group=group,
        user=player_one,
        rank=0,
        points=Decimal('0.00'),
    )
    standing_two = GroupStanding.objects.create(
        group=group,
        user=player_two,
        rank=0,
        points=Decimal('0.00'),
    )

    match = Match.objects.create(
        tournament=sync_tournament,
        round_number=1,
        match_number=1,
        participant1_id=player_one.id,
        participant1_name='Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        state=Match.SCHEDULED,
        participant1_score=0,
        participant2_score=0,
        lobby_info={
            'group_id': group.id,
            'group_name': group.name,
        },
        scheduled_time=timezone.now() + timedelta(hours=1),
    )

    match.participant1_score = 4
    match.participant2_score = 0
    match.winner_id = player_one.id
    match.loser_id = player_two.id
    match.state = Match.COMPLETED
    match.completed_at = timezone.now()
    match.save(update_fields=['participant1_score', 'participant2_score', 'winner_id', 'loser_id', 'state', 'completed_at', 'updated_at'])

    standing_one.refresh_from_db()
    standing_two.refresh_from_db()

    assert standing_one.matches_played == 1
    assert standing_one.matches_won == 1
    assert standing_one.matches_lost == 0
    assert standing_one.points > Decimal('0')

    assert standing_two.matches_played == 1
    assert standing_two.matches_won == 0
    assert standing_two.matches_lost == 1
    assert standing_two.points >= Decimal('0')
