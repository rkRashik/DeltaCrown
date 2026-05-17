"""Tests for game media safety helpers and the audit_game_media command."""

from __future__ import annotations

from io import StringIO
from unittest.mock import MagicMock, patch, PropertyMock

from django.test import TestCase, override_settings

from apps.common.media_urls import safe_game_image_url, storage_file_exists, field_file_url


# ---------------------------------------------------------------------------
# Helpers / mocks
# ---------------------------------------------------------------------------

def _make_field(name: str = "", url: str = "", url_exc=None):
    """Return a mock ImageField-like object."""
    field = MagicMock()
    field.name = name
    if url_exc is not None:
        type(field).url = PropertyMock(side_effect=url_exc)
    else:
        type(field).url = PropertyMock(return_value=url)
    # Truthiness mirrors Django ImageField: truthy when name is set.
    field.__bool__ = lambda self: bool(name)
    return field


# ---------------------------------------------------------------------------
# safe_game_image_url
# ---------------------------------------------------------------------------

class SafeGameImageUrlTests(TestCase):

    def test_returns_url_when_field_has_name_and_url(self):
        field = _make_field(name="games/icons/val.png", url="/media/games/icons/val.png")
        result = safe_game_image_url(field)
        self.assertEqual(result, "/media/games/icons/val.png")

    def test_returns_fallback_static_when_field_is_none(self):
        with patch("apps.common.media_urls._static", return_value="/static/img/game_logos/default_game_logo.jpg"):
            result = safe_game_image_url(None, fallback_static="img/game_logos/default_game_logo.jpg")
        self.assertEqual(result, "/static/img/game_logos/default_game_logo.jpg")

    def test_returns_fallback_when_field_name_empty(self):
        field = _make_field(name="", url="")
        with patch("apps.common.media_urls._static", return_value="/static/fallback.jpg"):
            result = safe_game_image_url(field, fallback_static="fallback.jpg")
        self.assertEqual(result, "/static/fallback.jpg")

    def test_returns_fallback_when_url_raises(self):
        field = _make_field(name="games/icons/broken.png", url_exc=Exception("storage error"))
        with patch("apps.common.media_urls._static", return_value="/static/fallback.jpg"):
            result = safe_game_image_url(field, fallback_static="fallback.jpg")
        self.assertEqual(result, "/static/fallback.jpg")

    def test_returns_empty_string_when_no_field_and_no_fallback(self):
        result = safe_game_image_url(None)
        self.assertEqual(result, "")

    def test_cloudinary_url_returned_even_if_may_404(self):
        # safe_game_image_url does NOT check storage.exists — that's intentional.
        cloudinary_url = "https://res.cloudinary.com/demo/image/upload/games/icons/val.png"
        field = _make_field(name="games/icons/val.png", url=cloudinary_url)
        result = safe_game_image_url(field)
        self.assertEqual(result, cloudinary_url)


# ---------------------------------------------------------------------------
# storage_file_exists
# ---------------------------------------------------------------------------

class StorageFileExistsTests(TestCase):

    def test_returns_true_when_storage_says_exists(self):
        field = _make_field(name="games/icons/val.png")
        with patch("apps.common.media_urls.default_storage") as mock_storage:
            mock_storage.exists.return_value = True
            self.assertTrue(storage_file_exists(field))
            mock_storage.exists.assert_called_once_with("games/icons/val.png")

    def test_returns_false_when_storage_says_missing(self):
        field = _make_field(name="games/icons/missing.png")
        with patch("apps.common.media_urls.default_storage") as mock_storage:
            mock_storage.exists.return_value = False
            self.assertFalse(storage_file_exists(field))

    def test_returns_false_when_field_name_empty(self):
        field = _make_field(name="")
        with patch("apps.common.media_urls.default_storage") as mock_storage:
            self.assertFalse(storage_file_exists(field))
            mock_storage.exists.assert_not_called()

    def test_returns_false_when_storage_raises(self):
        field = _make_field(name="games/icons/val.png")
        with patch("apps.common.media_urls.default_storage") as mock_storage:
            mock_storage.exists.side_effect = Exception("connection error")
            self.assertFalse(storage_file_exists(field))

    def test_accepts_raw_name_string(self):
        with patch("apps.common.media_urls.default_storage") as mock_storage:
            mock_storage.exists.return_value = True
            self.assertTrue(storage_file_exists("games/icons/val.png"))
            mock_storage.exists.assert_called_once_with("games/icons/val.png")

    def test_returns_false_for_none(self):
        with patch("apps.common.media_urls.default_storage") as mock_storage:
            self.assertFalse(storage_file_exists(None))
            mock_storage.exists.assert_not_called()


# ---------------------------------------------------------------------------
# field_file_url (existing helper) — smoke tests for exception safety
# ---------------------------------------------------------------------------

class FieldFileUrlSafetyTests(TestCase):

    def test_returns_empty_for_none(self):
        self.assertEqual(field_file_url(None), "")

    def test_returns_empty_for_falsy_field(self):
        field = _make_field(name="", url="")
        self.assertEqual(field_file_url(field), "")

    def test_does_not_crash_when_url_raises(self):
        field = _make_field(name="games/icons/x.png", url_exc=ValueError("boom"))
        # Should not raise; returns "" or normalized fallback
        result = field_file_url(field)
        self.assertIsInstance(result, str)


# ---------------------------------------------------------------------------
# audit_game_media command — smoke tests without DB
# ---------------------------------------------------------------------------

class AuditGameMediaCommandTests(TestCase):

    def _run_command(self, **kwargs):
        from django.core.management import call_command
        out = StringIO()
        err = StringIO()
        try:
            call_command("audit_game_media", stdout=out, stderr=err, **kwargs)
        except SystemExit:
            pass
        return out.getvalue(), err.getvalue()

    def test_command_runs_without_crash_on_empty_db(self):
        # No games → should succeed without error.
        stdout, _ = self._run_command()
        self.assertIn("Summary:", stdout)

    def test_json_flag_produces_valid_json(self):
        import json
        stdout, _ = self._run_command(json_output=True)
        data = json.loads(stdout)
        self.assertIn("summary", data)
        self.assertIn("games", data)

    def test_only_missing_flag_accepted(self):
        stdout, _ = self._run_command(only_missing=True)
        self.assertIn("Summary:", stdout)
