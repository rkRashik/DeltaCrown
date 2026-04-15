from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.tournaments.models import Bracket, Game, Match, Registration, Tournament
from apps.tournaments.services import lifecycle_announcements
from apps.tournaments.views.hub import _resolve_hub_command_center


User = get_user_model()
pytestmark = pytest.mark.django_db


def test_command_center_marks_participant_eliminated_after_terminal_loss_without_active_matches():
    organizer = User.objects.create_user(
        username='hub-command-organizer',
        email='hub-command-organizer@test.com',
        password='pass123',
    )
    player_one = User.objects.create_user(
        username='hub-command-player-one',
        email='hub-command-player-one@test.com',
        password='pass123',
    )
    player_two = User.objects.create_user(
        username='hub-command-player-two',
        email='hub-command-player-two@test.com',
        password='pass123',
    )

    game = Game.objects.create(
        name='Hub Command Game',
        slug='hub-command-game',
        is_active=True,
    )

    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Hub Command Tournament',
        slug='hub-command-tournament',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now - timedelta(hours=4),
        tournament_end=now + timedelta(days=2),
        status=Tournament.LIVE,
    )

    registration = Registration.objects.create(
        tournament=tournament,
        user=player_one,
        status=Registration.CONFIRMED,
        registration_data={},
    )

    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=3,
        total_matches=7,
    )

    terminal_match = Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=2,
        match_number=1,
        participant1_id=player_one.id,
        participant1_name='Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        state=Match.COMPLETED,
        winner_id=player_two.id,
        loser_id=player_one.id,
        completed_at=now - timedelta(minutes=5),
    )

    payload = _resolve_hub_command_center(
        tournament,
        registration,
        player_one,
        now=now,
    )

    assert payload['show'] is True
    assert payload['outcome_state'] == 'eliminated'
    assert payload['cta_action'] == 'open_bracket'
    assert payload['countdown_text'] == 'ELIMINATED'
    assert payload['match_id'] == terminal_match.id
    assert payload['match_stage_label'] == 'Knockout Stage'
    assert payload['outcome_experience']['enabled'] is True
    assert payload['outcome_experience']['spotlight']['enabled'] is True
    assert payload['outcome_experience']['persistent']['body']
    assert payload['outcome_experience']['community_post_suggestion']


def test_command_center_marks_eliminated_when_loser_id_exists_without_winner_id():
    organizer = User.objects.create_user(
        username='hub-loserid-organizer',
        email='hub-loserid-organizer@test.com',
        password='pass123',
    )
    player_one = User.objects.create_user(
        username='hub-loserid-player-one',
        email='hub-loserid-player-one@test.com',
        password='pass123',
    )
    player_two = User.objects.create_user(
        username='hub-loserid-player-two',
        email='hub-loserid-player-two@test.com',
        password='pass123',
    )

    game = Game.objects.create(
        name='Hub LoserId Game',
        slug='hub-loserid-game',
        is_active=True,
    )

    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Hub LoserId Tournament',
        slug='hub-loserid-tournament',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now - timedelta(hours=4),
        tournament_end=now + timedelta(days=2),
        status=Tournament.LIVE,
    )

    registration = Registration.objects.create(
        tournament=tournament,
        user=player_one,
        status=Registration.CONFIRMED,
        registration_data={},
    )

    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=3,
        total_matches=7,
    )

    terminal_match = Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=2,
        match_number=1,
        participant1_id=player_one.id,
        participant1_name='Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        state=Match.FORFEIT,
        winner_id=None,
        loser_id=player_one.id,
        completed_at=now - timedelta(minutes=2),
    )

    payload = _resolve_hub_command_center(
        tournament,
        registration,
        player_one,
        now=now,
    )

    assert payload['show'] is True
    assert payload['outcome_state'] == 'eliminated'
    assert payload['cta_action'] == 'open_bracket'
    assert payload['countdown_text'] == 'ELIMINATED'
    assert payload['match_id'] == terminal_match.id
    assert payload['outcome_experience']['enabled'] is True
    assert payload['outcome_experience']['spotlight']['enabled'] is True
    assert payload['outcome_experience']['persistent']['body']
    assert payload['outcome_experience']['community_post_suggestion']


def test_command_center_marks_participant_advanced_after_terminal_win_without_active_matches():
    organizer = User.objects.create_user(
        username='hub-advanced-organizer',
        email='hub-advanced-organizer@test.com',
        password='pass123',
    )
    player_one = User.objects.create_user(
        username='hub-advanced-player-one',
        email='hub-advanced-player-one@test.com',
        password='pass123',
    )
    player_two = User.objects.create_user(
        username='hub-advanced-player-two',
        email='hub-advanced-player-two@test.com',
        password='pass123',
    )

    game = Game.objects.create(
        name='Hub Advanced Game',
        slug='hub-advanced-game',
        is_active=True,
    )

    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Hub Advanced Tournament',
        slug='hub-advanced-tournament',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now - timedelta(hours=4),
        tournament_end=now + timedelta(days=2),
        status=Tournament.LIVE,
    )

    registration = Registration.objects.create(
        tournament=tournament,
        user=player_one,
        status=Registration.CONFIRMED,
        registration_data={},
    )

    bracket = Bracket.objects.create(
        tournament=tournament,
        format=Bracket.SINGLE_ELIMINATION,
        total_rounds=3,
        total_matches=7,
    )

    terminal_match = Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=player_one.id,
        participant1_name='Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        state=Match.COMPLETED,
        winner_id=player_one.id,
        loser_id=player_two.id,
        completed_at=now - timedelta(minutes=5),
    )

    payload = _resolve_hub_command_center(
        tournament,
        registration,
        player_one,
        now=now,
    )

    assert payload['show'] is True
    assert payload['outcome_state'] == 'advanced'
    assert payload['cta_action'] == 'open_bracket'
    assert payload['countdown_text'] == 'ADVANCED'
    assert payload['match_id'] == terminal_match.id
    assert payload['outcome_experience']['enabled'] is True
    assert payload['outcome_experience']['spotlight']['enabled'] is True
    assert payload['outcome_experience']['persistent']['body']
    assert payload['outcome_experience']['community_post_suggestion']


def test_command_center_uses_lifecycle_outcome_signal_for_overview_payload(monkeypatch):
    organizer = User.objects.create_user(
        username='hub-lifecycle-organizer',
        email='hub-lifecycle-organizer@test.com',
        password='pass123',
    )
    player = User.objects.create_user(
        username='hub-lifecycle-player',
        email='hub-lifecycle-player@test.com',
        password='pass123',
    )

    game = Game.objects.create(
        name='Hub Lifecycle Game',
        slug='hub-lifecycle-game',
        is_active=True,
    )

    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Hub Lifecycle Tournament',
        slug='hub-lifecycle-tournament',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now - timedelta(hours=4),
        tournament_end=now + timedelta(days=2),
        status=Tournament.LIVE,
    )

    registration = Registration.objects.create(
        tournament=tournament,
        user=player,
        status=Registration.CONFIRMED,
        registration_data={},
    )

    monkeypatch.setattr(
        lifecycle_announcements,
        'derive_participant_events',
        lambda *_args, **_kwargs: [
            {
                'event_type': lifecycle_announcements.EVENT_ADVANCED,
                'title': 'Advanced in Bracket',
                'message': 'Advanced in Bracket',
            }
        ],
    )

    payload = _resolve_hub_command_center(
        tournament,
        registration,
        player,
        now=now,
    )

    assert payload['show'] is True
    assert payload['outcome_state'] == 'advanced'
    assert payload['title'] == 'Advanced in Bracket'
    assert payload['outcome_experience']['source'] == 'announcement_signal'


def test_command_center_outcome_resolution_supports_registration_identifier_matches():
    organizer = User.objects.create_user(
        username='hub-registration-id-organizer',
        email='hub-registration-id-organizer@test.com',
        password='pass123',
    )
    player_one = User.objects.create_user(
        username='hub-registration-id-player-one',
        email='hub-registration-id-player-one@test.com',
        password='pass123',
    )
    player_two = User.objects.create_user(
        username='hub-registration-id-player-two',
        email='hub-registration-id-player-two@test.com',
        password='pass123',
    )

    game = Game.objects.create(
        name='Hub Registration Id Game',
        slug='hub-registration-id-game',
        is_active=True,
    )

    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Hub Registration Id Tournament',
        slug='hub-registration-id-tournament',
        organizer=organizer,
        game=game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now - timedelta(hours=4),
        tournament_end=now + timedelta(days=2),
        status=Tournament.LIVE,
    )

    registration = Registration.objects.create(
        tournament=tournament,
        user=player_one,
        status=Registration.CONFIRMED,
        registration_data={},
    )

    Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=registration.id,
        participant1_name='Registered Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        state=Match.COMPLETED,
        winner_id=registration.id,
        loser_id=player_two.id,
        completed_at=now - timedelta(minutes=3),
    )

    payload = _resolve_hub_command_center(
        tournament,
        registration,
        player_one,
        now=now,
    )

    assert payload['show'] is True
    assert payload['outcome_state'] == 'advanced'
