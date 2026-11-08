"""Match reminder sweep: idempotence, concurrency, claim ownership, failure/retry, fairness."""
import threading
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
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
OK = {'created': 1, 'skipped': 0, 'email_sent': 1, 'email_failed': 0}


@pytest.fixture
def setup(db):
    cache.clear()  # the sweep keeps a fairness cursor in the cache
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


def _sig(match, key='m60'):
    return match_ready._marker_signature(key, match.scheduled_time)


def test_fires_once_under_repeated_sweeps_and_keeps_recipients(setup):
    user, _, match, now = setup
    with patch(FIRE, return_value=OK) as fire:
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


def test_failed_dispatch_is_not_marked_and_retries_after_backoff(setup):
    _, _, match, now = setup
    with patch(FIRE, side_effect=RuntimeError('smtp down')):
        result = _sweep(now)
    assert result['failed'] == 1 and result['notified'] == 0
    match.refresh_from_db()
    assert not match.lobby_info.get(REMINDER_MARKERS_KEY)
    claim = match.lobby_info[REMINDER_CLAIMS_KEY]['m60']
    assert claim['attempts'] == 1 and claim['state'] == 'failed' and 'smtp down' in claim['error']

    with patch(FIRE, return_value=OK) as fire:
        assert _sweep(now + timedelta(seconds=5))['in_progress'] == 1  # still backing off
        assert fire.call_count == 0
        retry = _sweep(now + timedelta(seconds=match_ready.FAILURE_RETRY_SECONDS + 1))
    assert retry['notified'] == 1 and retry['reclaimed'] == 1 and fire.call_count == 1
    match.refresh_from_db()
    assert 'm60' in match.lobby_info[REMINDER_MARKERS_KEY]
    assert match.lobby_info[REMINDER_CLAIMS_KEY] == {}


def test_abandons_after_max_attempts_and_stays_quiet(setup):
    _, _, match, now = setup
    with patch.object(match_ready, 'FAILURE_RETRY_SECONDS', 10), \
            patch(FIRE, side_effect=RuntimeError('x')) as fire:
        for step in range(match_ready.MAX_ATTEMPTS):
            assert _sweep(now + timedelta(seconds=11 * step))['failed'] == 1
        later = now + timedelta(seconds=11 * match_ready.MAX_ATTEMPTS)
        assert _sweep(later)['gave_up'] == 1
        assert _sweep(later + timedelta(seconds=30))['abandoned'] == 1
    assert fire.call_count == match_ready.MAX_ATTEMPTS
    match.refresh_from_db()
    assert match.lobby_info[REMINDER_CLAIMS_KEY]['m60']['state'] == 'abandoned'


def test_active_lease_blocks_retry_and_expired_lease_is_reclaimed(setup):
    _, _, match, now = setup
    token, _ = match_ready._claim_reminder(match.id, 'm60', _sig(match), now)
    assert token
    soon = now + timedelta(seconds=match_ready.CLAIM_TTL_SECONDS - 1)
    assert match_ready._claim_reminder(match.id, 'm60', _sig(match), soon) == (None, 'in_progress')
    later = now + timedelta(seconds=match_ready.CLAIM_TTL_SECONDS + 1)
    new_token, reason = match_ready._claim_reminder(match.id, 'm60', _sig(match), later)
    assert new_token and new_token != token and reason == 'reclaimed'


def test_malformed_persisted_claim_data_is_handled(setup):
    _, _, match, now = setup
    for bad in ('garbage', 7, {'sig': _sig(match), 'at': 'not-a-date', 'attempts': 'x'}, None):
        Match.objects.filter(pk=match.pk).update(
            lobby_info={REMINDER_CLAIMS_KEY: {'m60': bad}, REMINDER_MARKERS_KEY: 'also bad'}
        )
        token, _ = match_ready._claim_reminder(match.id, 'm60', _sig(match), now)
        assert token, bad
    Match.objects.filter(pk=match.pk).update(lobby_info=['not', 'a', 'dict'])
    assert match_ready._claim_reminder(match.id, 'm60', _sig(match), now)[0]


def test_stale_worker_cannot_finalize_over_a_newer_claim(setup):
    _, _, match, now = setup
    old, _ = match_ready._claim_reminder(match.id, 'm60', _sig(match), now)
    later = now + timedelta(seconds=match_ready.CLAIM_TTL_SECONDS + 1)
    new, _ = match_ready._claim_reminder(match.id, 'm60', _sig(match), later)

    assert match_ready._finalize_reminder(match.id, 'm60', _sig(match), old) == 'stale'
    match.refresh_from_db()
    assert not match.lobby_info[REMINDER_MARKERS_KEY]
    assert match.lobby_info[REMINDER_CLAIMS_KEY]['m60']['token'] == new  # newer claim untouched

    assert match_ready._finalize_reminder(match.id, 'm60', _sig(match), new) == 'sent'


def test_rescheduling_during_dispatch_rejects_completion_and_resends_for_new_time(setup):
    _, _, match, now = setup

    def reschedule_midflight(*args, **kwargs):
        Match.objects.filter(pk=match.pk).update(scheduled_time=now + timedelta(minutes=62))
        return OK

    with patch(FIRE, side_effect=reschedule_midflight) as fire:
        first = _sweep(now)
        assert first['stale_completions'] == 1 and first['notified'] == 0
        match.refresh_from_db()
        assert not match.lobby_info[REMINDER_MARKERS_KEY]  # old schedule did not leak a marker
        second = _sweep(now)  # new schedule gets its own reminder
    assert second['notified'] == 1 and fire.call_count == 2
    match.refresh_from_db()
    assert match.lobby_info[REMINDER_MARKERS_KEY]['m60'] == _sig(match)


@pytest.mark.parametrize('state', ['cancelled', 'completed', 'live'])
def test_inactive_matches_are_skipped(setup, state):
    _, _, match, now = setup
    Match.objects.filter(pk=match.pk).update(state=state)
    with patch(FIRE, return_value=OK) as fire:
        assert _sweep(now)['notified'] == 0
    assert fire.call_count == 0


def test_claim_and_finalize_recheck_state_and_schedule_under_lock(setup):
    _, _, match, now = setup
    signature = _sig(match)
    Match.objects.filter(pk=match.pk).update(state='cancelled')
    assert match_ready._claim_reminder(match.id, 'm60', signature, now) == (None, 'stale')
    Match.objects.filter(pk=match.pk).update(state=Match.SCHEDULED, scheduled_time=now + timedelta(minutes=70))
    assert match_ready._claim_reminder(match.id, 'm60', signature, now) == (None, 'stale')

    Match.objects.filter(pk=match.pk).update(scheduled_time=now + timedelta(minutes=64))
    token, _ = match_ready._claim_reminder(match.id, 'm60', signature, now)
    Match.objects.filter(pk=match.pk).update(state='cancelled')  # cancelled mid-send
    assert match_ready._finalize_reminder(match.id, 'm60', signature, token) == 'stale'


def test_marker_write_preserves_concurrent_lobby_changes(setup):
    _, _, match, now = setup

    def organizer_sets_code(*args, **kwargs):  # lands while the reminder is being sent
        Match.objects.filter(pk=match.pk).update(
            lobby_info={**Match.objects.get(pk=match.pk).lobby_info, 'room_code': 'ABC123'}
        )
        return OK

    with patch(FIRE, side_effect=organizer_sets_code):
        _sweep(now)
    match.refresh_from_db()
    assert match.lobby_info['room_code'] == 'ABC123'
    assert 'm60' in match.lobby_info[REMINDER_MARKERS_KEY]


def test_handled_matches_cannot_starve_later_pending_ones(setup):
    _, tournament, first, now = setup
    handled = [first]
    for n in range(2, 6):
        handled.append(Match.objects.create(
            tournament=tournament, round_number=1, match_number=n,
            participant1_id=1, participant2_id=2, state=Match.SCHEDULED,
            scheduled_time=now + timedelta(minutes=60, seconds=n),
        ))
    for m in handled:
        Match.objects.filter(pk=m.pk).update(
            lobby_info={REMINDER_MARKERS_KEY: {'m60': match_ready._marker_signature('m60', m.scheduled_time)}}
        )
    pending = Match.objects.create(
        tournament=tournament, round_number=2, match_number=1,
        participant1_id=1, participant2_id=2, state=Match.SCHEDULED,
        scheduled_time=now + timedelta(minutes=64),
    )
    with patch.object(match_ready, 'SWEEP_PAGE_SIZE', 2), patch.object(match_ready, 'SWEEP_ACTION_LIMIT', 1), \
            patch(FIRE, return_value=OK) as fire:
        result = _sweep(now)
    assert fire.call_count == 1 and result['scanned'] == 6 and result['notified'] == 1
    pending.refresh_from_db()
    assert 'm60' in pending.lobby_info[REMINDER_MARKERS_KEY]


def test_limits_report_truncation_honestly(setup):
    _, tournament, _, now = setup
    for n in (2, 3):
        Match.objects.create(
            tournament=tournament, round_number=1, match_number=n,
            participant1_id=1, participant2_id=2, state=Match.SCHEDULED,
            scheduled_time=now + timedelta(minutes=64),
        )
    with patch.object(match_ready, 'SWEEP_ACTION_LIMIT', 2), patch(FIRE, return_value=OK) as fire:
        result = _sweep(now)
    assert result['truncated'] is True and result['attempted'] == 2 and fire.call_count == 2
    with patch(FIRE, return_value=OK) as fire:  # next sweep picks up the remainder
        assert _sweep(now)['notified'] == 1


def test_delivery_outcomes_are_reported_honestly(setup):
    _, _, match, now = setup
    with patch(FIRE, return_value=None):  # disabled by organizer / no rule
        result = _sweep(now)
    assert result['suppressed'] == 1 and result['notified'] == 0
    Match.objects.filter(pk=match.pk).update(lobby_info={})
    with patch(FIRE, return_value={**OK, 'email_failed': 2}):
        result = _sweep(now)
    assert result['notified'] == 1 and result['email_failed'] == 2  # persisted; email failure visible


def test_strict_mode_surfaces_failures_and_delivery_summary(setup):
    user, tournament, _, _ = setup
    context = {'target_user_ids': [user.id], 'match_id': 1, 'dedupe': False}
    with patch('apps.notifications.services.emit', side_effect=RuntimeError('boom')):
        assert TOCNotificationsService.fire_auto_event(tournament, 'match_reminder_1h', dict(context)) is None
        with pytest.raises(RuntimeError):
            TOCNotificationsService.fire_auto_event(tournament, 'match_reminder_1h', {**context, 'strict': True})

    summary = MagicMock(created=1, skipped=0, email_sent=0, email_failed=1)
    with patch('apps.notifications.services.emit', return_value=summary):
        delivery = TOCNotificationsService.fire_auto_event(
            tournament, 'match_reminder_1h', {**context, 'strict': True}
        )
    assert delivery == {'created': 1, 'skipped': 0, 'email_sent': 0, 'email_failed': 1}


def test_email_backend_rejection_is_not_reported_as_sent():
    from apps.notifications import services

    # The package re-exports a separately loaded services.py; patch that module's globals.
    ns = services.emit.__globals__
    status, plain = ns['_send_templated_email_status'], ns['_send_templated_email']
    with patch.dict(ns, {'render_to_string': MagicMock(return_value='body')}),             patch.object(ns['EmailMultiAlternatives'], 'send') as send:
        send.return_value = 0
        assert status('a@b.test', 's', 'tournament_update', {}) == 'failed'
        assert plain('a@b.test', 's', 'tournament_update', {}) is False
        send.return_value = 1
        assert status('a@b.test', 's', 'tournament_update', {}) == 'sent'
    assert status('', 's', 'tournament_update', {}) == 'skipped'


@pytest.mark.django_db(transaction=True)
def test_concurrent_sweeps_send_once(setup):
    user, _, match, now = setup
    calls = []

    def slow_send(*args, **kwargs):
        calls.append(1)
        time.sleep(0.6)  # keep the first sweep mid-send while the second one scans
        return OK

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


def _blocked_matches(tournament, now, count, *, start_second=1, state='abandoned'):
    """Due matches whose 60-minute reminder is persistently claimed (abandoned or in flight)."""
    rows = []
    for n in range(count):
        scheduled = now + timedelta(minutes=60, seconds=start_second + n)
        claim = {
            'sig': match_ready._marker_signature('m60', scheduled), 'token': 'x',
            'at': now.isoformat(), 'attempts': 1, 'state': state,
        }
        rows.append(Match(
            tournament=tournament, round_number=3, match_number=start_second + n,
            participant1_id=1, participant2_id=2, state=Match.SCHEDULED, scheduled_time=scheduled,
            lobby_info={REMINDER_CLAIMS_KEY: {'m60': claim}},
        ))
    Match.objects.bulk_create(rows)


def test_persistently_claimed_due_matches_do_not_consume_the_action_limit(setup):
    _, tournament, pending, now = setup
    # More due-but-blocked matches than SWEEP_ACTION_LIMIT, ordered before the pending one.
    _blocked_matches(tournament, now, match_ready.SWEEP_ACTION_LIMIT // 2 + 1, state='abandoned')
    _blocked_matches(
        tournament, now, match_ready.SWEEP_ACTION_LIMIT // 2 + 1,
        start_second=200, state='sending',
    )
    with patch(FIRE, return_value=OK) as fire:
        result = _sweep(now)
    assert fire.call_count == 1 and result['notified'] == 1  # the pending match is reached
    assert result['attempted'] == 1  # dispatches started, not candidates examined
    assert result['skipped'] >= match_ready.SWEEP_ACTION_LIMIT + 2
    assert result['abandoned'] > 0 and result['in_progress'] > 0
    pending.refresh_from_db()
    assert 'm60' in pending.lobby_info[REMINDER_MARKERS_KEY]


def test_scan_cursor_makes_progress_across_sweeps_behind_persistent_claims(setup):
    _, tournament, pending, now = setup
    _blocked_matches(tournament, now, 12, state='abandoned')  # all sort before the pending match
    results = []
    with patch.object(match_ready, 'SWEEP_SCAN_LIMIT', 5), patch(FIRE, return_value=OK) as fire:
        for _ in range(4):
            results.append(_sweep(now))
            if fire.call_count:
                break
    assert fire.call_count == 1 and 1 <= len(results) <= 3  # reached within a bounded number of sweeps
    assert results[0]['truncated'] is True and results[0]['scanned'] == 5
    pending.refresh_from_db()
    assert 'm60' in pending.lobby_info[REMINDER_MARKERS_KEY]
