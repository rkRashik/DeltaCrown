"""Tests for the audit_cloudinary_orphans management command."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.test import TestCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_resource(public_id: str, hours_old: int = 72, size: int = 10000) -> dict:
    created = datetime.now(timezone.utc) - timedelta(hours=hours_old)
    return {
        "public_id": public_id,
        "created_at": created.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bytes": size,
        "secure_url": f"https://res.cloudinary.com/demo/image/upload/{public_id}",
    }


def _run(args: list = None, cloudinary_resources: list = None, db_refs: set = None):
    """Run the command with mocked Cloudinary API and DB."""
    from django.core.management import call_command
    out = StringIO()
    err = StringIO()
    argv = args or []
    kwargs = {k.lstrip("-").replace("-", "_"): True for k in argv if k.startswith("--") and "=" not in k}
    for k in argv:
        if "=" in k:
            key, val = k.lstrip("-").replace("-", "_"), k.split("=", 1)[1]
            try:
                kwargs[key] = int(val)
            except ValueError:
                kwargs[key] = val

    with patch(
        "apps.games.management.commands.audit_cloudinary_orphans._cloudinary_available",
        return_value=True,
    ), patch(
        "apps.games.management.commands.audit_cloudinary_orphans._list_cloudinary_folder",
        return_value=(cloudinary_resources or []),
    ), patch(
        "apps.games.management.commands.audit_cloudinary_orphans._collect_db_references",
        return_value=(db_refs or set()),
    ), patch(
        "apps.games.management.commands.audit_cloudinary_orphans._destroy",
        return_value=True,
    ) as mock_destroy:
        try:
            call_command("audit_cloudinary_orphans", stdout=out, stderr=err, **kwargs)
        except SystemExit:
            pass
        return out.getvalue(), err.getvalue(), mock_destroy


# ---------------------------------------------------------------------------
# Core orphan detection
# ---------------------------------------------------------------------------

class OrphanDetectionTests(TestCase):

    def test_referenced_file_not_reported_as_orphan(self):
        res = _make_resource("media/games/icons/val_abc")
        stdout, _, destroy = _run(
            cloudinary_resources=[res],
            db_refs={"media/games/icons/val_abc"},
        )
        self.assertNotIn("orphan", stdout.lower())
        self.assertNotIn("[orphan]", stdout)
        destroy.assert_not_called()

    def test_unreferenced_game_file_reported_as_orphan(self):
        res = _make_resource("media/games/icons/old_icon_xyz")
        stdout, _, destroy = _run(
            cloudinary_resources=[res],
            db_refs=set(),
        )
        self.assertIn("1 orphaned file", stdout)
        self.assertIn("old_icon_xyz", stdout)
        destroy.assert_not_called()

    def test_no_orphans_when_all_referenced(self):
        resources = [
            _make_resource("media/games/icons/val_abc"),
            _make_resource("media/games/logos/val_logo"),
        ]
        db_refs = {"media/games/icons/val_abc", "media/games/logos/val_logo"}
        stdout, _, _ = _run(cloudinary_resources=resources, db_refs=db_refs)
        self.assertIn("No orphans found", stdout)

    def test_prefix_variant_protects_file(self):
        # DB stores without media/ prefix, Cloudinary has media/ prefix.
        res = _make_resource("media/games/icons/val_abc")
        # _collect_db_references adds both variants, but here we mock it
        # to only contain the un-prefixed version.
        db_refs = {"games/icons/val_abc", "media/games/icons/val_abc"}
        stdout, _, destroy = _run(
            cloudinary_resources=[res],
            db_refs=db_refs,
        )
        self.assertNotIn("[orphan]", stdout)
        destroy.assert_not_called()


# ---------------------------------------------------------------------------
# Dry-run safety
# ---------------------------------------------------------------------------

class DryRunTests(TestCase):

    def test_dry_run_does_not_delete(self):
        res = _make_resource("media/games/icons/orphan_file")
        _, _, destroy = _run(cloudinary_resources=[res], db_refs=set())
        destroy.assert_not_called()

    def test_apply_without_confirm_is_refused(self):
        _, err, destroy = _run(args=["--apply"], cloudinary_resources=[], db_refs=set())
        destroy.assert_not_called()
        self.assertIn("confirm", err.lower())

    def test_apply_with_confirm_calls_destroy(self):
        res = _make_resource("media/games/icons/orphan_old")
        _, _, destroy = _run(
            args=["--apply", "--confirm-delete-orphans"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        destroy.assert_called_once_with("media/games/icons/orphan_old")

    def test_apply_confirm_delete_only_orphans(self):
        orphan = _make_resource("media/games/icons/orphan")
        referenced = _make_resource("media/games/icons/referenced")
        _, _, destroy = _run(
            args=["--apply", "--confirm-delete-orphans"],
            cloudinary_resources=[orphan, referenced],
            db_refs={"media/games/icons/referenced"},
        )
        # Only orphan deleted, not referenced
        destroy.assert_called_once_with("media/games/icons/orphan")


# ---------------------------------------------------------------------------
# Age protection
# ---------------------------------------------------------------------------

class AgeProtectionTests(TestCase):

    def test_recent_file_is_skipped_by_default(self):
        res = _make_resource("media/games/icons/brand_new", hours_old=1)
        stdout, _, destroy = _run(cloudinary_resources=[res], db_refs=set())
        self.assertIn("recent", stdout.lower())
        self.assertNotIn("[orphan]", stdout)
        destroy.assert_not_called()

    def test_old_file_is_not_protected(self):
        res = _make_resource("media/games/icons/very_old", hours_old=200)
        stdout, _, destroy = _run(cloudinary_resources=[res], db_refs=set())
        self.assertIn("orphan", stdout.lower())

    def test_include_recent_includes_new_files(self):
        res = _make_resource("media/games/icons/brand_new", hours_old=1)
        stdout, _, destroy = _run(
            args=["--include-recent"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        self.assertIn("orphan", stdout.lower())

    def test_custom_min_age_hours(self):
        res = _make_resource("media/games/icons/medium_age", hours_old=10)
        # With --min-age-hours=24, a 10h file is still recent → protected
        stdout, _, _ = _run(
            args=["--min-age-hours=24"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        self.assertNotIn("[orphan]", stdout)

        # With --min-age-hours=5, a 10h file is old → orphan
        stdout2, _, _ = _run(
            args=["--min-age-hours=5"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        self.assertIn("orphan", stdout2.lower())


# ---------------------------------------------------------------------------
# Blocked path protection
# ---------------------------------------------------------------------------

class BlockedPathTests(TestCase):

    def test_match_media_never_deleted(self):
        res = _make_resource("media/match_media/screenshot.jpg", hours_old=999)
        stdout, _, destroy = _run(
            args=["--apply", "--confirm-delete-orphans", "--include-recent"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        destroy.assert_not_called()

    def test_payment_proofs_never_deleted(self):
        res = _make_resource("media/payment_proofs/receipt.jpg", hours_old=999)
        _, _, destroy = _run(
            args=["--apply", "--confirm-delete-orphans", "--include-recent"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        destroy.assert_not_called()

    def test_kyc_documents_never_deleted(self):
        res = _make_resource("media/kyc/document.jpg", hours_old=999)
        _, _, destroy = _run(
            args=["--apply", "--confirm-delete-orphans", "--include-recent"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        destroy.assert_not_called()

    def test_certificates_never_deleted(self):
        res = _make_resource("media/certificates/cert.jpg", hours_old=999)
        _, _, destroy = _run(
            args=["--apply", "--confirm-delete-orphans", "--include-recent"],
            cloudinary_resources=[res],
            db_refs=set(),
        )
        destroy.assert_not_called()


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

class JsonOutputTests(TestCase):

    def test_json_flag_produces_valid_json(self):
        res = _make_resource("media/games/icons/orphan")
        stdout, _, _ = _run(args=["--json"], cloudinary_resources=[res], db_refs=set())
        data = json.loads(stdout)
        self.assertIn("summary", data)
        self.assertIn("orphans", data)
        self.assertEqual(data["summary"]["orphans_found"], 1)
        self.assertEqual(data["orphans"][0]["public_id"], "media/games/icons/orphan")

    def test_json_referenced_not_in_orphan_list(self):
        res = _make_resource("media/games/icons/referenced")
        stdout, _, _ = _run(
            args=["--json"],
            cloudinary_resources=[res],
            db_refs={"media/games/icons/referenced"},
        )
        data = json.loads(stdout)
        self.assertEqual(len(data["orphans"]), 0)
        self.assertEqual(data["summary"]["referenced"], 1)

    def test_json_dry_run_flag_is_true(self):
        stdout, _, _ = _run(args=["--json"], cloudinary_resources=[], db_refs=set())
        data = json.loads(stdout)
        self.assertTrue(data["summary"]["dry_run"])

    def test_json_apply_dry_run_flag_is_false(self):
        stdout, _, _ = _run(
            args=["--json", "--apply", "--confirm-delete-orphans"],
            cloudinary_resources=[],
            db_refs=set(),
        )
        data = json.loads(stdout)
        self.assertFalse(data["summary"]["dry_run"])


# ---------------------------------------------------------------------------
# Cloudinary not configured
# ---------------------------------------------------------------------------

class NotConfiguredTests(TestCase):

    def test_exits_when_cloudinary_not_configured(self):
        from django.core.management import call_command
        out = StringIO()
        err = StringIO()
        with patch(
            "apps.games.management.commands.audit_cloudinary_orphans._cloudinary_available",
            return_value=False,
        ):
            try:
                call_command("audit_cloudinary_orphans", stdout=out, stderr=err)
            except SystemExit as exc:
                self.assertEqual(exc.code, 1)
            else:
                self.fail("Expected SystemExit")
        self.assertIn("not configured", err.getvalue().lower())
