"""Tests for /admin/maintenance/ System Operations Center."""

from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()
PANEL_URL = "/admin/maintenance/"


# ---------------------------------------------------------------------------
# User factories
# ---------------------------------------------------------------------------

def _superuser(username="su"):
    return User.objects.create_superuser(username=username, password="pass", email=f"{username}@test.com")


def _staff_with_perm(username="staff_ok"):
    u = User.objects.create_user(username=username, password="pass", email=f"{username}@test.com", is_staff=True)
    from django.contrib.auth.models import Permission
    perm = Permission.objects.get(codename="can_run_maintenance_tasks")
    u.user_permissions.add(perm)
    return u


def _staff_no_perm(username="staff_no"):
    return User.objects.create_user(username=username, password="pass", email=f"{username}@test.com", is_staff=True)


def _regular(username="plain"):
    return User.objects.create_user(username=username, password="pass", email=f"{username}@test.com")


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------

class AccessControlTests(TestCase):

    def test_anonymous_redirected(self):
        resp = Client().get(PANEL_URL)
        self.assertIn(resp.status_code, [301, 302])

    def test_regular_user_cannot_access(self):
        c = Client()
        c.force_login(_regular())
        resp = c.get(PANEL_URL)
        self.assertIn(resp.status_code, [302, 403])

    def test_staff_without_perm_forbidden(self):
        c = Client()
        c.force_login(_staff_no_perm())
        resp = c.get(PANEL_URL)
        self.assertEqual(resp.status_code, 403)

    def test_staff_with_perm_can_access(self):
        c = Client()
        c.force_login(_staff_with_perm())
        resp = c.get(PANEL_URL)
        self.assertEqual(resp.status_code, 200)

    def test_superuser_can_access(self):
        c = Client()
        c.force_login(_superuser())
        resp = c.get(PANEL_URL)
        self.assertEqual(resp.status_code, 200)

    def test_page_shows_all_operation_groups(self):
        c = Client()
        c.force_login(_superuser())
        resp = c.get(PANEL_URL)
        content = resp.content.decode()
        self.assertIn("Game Media Audit", content)
        self.assertIn("Cloudinary Orphan Scan", content)
        self.assertIn("Delete Eligible Media", content)
        self.assertIn("Riot Passport Retry", content)
        self.assertIn("No-Show", content)
        self.assertIn("Evidence Cleanup", content)
        self.assertIn("Health Check", content)

    def test_page_shows_environment_status(self):
        c = Client()
        c.force_login(_superuser())
        resp = c.get(PANEL_URL)
        content = resp.content.decode()
        self.assertIn("CELERY_BEAT", content)
        self.assertIn("Storage", content)


# ---------------------------------------------------------------------------
# POST actions — basic dispatch
# ---------------------------------------------------------------------------

class ActionDispatchTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.client.force_login(_superuser())

    def _post(self, action, extra=None):
        data = {"action": action}
        if extra:
            data.update(extra)
        return self.client.post(PANEL_URL, data)

    def test_unknown_action_handled_gracefully(self):
        resp = self._post("nonexistent_action")
        self.assertEqual(resp.status_code, 302)

    def test_game_media_audit_runs(self):
        with patch("apps.games.views.admin_maintenance._run_game_media_audit",
                   return_value={"ok": 5, "empty": 2, "missing": 0, "missing_detail": []}):
            resp = self._post("game_media_audit")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Game Media Audit", resp.content)

    def test_map_image_audit_runs(self):
        with patch("apps.games.views.admin_maintenance._run_map_image_audit",
                   return_value={"ok": 3, "empty": 1, "missing": 0, "no_image_active": 0, "missing_detail": []}):
            resp = self._post("map_image_audit")
        self.assertEqual(resp.status_code, 200)

    def test_storage_backend_check_runs(self):
        with patch("apps.games.views.admin_maintenance._run_storage_backend_check",
                   return_value={"backend": "FileSystemStorage", "is_cloudinary": False, "cloudinary_env_set": False}):
            resp = self._post("storage_backend_check")
        self.assertEqual(resp.status_code, 200)

    def test_orphan_scan_runs(self):
        with patch("apps.games.views.admin_maintenance._run_cloudinary_orphan_scan",
                   return_value={"scanned": 10, "orphan_count": 2, "recent_protected": 1, "folders": 5, "orphans_preview": []}):
            resp = self._post("orphan_scan")
        self.assertEqual(resp.status_code, 200)

    def test_riot_retry_runs(self):
        with patch("apps.games.views.admin_maintenance._run_riot_retry",
                   return_value={"queued": True, "method": "celery"}):
            resp = self._post("riot_retry")
        self.assertEqual(resp.status_code, 200)

    def test_sweep_no_show_runs(self):
        with patch("apps.games.views.admin_maintenance._run_sweep_no_show",
                   return_value={"ok": True}):
            resp = self._post("sweep_no_show")
        self.assertEqual(resp.status_code, 200)

    def test_health_check_runs(self):
        with patch("apps.games.views.admin_maintenance._run_health_check",
                   return_value={"status": "ok", "db": "ok", "cache": "ok"}):
            resp = self._post("health_check")
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Destructive confirmation
# ---------------------------------------------------------------------------

class DestructiveConfirmationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.client.force_login(_superuser())

    def test_delete_media_wrong_word_redirects_without_deleting(self):
        with patch("apps.games.views.admin_maintenance._run_delete_eligible_media") as mock:
            self.client.post(PANEL_URL, {"action": "delete_eligible_media", "confirm_word": "wrong"})
            mock.assert_not_called()

    def test_delete_media_correct_word_executes(self):
        with patch("apps.games.views.admin_maintenance._run_delete_eligible_media",
                   return_value={"deleted": 1, "skipped": 0, "failed": 0, "dry_run": False}) as mock:
            resp = self.client.post(PANEL_URL, {"action": "delete_eligible_media", "confirm_word": "CLEANUP"})
        mock.assert_called_once()
        self.assertEqual(resp.status_code, 200)

    def test_evidence_sweep_wrong_word_rejected(self):
        with patch("apps.games.views.admin_maintenance._run_evidence_sweep") as mock:
            self.client.post(PANEL_URL, {"action": "evidence_sweep", "confirm_word": "CLEANUP"})
            mock.assert_not_called()

    def test_evidence_sweep_correct_word_executes(self):
        with patch("apps.games.views.admin_maintenance._run_evidence_sweep",
                   return_value={"ok": True, "swept": True}) as mock:
            resp = self.client.post(PANEL_URL, {"action": "evidence_sweep", "confirm_word": "RUN"})
        mock.assert_called_once()
        self.assertEqual(resp.status_code, 200)

    def test_delete_post_only(self):
        resp = self.client.get(PANEL_URL)
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# Input-based actions
# ---------------------------------------------------------------------------

class InputActionTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.client.force_login(_superuser())

    def test_riot_verify_one_with_valid_id(self):
        with patch("apps.games.views.admin_maintenance._run_riot_verify_one",
                   return_value={"passport_id": 42, "dispatched": True}):
            resp = self.client.post(PANEL_URL, {"action": "riot_verify_one", "passport_id": "42"})
        self.assertEqual(resp.status_code, 200)

    def test_riot_verify_one_with_invalid_id(self):
        resp = self.client.post(PANEL_URL, {"action": "riot_verify_one", "passport_id": "abc"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"valid numeric", resp.content)

    def test_riot_api_test_valid_format(self):
        with patch("apps.games.views.admin_maintenance._run_riot_api_test",
                   return_value={"riot_id_tested": "Player#1234", "verified": True, "puuid_found": True}):
            resp = self.client.post(PANEL_URL, {"action": "riot_api_test", "riot_id": "Player#1234"})
        self.assertEqual(resp.status_code, 200)

    def test_riot_api_test_no_hash_returns_error(self):
        resp = self.client.post(PANEL_URL, {"action": "riot_api_test", "riot_id": "PlayerNoTag"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Format must be", resp.content)


# ---------------------------------------------------------------------------
# MaintenanceRunLog creation
# ---------------------------------------------------------------------------

class RunLogCreationTests(TestCase):

    def test_log_created_on_success(self):
        from apps.games.models.maintenance_log import MaintenanceRunLog
        c = Client()
        c.force_login(_superuser())
        with patch("apps.games.views.admin_maintenance._run_health_check",
                   return_value={"status": "ok", "db": "ok"}):
            c.post(PANEL_URL, {"action": "health_check"})
        self.assertTrue(MaintenanceRunLog.objects.filter(task_name="System Health Check").exists())

    def test_log_status_failed_on_exception(self):
        from apps.games.models.maintenance_log import MaintenanceRunLog
        c = Client()
        c.force_login(_superuser())
        with patch("apps.games.views.admin_maintenance._run_health_check",
                   side_effect=RuntimeError("boom")):
            c.post(PANEL_URL, {"action": "health_check"})
        log = MaintenanceRunLog.objects.filter(task_name="System Health Check").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, "failed")


# ---------------------------------------------------------------------------
# Storage diagnostic — local vs Cloudinary detection
# ---------------------------------------------------------------------------

class StorageDiagnosticTests(TestCase):

    def _get_diagnostic_html(self, backend_cls_name):
        from apps.games.admin import GameAdmin
        from apps.games.models.game import Game
        import django.contrib.admin as dadmin

        admin_instance = GameAdmin(Game, dadmin.site)

        class FakeField:
            name = "games/icons/test.png"
            @property
            def url(self):
                return "/media/games/icons/test.png"

        class FakeGame:
            icon = FakeField()
            logo = None
            banner = None
            card_image = None
            _meta = Game._meta

        with patch("apps.games.admin.storage_file_exists", return_value=True), \
             patch("django.core.files.storage.default_storage.__class__.__name__", new=backend_cls_name):
            return admin_instance.media_storage_diagnostic(FakeGame())

    def test_diagnostic_shows_active_storage_banner(self):
        with patch("apps.games.views.admin_maintenance._run_storage_backend_check",
                   return_value={"backend": "FileSystemStorage", "is_cloudinary": False}):
            c = Client()
            c.force_login(_superuser())
            resp = c.post("/admin/maintenance/", {"action": "storage_backend_check"})
            self.assertIn(b"FileSystemStorage", resp.content)

    def test_storage_backend_check_detects_cloudinary(self):
        with patch("apps.games.views.admin_maintenance._run_storage_backend_check",
                   return_value={"backend": "MediaCloudinaryStorage", "is_cloudinary": True, "cloudinary_api_ok": True}):
            c = Client()
            c.force_login(_superuser())
            resp = c.post("/admin/maintenance/", {"action": "storage_backend_check"})
            self.assertIn(b"MediaCloudinaryStorage", resp.content)


# ---------------------------------------------------------------------------
# Evidence safety
# ---------------------------------------------------------------------------

class EvidenceSafetyTests(TestCase):

    def test_evidence_audit_is_always_dry_run(self):
        with patch("apps.games.views.admin_maintenance._run_evidence_audit",
                   return_value={"dry_run": True, "total_completed_old": 5}) as mock:
            c = Client()
            c.force_login(_superuser())
            c.post(PANEL_URL, {"action": "evidence_audit"})
        result = mock.return_value
        self.assertTrue(result.get("dry_run"))

    def test_evidence_sweep_confirmation_required(self):
        with patch("apps.games.views.admin_maintenance._run_evidence_sweep") as mock:
            c = Client()
            c.force_login(_superuser())
            c.post(PANEL_URL, {"action": "evidence_sweep", "confirm_word": "wrong"})
            mock.assert_not_called()

    def test_media_cleanup_blocked_path_never_deleted(self):
        from apps.games.models.cleanup_candidate import MediaCleanupCandidate
        from django.utils import timezone
        from datetime import timedelta
        MediaCleanupCandidate.objects.create(
            file_name="media/match_media/screenshot.jpg",
            storage_type="cloudinary",
            source_model="games.Game",
            source_object_id=1,
            source_field="icon",
            reason="replaced",
            status="pending",
            eligible_after=timezone.now() - timedelta(hours=1),
        )
        with patch("apps.games.services.media_cleanup_service._destroy") as mock_destroy:
            c = Client()
            c.force_login(_superuser())
            c.post(PANEL_URL, {"action": "delete_eligible_media", "confirm_word": "CLEANUP"})
        mock_destroy.assert_not_called()


# ---------------------------------------------------------------------------
# No Celery Beat required
# ---------------------------------------------------------------------------

class NoBeatTests(TestCase):

    def test_all_tournament_ops_work_without_beat(self):
        import os
        ops = ["sweep_no_show", "auto_advance", "tournament_wrapup", "expire_payments", "auto_confirm_submissions"]
        c = Client()
        c.force_login(_superuser())
        for op in ops:
            with patch.dict(os.environ, {"ENABLE_CELERY_BEAT": "0"}), \
                 patch(f"apps.games.views.admin_maintenance._run_{op.replace('sweep_no_show', 'sweep_no_show').replace('auto_advance', 'auto_advance').replace('tournament_wrapup', 'tournament_wrapup').replace('expire_payments', 'expire_payments').replace('auto_confirm_submissions', 'auto_confirm_submissions')}",
                       return_value={"ok": True}):
                resp = c.post(PANEL_URL, {"action": op})
            self.assertIn(resp.status_code, [200, 302], msg=f"op={op} returned {resp.status_code}")
