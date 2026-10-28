"""Focused offline regressions for free-hosting stabilization; no DB/network."""

from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit
import importlib
import ssl

from django.test import SimpleTestCase, RequestFactory
from deltacrown.redis_config import verified_redis_url, redis_url_with_db


class RedisTLSChecks(SimpleTestCase):
    def test_cert_and_hostname_required_even_for_explicit_insecure_overrides(self):
        for suffix in (
            "",
            "?ssl_cert_reqs=CERT_NONE&ssl_check_hostname=false",
            "?ssl_cert_reqs=optional",
        ):
            url = verified_redis_url(
                "rediss://synthetic:placeholder@demo.upstash.io:6379/2" + suffix
            )
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(query["ssl_cert_reqs"], ["required"])
            self.assertEqual(query["ssl_check_hostname"], ["true"])
            self.assertEqual(urlsplit(url).password, "placeholder")

    def test_db_rewrite_preserves_tls_ca_and_query(self):
        url = verified_redis_url(
            "rediss://synthetic:placeholder@demo.upstash.io:6379/2?ssl_ca_certs=%2Ftmp%2Fsynthetic-ca.pem"
        )
        updated = redis_url_with_db(url, 3)
        self.assertEqual(urlsplit(updated).path, "/0")
        self.assertEqual(
            parse_qs(urlsplit(updated).query)["ssl_ca_certs"], ["/tmp/synthetic-ca.pem"]
        )
        self.assertEqual(urlsplit(redis_url_with_db("redis://localhost:6379/0?x=1", 3)).path, "/3")

    def test_non_tls_schemes_unchanged_and_normalization_idempotent(self):
        self.assertEqual(verified_redis_url("memory://"), "memory://")
        url = verified_redis_url("rediss://demo.invalid:6379/0")
        self.assertEqual(verified_redis_url(url), url)

    def test_installed_redis_kombu_and_celery_parse_verification_without_network(self):
        import redis
        from kombu import Connection
        from celery import Celery
        from celery.backends.redis import RedisBackend

        url = verified_redis_url("rediss://synthetic:placeholder@demo.invalid:6379/0")
        pool = redis.ConnectionPool.from_url(url)
        self.assertEqual(pool.connection_kwargs["ssl_cert_reqs"], "required")
        self.assertIs(pool.connection_kwargs["ssl_check_hostname"], True)
        conn = redis.SSLConnection(
            **{k: v for k, v in pool.connection_kwargs.items() if k != "connection_class"}
        )
        self.assertEqual(conn.cert_reqs, ssl.CERT_REQUIRED)
        self.assertTrue(conn.check_hostname)
        from redis.asyncio import ConnectionPool as AsyncPool
        async_pool = AsyncPool.from_url(url)
        self.assertEqual(async_pool.connection_kwargs['ssl_cert_reqs'], 'required')
        self.assertIs(async_pool.connection_kwargs['ssl_check_hostname'], True)
        broker = Connection(url)
        self.assertEqual(broker.ssl["ssl_cert_reqs"], ssl.CERT_REQUIRED)
        app = Celery("synthetic_tls_test", set_as_current=False)
        backend = RedisBackend(app=app, url=url)
        self.assertEqual(backend.connparams["ssl_cert_reqs"], ssl.CERT_REQUIRED)
        self.assertIs(backend.connparams["ssl_check_hostname"], True)
        broker.release()
        app.close()

    def test_environment_override_normalization_also_enforces_tls(self):
        import os
        from deltacrown.celery import _normalize_celery_env_url

        with patch.dict(
            os.environ,
            {
                "CELERY_BROKER_URL": "rediss://synthetic:placeholder@demo.invalid/0?ssl_cert_reqs=CERT_NONE"
            },
        ):
            _normalize_celery_env_url("CELERY_BROKER_URL")
            self.assertEqual(
                parse_qs(urlsplit(os.environ["CELERY_BROKER_URL"]).query)["ssl_cert_reqs"],
                ["required"],
            )


class CronChecks(SimpleTestCase):
    runners = (
        "_run_auto_advance",
        "_run_wrapup",
        "_run_no_show",
        "_run_lobby_close",
        "_run_payment_expiry",
        "_run_group_playoff_reconcile",
        "_run_auto_confirm_submissions",
        "_run_dispute_escalation",
    )

    def invoke(self, fail=False):
        from deltacrown import lifecycle_cron as cron

        request = RequestFactory().post(
            "/api/lifecycle/cron/", HTTP_AUTHORIZATION="Bearer synthetic-test-secret"
        )
        with ExitStack() as stack:
            stack.enter_context(patch.object(cron, "_CRON_SECRET", "synthetic-test-secret"))
            stack.enter_context(patch.object(cron.cache, "add", return_value=True))
            release = stack.enter_context(patch.object(cron.cache, "delete"))
            mocks = [
                stack.enter_context(
                    patch.object(cron, name, return_value={"ok": not fail if i == 0 else True})
                )
                for i, name in enumerate(self.runners)
            ]
            response = cron.lifecycle_cron(request)
            for mock in mocks:
                mock.assert_called_once()
            release.assert_called_once()
        return response

    def test_all_eight_essential_tasks_run_and_success_remains_200(self):
        self.assertEqual(self.invoke().status_code, 200)

    def test_partial_failure_is_500_without_skipping_other_tasks(self):
        self.assertEqual(self.invoke(fail=True).status_code, 500)

    def test_task_body_used_without_celery_eager_tracer_backend(self):
        from deltacrown import lifecycle_cron as cron

        cases = [
            ("_run_no_show", "apps.tournaments.tasks.no_show_timer.check_no_show_matches"),
            ("_run_lobby_close", "apps.tournaments.tasks.no_show_timer.auto_close_expired_lobbies"),
            (
                "_run_payment_expiry",
                "apps.tournaments.tasks.payment_expiry.expire_overdue_payments",
            ),
            (
                "_run_group_playoff_reconcile",
                "apps.tournaments.tasks.lifecycle.reconcile_group_playoff_transitions",
            ),
            (
                "_run_dispute_escalation",
                "apps.tournament_ops.tasks_dispute.dispute_escalation_task",
            ),
        ]
        for runner, path in cases:
            with (
                self.subTest(runner=runner),
                patch(path + ".run", return_value={"processed": 1}) as run,
                patch(path + ".apply", side_effect=AssertionError("Eager tracing forbidden")),
            ):
                self.assertTrue(getattr(cron, runner)()["ok"])
                run.assert_called_once_with()

    def test_direct_task_exception_visible_as_failure(self):
        from deltacrown.lifecycle_cron import _run_payment_expiry

        with patch(
            "apps.tournaments.tasks.payment_expiry.expire_overdue_payments.run",
            side_effect=RuntimeError("synthetic failure"),
        ):
            self.assertFalse(_run_payment_expiry()["ok"])

    def test_auth_and_overlap_rejected_before_tasks(self):
        from deltacrown import lifecycle_cron as cron

        request = RequestFactory().post("/", HTTP_AUTHORIZATION="Bearer wrong")
        with (
            patch.object(cron, "_CRON_SECRET", "synthetic-test-secret"),
            patch.object(cron.cache, "add") as acquire,
        ):
            self.assertEqual(cron.lifecycle_cron(request).status_code, 401)
            acquire.assert_not_called()
            request.META["HTTP_AUTHORIZATION"] = "Bearer synthetic-test-secret"
            acquire.return_value = False
            self.assertEqual(cron.lifecycle_cron(request).status_code, 409)

    def test_auto_confirm_does_not_hide_failures_or_count_skips_as_confirmed(self):
        from deltacrown.lifecycle_cron import _run_auto_confirm_submissions

        with (
            patch(
                "apps.tournaments.models.result_submission.MatchResultSubmission.objects"
            ) as objects,
            patch(
                "apps.tournament_ops.tasks_result_submission.auto_confirm_submission_task.run"
            ) as run,
        ):
            objects.filter.return_value.values_list.return_value.__getitem__.return_value = [
                1,
                2,
                3,
            ]
            run.side_effect = [
                {"status": "success"},
                {"status": "already_processed"},
                RuntimeError("synthetic failure"),
            ]
            result = _run_auto_confirm_submissions()
            self.assertFalse(result["ok"])
            self.assertEqual(result["confirmed"], 1)
            self.assertEqual(result["failed"], 1)


class StorageConfigChecks(SimpleTestCase):
    def test_s3_path_style_preserves_private_delivery_and_actual_region(self):
        from pathlib import Path
        from apps.common.media.configuration import configure
        import os

        with patch.dict(
            os.environ, {"OWNLOBBY_MEDIA_MODE": "s3", "MEDIA_PRIVATE_REGION": "ap-southeast-1"}
        ):
            aliases = {}
            configure(aliases, Path("."), Path("media"))
        options = aliases["private_media"]["OPTIONS"]
        self.assertEqual(options["client_config"].s3, {"addressing_style": "path"})
        self.assertEqual(options["region_name"], "ap-southeast-1")
        self.assertIsNone(options["default_acl"])
        self.assertIsNone(options["custom_domain"])
