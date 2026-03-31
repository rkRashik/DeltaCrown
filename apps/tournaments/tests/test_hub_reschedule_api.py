import json
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.tournaments.models import Game, Match, Registration, Tournament
from apps.tournaments.models.match_operations import RescheduleRequest


User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def hub_game(db):
    return Game.objects.create(
        name='Hub Reschedule Game',
        slug='hub-reschedule-game',
        is_active=True,
    )


@pytest.fixture
def hub_users(db):
    organizer = User.objects.create_user(
        username='hub-reschedule-organizer',
        email='hub-reschedule-organizer@test.com',
        password='pass123',
    )
    player_one = User.objects.create_user(
        username='hub-reschedule-player-one',
        email='hub-reschedule-player-one@test.com',
        password='pass123',
    )
    player_two = User.objects.create_user(
        username='hub-reschedule-player-two',
        email='hub-reschedule-player-two@test.com',
        password='pass123',
    )
    return organizer, player_one, player_two


@pytest.fixture
def hub_tournament(db, hub_game, hub_users):
    organizer, _, _ = hub_users
    now = timezone.now()
    return Tournament.objects.create(
        name='Hub Reschedule Tournament',
        slug='hub-reschedule-tournament',
        organizer=organizer,
        game=hub_game,
        format=Tournament.SINGLE_ELIM,
        participation_type=Tournament.SOLO,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=1),
        tournament_start=now + timedelta(days=2),
        tournament_end=now + timedelta(days=3),
        status=Tournament.LIVE,
    )


@pytest.fixture
def hub_registrations(db, hub_tournament, hub_users):
    _, player_one, player_two = hub_users
    reg_one = Registration.objects.create(
        tournament=hub_tournament,
        user=player_one,
        status=Registration.CONFIRMED,
        registration_data={},
    )
    reg_two = Registration.objects.create(
        tournament=hub_tournament,
        user=player_two,
        status=Registration.CONFIRMED,
        registration_data={},
    )
    return reg_one, reg_two


def test_hub_matches_infers_winner_from_scores_when_winner_id_missing_for_forfeit(
    client,
    hub_tournament,
    hub_users,
    hub_registrations,
):
    _, player_one, player_two = hub_users
    Match.objects.create(
        tournament=hub_tournament,
        round_number=1,
        match_number=1,
        participant1_id=player_one.id,
        participant1_name='Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        participant1_score=0,
        participant2_score=4,
        winner_id=None,
        state=Match.FORFEIT,
        scheduled_time=timezone.now() - timedelta(hours=1),
    )

    client.force_login(player_one)
    url = reverse('tournaments:hub_matches_api', kwargs={'slug': hub_tournament.slug})
    response = client.get(url)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload['match_history']) == 1
    match_payload = payload['match_history'][0]

    assert match_payload['your_score'] == 0
    assert match_payload['opponent_score'] == 4
    assert match_payload['is_winner'] is False


def test_reschedule_propose_and_accept_flow_sets_pending_visibility_and_updates_schedule(
    client,
    hub_tournament,
    hub_users,
    hub_registrations,
):
    _, player_one, player_two = hub_users

    hub_tournament.config = {
        'participant_rescheduling': {
            'allow_participant_rescheduling': True,
            'deadline_minutes_before': 120,
        }
    }
    hub_tournament.save(update_fields=['config'])

    scheduled_time = timezone.now() + timedelta(days=2)
    match = Match.objects.create(
        tournament=hub_tournament,
        round_number=1,
        match_number=7,
        participant1_id=player_one.id,
        participant1_name='Player One',
        participant2_id=player_two.id,
        participant2_name='Player Two',
        state=Match.SCHEDULED,
        scheduled_time=scheduled_time,
    )

    proposal_url = reverse(
        'tournaments:hub_match_reschedule_propose_api',
        kwargs={'slug': hub_tournament.slug, 'match_id': match.id},
    )

    new_time = timezone.now() + timedelta(days=2, hours=3)
    client.force_login(player_one)
    proposal_response = client.post(
        proposal_url,
        data=json.dumps({
            'new_time': new_time.isoformat(),
            'reason': 'Need to move due to roster availability.',
        }),
        content_type='application/json',
    )

    assert proposal_response.status_code == 200
    proposal_payload = proposal_response.json()
    assert proposal_payload['success'] is True
    assert proposal_payload['request']['status'] == RescheduleRequest.PENDING
    request_id = proposal_payload['request']['id']

    matches_url = reverse('tournaments:hub_matches_api', kwargs={'slug': hub_tournament.slug})
    client.force_login(player_two)
    matches_response = client.get(matches_url)
    assert matches_response.status_code == 200

    match_payload = matches_response.json()['active_matches'][0]
    assert match_payload['reschedule']['can_respond'] is True
    assert match_payload['reschedule']['pending_request']['id'] == request_id

    respond_url = reverse(
        'tournaments:hub_match_reschedule_respond_api',
        kwargs={'slug': hub_tournament.slug, 'match_id': match.id},
    )
    respond_response = client.post(
        respond_url,
        data=json.dumps({
            'action': 'accept',
            'request_id': request_id,
            'response_note': 'Approved, we can play then.',
        }),
        content_type='application/json',
    )

    assert respond_response.status_code == 200
    respond_payload = respond_response.json()
    assert respond_payload['success'] is True
    assert respond_payload['action'] == 'accept'

    match.refresh_from_db()
    assert match.scheduled_time.isoformat() == respond_payload['scheduled_at']

    request_obj = RescheduleRequest.objects.get(id=request_id)
    assert request_obj.status == RescheduleRequest.APPROVED
