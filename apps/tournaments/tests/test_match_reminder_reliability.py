"""Match reminder sweep: idempotence, concurrency, failure/retry, stale matches."""
import threading
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.utils import timezone

from apps.games.models.game import Game
from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
from apps.tournaments.models import Match, Tournament
from apps.tournaments.tasks import match_ready
from apps.tournaments.tasks.match_ready import (
    REMINDER_CLAIMS_KEY,
    REMINDER_MARKERS_KEY,
    run_match_ready_reminder_sweep,
)

pytestmark = pytest.mark.django_db

FIRE = 'apps.tournaments.api.toc.notifications_service.TOCNotificationsService.fire_auto_event'
TARGETS = 'apps.tournaments.api.toc.brackets_service.TOCBracketsService._match_participant_user_ids'


@pytest.fixture
def setup(db):
    user = get_user_model().objects.create_user(username='rem-user', email='rem-user@test.com')
    game = Game.objects.create(
        name='Reminder Game', slug='reminder-game', default_team_size=1,
        profile_id_field='ingame_id', default_result_type='map_score', is_active=True,
    )
    now = timezone.now().replace(microsecond=0)
    tournament = Tournament.objects.create(
        name='Reminder Cup', slug='reminder-cup', organizer=user, game=game,
        format=Tournament.SINGLE_ELIM, participation_type=Tournament.SOLO,
        max_participants=4, min_participants=2,
        registration_start=now - timedelta(days=2), registration_end=now - timedelta(days=1),
        tournament_start=now, tournament_end=now + timedelta(days=1),
        status=Tournament.LIVE,
    )
    match = Match.objects.create(
        tournament=tournament, round_number=1, match_number=1,
        participant1_id=1, participant2_id=2, state=Match.SCHEDULED,
        scheduled_time=now + timedelta(minutes=64),  # inside the 60-minute window
    )
    return user, tournament, match, now


def _sweep(now):
    with patch(TARGETS, return_value=[1]):
        return run_match_ready_reminder_sweep(now=now)


def test_fires_once_under_repeated_sweeps_and_keeps_recipients(setup):
    user, _, match, now = setup
    with patch(FIRE) as fire:
        with patch(TARGETS, return_value=[user.id]):
            first = run_match_ready_reminder_sweep(now=now)
            second = run_match_ready_reminder_sweep(now=now)
    assert first['notified'] == 1 and second['notified'] == 0
    assert fire.call_count == 1
    context = fire.call_args.args[2]
    assert context['target_user_ids'] == [user.id] and context['strict'] is True
    match.refresh_from_db()
    assert list(match.lobby_info[REMINDER_MARKERS_KEY]) == ['m60']
    assert match.lobby_info[REMINDER_CLAIMS_KEY] == {}


def test_failed_dispatch_is_not_marked_and_retries_after_ttl(setup):
    _, _, match, now = setup
    with patch(FIRE, side_effect=RuntimeError('smtp down')):
        result = _sweep(now)
    assert result['failed'] == 1 and result['notified'] == 0
    match.refresh_from_db()
    assert REMINDER_MARKERS_KEY not in match.lobby_info or not match.lobby_info[REMINDER_MARKERS_KEY]
    assert match.lobby_info[REMINDER_CLAIMS_KEY]['m60']['attempts'] == 1

    with patch(FIRE) as fire:
        assert _sweep(now + timedelta(seconds=5))['in_progress'] == 1  # still claimed
        assert fire.call_count == 0
        retry = _sweep(now + timedelta(seconds=match_ready.CLAIM_TTL_SECONDS + 1))
    assert retry['notified'] == 1 and fire.call_count == 1
    match.refresh_from_db()
    assert 'm60' in match.lobby_info[REMINDER_MARKERS_KEY]
    assert match.lobby_info[REMINDER_CLAIMS_KEY] == {}


def test_gives_up_after_max_attempts(setup):
    _, _, _, now = setup
    with patch.object(match_ready, 'CLAIM_TTL_SECONDS', 10), patch(FIRE, side_effect=RuntimeError('x')) as fire:
        for step in range(match_ready.MAX_ATTEMPTS):
            assert _sweep(now + timedelta(seconds=11 * step))['failed'] == 1
        final = _sweep(now + timedelta(seconds=11 * match_ready.MAX_ATTEMPTS))
    assert final['gave_up'] == 1 and final['failed'] == 0
    assert fire.call_count == match_ready.MAX_ATTEMPTS


def test_reschedule_makes_a_new_reminder_eligible(setup):
    _, _, match, now = setup
    with patch(FIRE) as fire:
        _sweep(now)
        Match.objects.filter(pk=match.pk).update(scheduled_time=now + timedelta(minutes=62))
        assert _sweep(now)['notified'] == 1
    assert fire.call_count == 2


@pytest.mark.parametrize('state', ['cancelled', 'completed', 'live'])
def test_inactive_matches_are_skipped(setup, state):
    _, _, match, now = setup
    Match.objects.filter(pk=match.pk).update(state=state)
    with patch(FIRE) as fire:
        assert _sweep(now)['notified'] == 0
    assert fire.call_count == 0


def test_claim_rechecks_state_and_schedule_under_lock(setup):
    _, _, match, now = setup
    signature = match_ready._marker_signature('m60', match.scheduled_time)
    Match.objects.filter(pk=match.pk).update(state='cancelled')
    assert match_ready._claim_reminder(match.id, 'm60', signature, now) == (False, 'stale')
    Match.objects.filter(pk=match.pk).update(state=Match.SCHEDULED, scheduled_time=now + timedelta(minutes=70))
    assert match_ready._claim_reminder(match.id, 'm60', signature, now) == (False, 'stale')


def test_marker_write_preserves_concurrent_lobby_changes(setup):
    _, _, match, now = setup

    def organizer_sets_code(*args, **kwargs):  # lands while the reminder is being sent
        Match.objects.filter(pk=match.pk).update(
            lobby_info={**Match.objects.get(pk=match.pk).lobby_info, 'room_code': 'ABC123'}
        )

    with patch(FIRE, side_effect=organizer_sets_code):
        _sweep(now)
    match.refresh_from_db()
    assert match.lobby_info['room_code'] == 'ABC123'
    assert 'm60' in match.lobby_info[REMINDER_MARKERS_KEY]


def test_sweep_is_bounded(setup):
    _, tournament, _, now = setup
    for n in (2, 3):
        Match.objects.create(
            tournament=tournament, round_number=1, match_number=n,
            participant1_id=1, participant2_id=2, state=Match.SCHEDULED,
            scheduled_time=now + timedelta(minutes=64),
        )
    with patch.object(match_ready, 'SWEEP_MATCH_LIMIT', 2), patch(FIRE) as fire:
        result = _sweep(now)
    assert result['truncated'] is True and result['scanned'] == 2 and fire.call_count == 2


def test_strict_mode_surfaces_dispatch_failure_default_stays_silent(setup):
    user, tournament, _, _ = setup
    context = {'target_user_ids': [user.id], 'match_id': 1, 'dedupe': False}
    with patch('apps.notifications.services.emit', side_effect=RuntimeError('boom')):
        TOCNotificationsService.fire_auto_event(tournament, 'match_reminder_1h', dict(context))
        with pytest.raises(RuntimeError):
            TOCNotificationsService.fire_auto_event(
                tournament, 'match_reminder_1h', {**context, 'strict': True}
            )


@pytest.mark.django_db(transaction=True)
def test_concurrent_sweeps_send_once(setup):
    user, _, match, now = setup
    calls = []

    def slow_send(*args, **kwargs):
        calls.append(1)
        time.sleep(0.6)  # keep the first sweep mid-send while the second one scans

    def run():
        try:
            with patch(TARGETS, return_value=[user.id]):
                run_match_ready_reminder_sweep(now=now)
        finally:
            connection.close()

    with patch(FIRE, side_effect=slow_send):
        threads = [threading.Thread(target=run) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    assert len(calls) == 1
