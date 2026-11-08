"""Result dispute journey over the REST result/match APIs (solo, single elimination, free entry).

Synthetic users on a disposable database. Registrations are created directly as CONFIRMED
(fixture shortcut) and the tournament is put LIVE directly; bracket generation, result
submission, disputes and resolution then run through the real services/endpoints.
"""
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.games.models.game import Game
from apps.tournaments.api.toc.brackets_service import TOCBracketsService
from apps.tournaments.models import Match, Registration, Tournament
from apps.tournaments.models.dispute import DisputeRecord
from apps.tournaments.models.result_submission import MatchResultSubmission
from apps.tournaments.services.match_service import MatchService

pytestmark = pytest.mark.django_db
User = get_user_model()
SCORE_NOTE = 'The submitted score is wrong: I won this match 2-1 and have a screenshot.'


def _client(user=None):
    client = APIClient()
    if user is not None:
        client.force_authenticate(user=user)
    return client


def _post(user, path, payload=None):
    return _client(user).post(path, payload or {}, format='json', secure=True)


@pytest.fixture
def world(db):
    organizer = User.objects.create_user(username='dp-organizer', email='dp-organizer@example.test')
    staff = User.objects.create_superuser(username='dp-staff', email='dp-staff@example.test', password=None)  # is_staff is synced from groups/superuser
    players = [User.objects.create_user(username=f'dp-p{n}', email=f'dp-p{n}@example.test') for n in range(1, 5)]
    outsider = User.objects.create_user(username='dp-outsider', email='dp-outsider@example.test')
    game = Game.objects.create(
        name='eFootball', slug='efootball', default_team_size=1,
        profile_id_field='ingame_id', default_result_type='map_score', is_active=True,
    )
    now = timezone.now()
    tournament = Tournament.objects.create(
        name='Dispute Cup', slug='dispute-cup', organizer=organizer, game=game,
        format=Tournament.SINGLE_ELIM, participation_type=Tournament.SOLO,
        max_participants=4, min_participants=2,
        registration_start=now - timedelta(days=2), registration_end=now - timedelta(days=1),
        tournament_start=now - timedelta(hours=1), tournament_end=now + timedelta(days=1),
        status=Tournament.LIVE,
    )
    for player in players:  # fixture shortcut: confirmed entrants
        Registration.objects.create(
            tournament=tournament, user=player, status=Registration.CONFIRMED,
            registration_data={'game_id': f'{player.username}-efootball'},
        )
    TOCBracketsService.generate_bracket(tournament, organizer, {})
    match = Match.objects.filter(tournament=tournament, round_number=1).order_by('match_number').first()
    p1 = User.objects.get(pk=match.participant1_id)
    p2 = User.objects.get(pk=match.participant2_id)
    for participant in (p1.id, p2.id):
        MatchService.check_in_participant(Match.objects.get(pk=match.pk), participant)
    MatchService.transition_to_live(Match.objects.get(pk=match.pk))
    return {'organizer': organizer, 'staff': staff, 'outsider': outsider, 'tournament': tournament,
            'match': Match.objects.get(pk=match.pk), 'p1': p1, 'p2': p2}


def test_submit_dispute_and_staff_resolution_via_api(world):
    match, p1, p2 = world['match'], world['p1'], world['p2']
    results = f'/api/tournaments/results/{match.id}'

    submit = _post(p1, f'{results}/submit-result/', {'participant1_score': 2, 'participant2_score': 1})
    assert submit.status_code == 200
    assert Match.objects.get(pk=match.pk).state == Match.PENDING_RESULT

    # Only a participant may dispute: a stranger and an anonymous caller are refused
    assert _post(world['outsider'], f'{results}/report-dispute/',
                 {'reason': 'score_mismatch', 'description': SCORE_NOTE}).status_code in (401, 403)
    assert _post(None, f'{results}/report-dispute/',
                 {'reason': 'score_mismatch', 'description': SCORE_NOTE}).status_code in (401, 403)

    # The opposing participant disputes the submitted result
    dispute = _post(p2, f'{results}/report-dispute/', {'reason': 'score_mismatch', 'description': SCORE_NOTE})
    assert dispute.status_code in (200, 201), dispute.data
    disputed = Match.objects.get(pk=match.pk)
    assert disputed.state == Match.DISPUTED
    record = DisputeRecord.objects.get(submission__match=match)
    assert record.status == DisputeRecord.OPEN and record.opened_by_user_id == p2.id
    # The on-demand submission snapshot is attributed to the submitter and is not 'pending',
    # so auto-confirm sweeps cannot finalize it behind the dispute's back.
    snapshot = MatchResultSubmission.objects.get(match=match)
    assert snapshot.submitted_by_user_id == p1.id and snapshot.status == MatchResultSubmission.STATUS_DISPUTED

    # A second active dispute is refused; confirming a disputed match is refused
    again = _post(p1, f'{results}/report-dispute/', {'reason': 'other', 'description': SCORE_NOTE})
    assert again.status_code >= 400
    assert _post(world['organizer'], f'{results}/confirm-result/').status_code >= 400
    assert DisputeRecord.objects.filter(submission__match=match).count() == 1

    # Nothing advanced while the dispute is open
    assert not Match.objects.filter(tournament=world['tournament'], round_number=2).exists()

    # Resolution is staff-only: a participant, a stranger and the (non-staff) organizer are refused
    resolve = f'/api/tournaments/matches/{match.id}/resolve-dispute/'
    body = {'decision': 'ACCEPT_REPORTED'}
    for user in (p1, p2, world['outsider'], world['organizer']):
        assert _post(user, resolve, body).status_code in (401, 403), user.username
    assert Match.objects.get(pk=match.pk).state == Match.DISPUTED

    # Staff resolve it; the match completes with the reported winner
    done = _post(world['staff'], resolve, body)
    assert done.status_code == 200, getattr(done, 'data', done.content)
    final = Match.objects.get(pk=match.pk)
    assert final.state == Match.COMPLETED and final.winner_id == p1.id
    assert DisputeRecord.objects.get(submission__match=match).status != DisputeRecord.OPEN

    # Replaying the resolution neither changes the outcome nor duplicates side effects
    replay = _post(world['staff'], resolve, body)
    assert replay.status_code in (200, 409)
    assert Match.objects.get(pk=match.pk).winner_id == p1.id
    assert MatchResultSubmission.objects.filter(match=match).count() == 1


def test_override_resolution_advances_the_override_winner(world):
    from apps.brackets.models import BracketNode

    match, p1, p2 = world['match'], world['p1'], world['p2']
    results = f'/api/tournaments/results/{match.id}'
    assert _post(p1, f'{results}/submit-result/', {'participant1_score': 2, 'participant2_score': 1}).status_code == 200
    assert _post(p2, f'{results}/report-dispute/', {'reason': 'wrong_winner', 'description': SCORE_NOTE}).status_code == 201

    resolve = f'/api/tournaments/matches/{match.id}/resolve-dispute/'
    done = _post(world['staff'], resolve, {'decision': 'OVERRIDE', 'final_score_a': 0, 'final_score_b': 3})
    assert done.status_code == 200, getattr(done, 'data', done.content)

    final = Match.objects.get(pk=match.pk)
    assert final.state == Match.COMPLETED and final.winner_id == p2.id  # the overridden winner
    assert DisputeRecord.objects.get(submission__match=match).status == DisputeRecord.RESOLVED_CUSTOM
    parent = BracketNode.objects.get(match=match).parent_node
    parent.refresh_from_db()
    assert p2.id in (parent.participant1_id, parent.participant2_id)  # advanced into round two
    assert p1.id not in (parent.participant1_id, parent.participant2_id)


def _open_dispute(world):
    match, p1, p2 = world['match'], world['p1'], world['p2']
    results = f'/api/tournaments/results/{match.id}'
    assert _post(p1, f'{results}/submit-result/', {'participant1_score': 2, 'participant2_score': 1}).status_code == 200
    assert _post(p2, f'{results}/report-dispute/', {'reason': 'wrong_winner', 'description': SCORE_NOTE}).status_code == 201
    return f'/api/tournaments/matches/{match.id}/resolve-dispute/'


@pytest.mark.parametrize('decision, state', [('REMATCH', Match.SCHEDULED), ('DISQUALIFY', Match.CANCELLED)])
def test_rematch_and_disqualify_close_the_dispute_without_advancing(world, decision, state):
    from apps.brackets.models import BracketNode

    match = world['match']
    resolve = _open_dispute(world)

    done = _post(world['staff'], resolve, {'decision': decision, 'notes': 'staff ruling'})
    assert done.status_code == 200, getattr(done, 'data', done.content)

    final = Match.objects.get(pk=match.pk)
    assert final.state == state
    assert final.winner_id is None and final.loser_id is None and final.completed_at is None
    if decision == 'REMATCH':
        assert (final.participant1_score, final.participant2_score) == (0, 0)
        assert 'result_submitted_by_id' not in final.lobby_info
    record = DisputeRecord.objects.get(submission__match=match)
    assert record.status == DisputeRecord.RESOLVED_CUSTOM
    assert record.resolved_by_user_id == world['staff'].id and record.resolved_at is not None
    assert record.resolution_notes == 'staff ruling'

    # Nothing advanced: no round-two match, no winner marker, parent slots untouched
    assert not Match.objects.filter(tournament=world['tournament'], round_number=2).exists()
    node = BracketNode.objects.get(match=match)
    assert node.winner_id is None
    parent = node.parent_node
    assert world['p1'].id not in (parent.participant1_id, parent.participant2_id)
    assert world['p2'].id not in (parent.participant1_id, parent.participant2_id)

    # Repeating the request is refused and changes nothing
    again = _post(world['staff'], resolve, {'decision': decision})
    assert again.status_code == 409
    assert DisputeRecord.objects.filter(submission__match=match).count() == 1
    assert Match.objects.get(pk=match.pk).state == state


def _complete_other_round_one_match(world):
    other = Match.objects.filter(tournament=world['tournament'], round_number=1).exclude(pk=world['match'].pk).get()
    a, b = other.participant1_id, other.participant2_id
    for pid in (a, b):
        MatchService.check_in_participant(Match.objects.get(pk=other.pk), pid)
    MatchService.transition_to_live(Match.objects.get(pk=other.pk))
    results = f'/api/tournaments/results/{other.id}'
    assert _post(User.objects.get(pk=a), f'{results}/submit-result/', {'participant1_score': 1, 'participant2_score': 0}).status_code == 200
    assert _post(world['organizer'], f'{results}/confirm-result/').status_code == 200


def test_dispute_after_advancement_before_next_match_exists(world):
    """The winner only sits in a bracket slot, so an override re-seats the new winner there."""
    from apps.brackets.models import BracketNode

    match, p1, p2 = world['match'], world['p1'], world['p2']
    results = f'/api/tournaments/results/{match.id}'
    assert _post(p1, f'{results}/submit-result/', {'participant1_score': 2, 'participant2_score': 1}).status_code == 200
    assert _post(world['organizer'], f'{results}/confirm-result/').status_code == 200
    assert _post(p2, f'{results}/report-dispute/', {'reason': 'wrong_winner', 'description': SCORE_NOTE}).status_code == 201
    done = _post(world['staff'], f'/api/tournaments/matches/{match.id}/resolve-dispute/',
                 {'decision': 'OVERRIDE', 'final_score_a': 0, 'final_score_b': 3})
    assert done.status_code == 200
    parent = BracketNode.objects.get(match=match).parent_node
    parent.refresh_from_db()
    slots = (parent.participant1_id, parent.participant2_id)
    assert p2.id in slots and p1.id not in slots


def _advanced_world_with_live_final(world):
    match, p1, p2 = world['match'], world['p1'], world['p2']
    results = f'/api/tournaments/results/{match.id}'
    assert _post(p1, f'{results}/submit-result/', {'participant1_score': 2, 'participant2_score': 1}).status_code == 200
    assert _post(world['organizer'], f'{results}/confirm-result/').status_code == 200
    _complete_other_round_one_match(world)
    nxt = Match.objects.get(tournament=world['tournament'], round_number=2)
    for pid in (nxt.participant1_id, nxt.participant2_id):
        MatchService.check_in_participant(Match.objects.get(pk=nxt.pk), pid)
    MatchService.transition_to_live(Match.objects.get(pk=nxt.pk))
    assert _post(p2, f'{results}/report-dispute/', {'reason': 'wrong_winner', 'description': SCORE_NOTE}).status_code == 201
    return nxt, f'/api/tournaments/matches/{match.id}/resolve-dispute/'


@pytest.mark.parametrize('body', [
    {'decision': 'OVERRIDE', 'final_score_a': 0, 'final_score_b': 3},
    {'decision': 'REMATCH'},
    {'decision': 'DISQUALIFY'},
])
def test_rulings_that_would_corrupt_an_advanced_bracket_are_refused(world, body):
    nxt, resolve = _advanced_world_with_live_final(world)
    before = (nxt.participant1_id, nxt.participant2_id)

    assert _post(world['staff'], resolve, body).status_code == 409

    after = Match.objects.get(pk=nxt.pk)
    assert (after.participant1_id, after.participant2_id) == before and after.state == Match.LIVE
    disputed = Match.objects.get(pk=world['match'].pk)
    assert disputed.state == Match.DISPUTED and disputed.winner_id == world['p1'].id
    assert DisputeRecord.objects.get(submission__match=disputed).status == DisputeRecord.OPEN

    # Confirming the original result is still possible and leaves the bracket untouched
    assert _post(world['staff'], resolve, {'decision': 'ACCEPT_REPORTED'}).status_code == 200
    assert Match.objects.get(pk=nxt.pk).participant1_id in before
