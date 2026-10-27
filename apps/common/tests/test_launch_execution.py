"""Focused release regressions. No production database or provider access."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path
from contextlib import ExitStack

from django.test import SimpleTestCase, override_settings


class GovernedReferenceTests(SimpleTestCase):
    @override_settings(OWNLOBBY_MEDIA_MODE='hybrid')
    def test_local_file_cannot_replace_authorized_url(self):
        from apps.common.media_urls import normalize_media_url
        with tempfile.TemporaryDirectory() as root:
            Path(root, 'proof.png').write_bytes(b'private')
            with override_settings(MEDIA_ROOT=root):
                self.assertEqual(normalize_media_url('/files/app.model/proof/1/', 'proof.png'),
                                 '/files/app.model/proof/1/')

    @override_settings(OWNLOBBY_MEDIA_MODE='hybrid')
    def test_snapshot_avatars_use_current_record_without_mutation(self):
        from apps.common.media.snapshots import lineup_with_current_avatars
        snapshot = [{'user_id': 42, 'avatar': 'https://res.cloudinary.com/old.png'},
                    {'user_id': 43, 'avatar': 'https://res.cloudinary.com/deleted.png'}]
        profile = SimpleNamespace(user_id=42, avatar=SimpleNamespace(url='/files/user_profile.userprofile/avatar/99/'))
        with patch('apps.user_profile.models.UserProfile.objects.filter') as query:
            query.return_value.only.return_value = [profile]
            result = lineup_with_current_avatars(snapshot)
        self.assertEqual(result[0]['avatar'], '/files/user_profile.userprofile/avatar/99/')
        self.assertEqual(result[1]['avatar'], '')
        self.assertEqual(snapshot[0]['avatar'], 'https://res.cloudinary.com/old.png')

    @override_settings(OWNLOBBY_MEDIA_MODE='legacy')
    def test_legacy_snapshot_unchanged(self):
        from apps.common.media.snapshots import lineup_with_current_avatars
        snapshot = [{'avatar': 'old.png'}]
        self.assertIs(lineup_with_current_avatars(snapshot), snapshot)


class TaskExecutionTests(SimpleTestCase):
    def test_authenticated_cron_probe_failure_returns_500(self):
        from django.test import RequestFactory
        from deltacrown import lifecycle_cron as cron
        runners = ('auto_advance', 'wrapup', 'no_show', 'lobby_close', 'payment_expiry',
                   'group_playoff_reconcile', 'auto_confirm_submissions', 'dispute_escalation')
        with ExitStack() as stack:
            stack.enter_context(patch.object(cron, '_CRON_SECRET', 'synthetic'))
            stack.enter_context(patch.object(cron.cache, 'add', return_value=True))
            stack.enter_context(patch.object(cron.cache, 'delete'))
            for runner in runners:
                stack.enter_context(patch.object(cron, '_run_' + runner, return_value={'ok': True}))
            probe = stack.enter_context(patch.object(cron, '_run_worker_probe', return_value={'ok': False}))
            response = cron.lifecycle_cron(RequestFactory().post(
                '/api/lifecycle/cron/?worker_probe=1', HTTP_AUTHORIZATION='Bearer synthetic'))
            self.assertEqual(response.status_code, 500)
            probe.assert_called_once()

    def test_unauthorized_cron_cannot_publish_probe(self):
        from django.test import RequestFactory
        from deltacrown import lifecycle_cron as cron
        with patch.object(cron, '_CRON_SECRET', 'synthetic'), patch.object(cron, '_run_worker_probe') as probe:
            response = cron.lifecycle_cron(RequestFactory().post('/api/lifecycle/cron/?worker_probe=1'))
            self.assertEqual(response.status_code, 401)
            probe.assert_not_called()

    def test_cron_probe_rejects_eager(self):
        from deltacrown.lifecycle_cron import _run_worker_probe
        with patch('deltacrown.celery.worker_probe') as probe:
            probe.app.conf.task_always_eager = True
            self.assertFalse(_run_worker_probe()['ok'])
            probe.delay.assert_not_called()

    def test_cron_probe_requires_matching_worker_result(self):
        from deltacrown.lifecycle_cron import _run_worker_probe
        with patch('deltacrown.celery.worker_probe') as probe:
            probe.app.conf.task_always_eager = False
            result = probe.delay.return_value
            result.id = 'synthetic-task'
            result.get.side_effect = lambda **kwargs: probe.delay.call_args.args[0]
            self.assertTrue(_run_worker_probe()['ok'])
            result.get.assert_called_once_with(timeout=10)

    def test_cron_probe_failure_is_visible(self):
        from deltacrown.lifecycle_cron import _run_worker_probe
        with patch('deltacrown.celery.worker_probe') as probe:
            probe.app.conf.task_always_eager = False
            probe.delay.return_value.get.side_effect = TimeoutError()
            self.assertFalse(_run_worker_probe()['ok'])

    def test_nested_tasks_are_registered_in_worker(self):
        from deltacrown.celery import app
        app.loader.import_default_modules()
        for name in (
            'notifications.send_email_notification',
            'notifications.send_discord_notification',
            'apps.tournament_ops.tasks.match_polling.advance_bracket_after_match',
            'apps.tournaments.tasks.run_ocr_and_compare',
            'games.verify_game_passport',
            'ownlobby.worker_probe',
        ):
            self.assertIn(name, app.tasks)

    def test_bracket_task_calls_existing_canonical_service(self):
        from apps.tournament_ops.tasks.match_polling import advance_bracket_after_match
        from apps.tournaments.models.match import Match
        match = SimpleNamespace(pk=42, state=Match.COMPLETED)
        with patch.object(Match.objects, 'get', return_value=match), patch(
            'apps.tournaments.services.bracket_service.BracketService.update_bracket_after_match'
        ) as advance:
            self.assertEqual(advance_bracket_after_match.run(42)['status'], 'ok')
            advance.assert_called_once_with(match)

    def test_bracket_failure_is_retried_not_reported_as_deferred(self):
        from apps.tournament_ops.tasks.match_polling import advance_bracket_after_match
        from apps.tournaments.models.match import Match
        from celery.exceptions import Retry
        with patch.object(Match.objects, 'get', return_value=SimpleNamespace(state=Match.COMPLETED)), patch(
            'apps.tournaments.services.bracket_service.BracketService.update_bracket_after_match',
            side_effect=ImportError('synthetic'),
        ), patch.object(advance_bracket_after_match, 'retry', side_effect=Retry()) as retry:
            with self.assertRaises(Retry):
                advance_bracket_after_match.run(42)
            retry.assert_called_once()

    def test_notification_publish_waits_for_commit(self):
        from apps.notifications.services import services_module
        task = Mock()
        with patch.object(services_module.transaction, 'on_commit') as on_commit:
            services_module._queue_after_commit(task, [42])
            task.apply_async.assert_not_called()
            on_commit.call_args.args[0]()
            task.apply_async.assert_called_once_with(args=[42], ignore_result=True, retry=False)

    def test_real_memory_broker_consumption_without_eager(self):
        # A running worker, not .apply() or eager execution. Windows uses solo
        # for this isolated transport test; Render's prefork must be live-tested.
        from celery import Celery
        from celery.contrib.testing.worker import start_worker
        app = Celery('launch_test', broker='memory://', backend='cache+memory://')
        app.conf.update(task_always_eager=False, task_serializer='json', accept_content=['json'])

        @app.task
        def probe(token):
            return token

        with start_worker(app, pool='solo', concurrency=1, perform_ping_check=False):
            result = probe.delay('synthetic-launch-canary')
            self.assertEqual(result.get(timeout=10), 'synthetic-launch-canary')

    def test_real_memory_worker_retry_completion(self):
        from celery import Celery
        from celery.contrib.testing.worker import start_worker
        app = Celery('retry_test', broker='memory://', backend='cache+memory://')
        app.conf.update(task_always_eager=False, task_serializer='json', accept_content=['json'])

        @app.task(bind=True, max_retries=1)
        def retry_probe(task):
            if task.request.retries == 0:
                raise task.retry(countdown=0)
            return task.request.retries

        with start_worker(app, pool='solo', concurrency=1, perform_ping_check=False):
            self.assertEqual(retry_probe.delay().get(timeout=10), 1)

    @override_settings(DISCORD_NOTIFICATIONS_ENABLED=True, DISCORD_WEBHOOK_URL='https://example.invalid/webhook')
    def test_discord_transport_failure_retries(self):
        from apps.notifications.tasks import send_discord_notification
        from celery.exceptions import Retry
        from requests.exceptions import ConnectionError
        with patch('apps.notifications.tasks.requests.post', side_effect=ConnectionError('synthetic')), patch.object(
            send_discord_notification, 'retry', side_effect=Retry()
        ) as retry:
            with self.assertRaises(Retry):
                send_discord_notification.run({'title': 'Synthetic'})
            retry.assert_called_once()

    def test_email_transport_failure_retries(self):
        from apps.notifications.tasks import send_email_notification
        from apps.notifications.models import Notification
        from celery.exceptions import Retry
        notification = SimpleNamespace(recipient=SimpleNamespace(email='synthetic@example.invalid'),
                                       type='generic', title='Synthetic')
        with patch.object(Notification.objects, 'select_related') as query, patch(
            'apps.notifications.enforcement.can_deliver_notification', return_value=True
        ), patch('apps.notifications.tasks.render_to_string', return_value='Synthetic'), patch(
            'apps.notifications.tasks.send_mail', side_effect=OSError('synthetic')
        ), patch.object(send_email_notification, 'retry', side_effect=Retry()) as retry:
            query.return_value.get.return_value = notification
            with self.assertRaises(Retry):
                send_email_notification.run(42)
            retry.assert_called_once()
