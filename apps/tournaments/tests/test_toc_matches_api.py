from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.tournaments.api.toc.matches_service import TOCMatchesService
from apps.tournaments.models import Game, Match, Tournament
from apps.tournaments.models.result_submission import MatchResultSubmission
from apps.tournaments.services.match_service import MatchService

User = get_user_model()


@pytest.fixture
def game(db):
    return Game.objects.create(
        name='TOC Match Test Game',
        slug='toc-match-test-game',
        is_active=True,
    )


@pytest.fixture
def organizer(db):
    return User.objects.create_user(
        username='toc-match-organizer',
        email='toc-match-organizer@test.com',
        password='pass123',
    )


@pytest.fixture
def opponent(db):
    return User.objects.create_user(
        username='toc-match-opponent',
        email='toc-match-opponent@test.com',
        password='pass123',
    )


@pytest.fixture
def tournament(db, game, organizer):
    now = timezone.now()
    return Tournament.objects.create(
        name='TOC Match Ops',
        slug='toc-match-ops',
        game=game,
        organizer=organizer,
        format=Tournament.SINGLE_ELIMINATION,
        max_participants=16,
        registration_start=now,
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=8),
        tournament_end=now + timedelta(days=9),
    )


@pytest.fixture
def match(db, tournament, organizer, opponent):
    return Match.objects.create(
        tournament=tournament,
        round_number=1,
        match_number=1,
        participant1_id=organizer.id,
        participant1_name='Organizer Team',
        participant2_id=opponent.id,
        participant2_name='Opponent Team',
        state=Match.READY,
    )


@pytest.mark.django_db
def test_submit_score_uses_match_service_override_signature(match, tournament, organizer, monkeypatch):
    captured = {}

    def fake_override(match, score1, score2, reason, overridden_by_username):
        captured['score1'] = score1
        captured['score2'] = score2
        captured['reason'] = reason
        captured['overridden_by_username'] = overridden_by_username
        match.participant1_score = score1
        match.participant2_score = score2
        return match

    monkeypatch.setattr(MatchService, 'organizer_override_score', staticmethod(fake_override))

    payload = TOCMatchesService.submit_score(
        match_id=match.id,
        tournament=tournament,
        p1_score=5,
        p2_score=2,
        user_id=organizer.id,
    )

    assert captured['score1'] == 5
    assert captured['score2'] == 2
    assert captured['overridden_by_username'] == organizer.username
    assert payload['participant1_score'] == 5
    assert payload['participant2_score'] == 2


@pytest.mark.django_db
def test_forfeit_match_maps_forfeiter_to_side(match, tournament, organizer, monkeypatch):
    captured = {}

    def fake_forfeit(match, forfeiting_participant, reason, forfeited_by_username):
        captured['forfeiting_participant'] = forfeiting_participant
        captured['reason'] = reason
        captured['forfeited_by_username'] = forfeited_by_username
        match.state = Match.FORFEIT
        return match

    monkeypatch.setattr(MatchService, 'organizer_forfeit_match', staticmethod(fake_forfeit))

    TOCMatchesService.forfeit_match(
        match_id=match.id,
        tournament=tournament,
        forfeiter_id=match.participant2_id,
        user_id=organizer.id,
    )

    assert captured['forfeiting_participant'] == 2
    assert captured['forfeited_by_username'] == organizer.username


@pytest.mark.django_db
def test_match_verify_view_casts_scores_to_int(match, tournament, organizer, monkeypatch):
    captured = {}

    def fake_verify(cls, **kwargs):
        captured.update(kwargs)
        return {'status': 'confirmed'}

    monkeypatch.setattr(TOCMatchesService, 'verify_match', classmethod(fake_verify))

    client = APIClient()
    client.force_login(organizer)
    url = reverse('toc_api:match-verify', kwargs={'slug': tournament.slug, 'pk': match.id})

    response = client.post(
        url,
        data={
            'action': 'confirm',
            'participant1_score': '10',
            'participant2_score': '2',
            'notes': 'manual verify',
        },
        format='json',
    )

    assert response.status_code == 200
    assert captured['p1_score'] == 10
    assert captured['p2_score'] == 2
    assert isinstance(captured['p1_score'], int)
    assert isinstance(captured['p2_score'], int)


@pytest.mark.django_db
def test_match_verify_view_rejects_invalid_scores(match, tournament, organizer):
    client = APIClient()
    client.force_login(organizer)
    url = reverse('toc_api:match-verify', kwargs={'slug': tournament.slug, 'pk': match.id})

    response = client.post(
        url,
        data={
            'action': 'confirm',
            'participant1_score': 'NaN',
            'participant2_score': '3',
        },
        format='json',
    )

    assert response.status_code == 400
    assert 'must be integers' in str(response.json().get('error', ''))


@pytest.mark.django_db
def test_match_reset_endpoint_calls_service(match, tournament, organizer, monkeypatch):
    called = {}

    def fake_reset(cls, match_id, tournament, user_id):
        called['match_id'] = match_id
        called['user_id'] = user_id
        return {'id': match_id, 'state': Match.READY}

    monkeypatch.setattr(TOCMatchesService, 'reset_match', classmethod(fake_reset))

    client = APIClient()
    client.force_login(organizer)
    url = reverse('toc_api:match-reset', kwargs={'slug': tournament.slug, 'pk': match.id})

    response = client.post(url, data={}, format='json')

    assert response.status_code == 200
    assert called['match_id'] == match.id
    assert called['user_id'] == organizer.id


@pytest.mark.django_db
def test_reset_match_clears_scores_and_submissions(match, tournament, organizer):
    now = timezone.now()
    match.state = Match.COMPLETED
    match.participant1_score = 3
    match.participant2_score = 1
    match.winner_id = match.participant1_id
    match.loser_id = match.participant2_id
    match.started_at = now - timedelta(minutes=7)
    match.completed_at = now
    match.save(
        update_fields=[
            'state',
            'participant1_score',
            'participant2_score',
            'winner_id',
            'loser_id',
            'started_at',
            'completed_at',
        ]
    )

    MatchResultSubmission.objects.create(
        match=match,
        submitted_by_user=organizer,
        submitted_by_team_id=match.participant1_id,
        raw_result_payload={'score_p1': 3, 'score_p2': 1},
        submitter_notes='reset test',
    )

    payload = TOCMatchesService.reset_match(
        match_id=match.id,
        tournament=tournament,
        user_id=organizer.id,
    )

    match.refresh_from_db()
    assert match.state == Match.SCHEDULED
    assert match.participant1_score == 0
    assert match.participant2_score == 0
    assert match.winner_id is None
    assert match.loser_id is None
    assert match.started_at is None
    assert match.completed_at is None
    assert MatchResultSubmission.objects.filter(match=match).count() == 0
    assert payload['state'] == Match.SCHEDULED
