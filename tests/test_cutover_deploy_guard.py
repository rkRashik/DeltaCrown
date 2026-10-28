"""QA-only checks: cutover can build only while all public routes stay locked."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from apps.siteui import checks


def config(**overrides):
    values = {
        "DEBUG": False,
        "REQUIRE_PERSISTENT_MEDIA": True,
        "OWNLOBBY_MEDIA_MODE": "hybrid",
        "MEDIA_STORAGE_VERIFIED": False,
        "MEDIA_RESTORE_VERIFIED": False,
        "MEDIA_LEGACY_PRIVACY_VERIFIED": False,
        "STORAGES": {
            "default": {"BACKEND": "apps.common.media.storage.ProtectedS3Storage"},
            "public_media": {
                "BACKEND": "apps.common.media.cloudinary.PublicArtworkStorage"},
            "private_media": {
                "BACKEND": "apps.common.media.storage.ProtectedS3Storage",
                "OPTIONS": {
                    "bucket_name": "fake-private-bucket",
                    "endpoint_url": "https://s3.example.test",
                    "access_key": "synthetic-not-production",
                    "secret_key": "synthetic-not-production",
                },
            },
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class StagedDeploymentGuardTests(unittest.TestCase):

    def run_checks(self, locked, settings_obj=None):
        env = {
            "OWNLOBBY_CUTOVER_LOCKDOWN": "1" if locked else "0",
            "CLOUDINARY_URL": "cloudinary://synthetic-key:synthetic-secret@example",
        }
        with patch.object(checks, "settings", settings_obj or config()):
            with patch.dict(os.environ, env):
                return checks.governed_media_release_check(None)

    def test_lockdown_is_warning_only_with_valid_hybrid_provider(self):
        issues = self.run_checks(locked=True)
        self.assertEqual([item.id for item in issues], ["siteui.W008"])

    def test_public_build_requires_all_real_proofs(self):
        issues = self.run_checks(locked=False)
        self.assertEqual({item.id for item in issues},
                         {"siteui.E005", "siteui.E007"})

    def test_lockdown_does_not_exempt_insecure_storage(self):
        bad = config()
        bad.STORAGES["private_media"]["OPTIONS"]["endpoint_url"] = "http://s3.example.test"
        issues = self.run_checks(locked=True, settings_obj=bad)
        self.assertIn("siteui.E003", {item.id for item in issues})

    def test_lockdown_does_not_exempt_missing_cloudinary_config(self):
        with patch.object(checks, "settings", config()):
            with patch.dict(os.environ, {"OWNLOBBY_CUTOVER_LOCKDOWN": "1",
                                         "CLOUDINARY_URL": ""}):
                issues = checks.governed_media_release_check(None)
        self.assertIn("siteui.E003", {item.id for item in issues})

    def test_lockdown_rejects_legacy_storage_mode(self):
        issues = self.run_checks(locked=True,
                                 settings_obj=config(OWNLOBBY_MEDIA_MODE="legacy"))
        self.assertIn("siteui.E002", {item.id for item in issues})
