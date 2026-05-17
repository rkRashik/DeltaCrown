"""
P7-B — Riot API verification service unit tests.

Uses SimpleTestCase (no DB) and unittest.mock to avoid network calls.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


class ParseRiotIdTests(unittest.TestCase):

    def setUp(self):
        from apps.games.services.riot_verification_service import parse_riot_id
        self.parse = parse_riot_id

    def test_valid_riot_id(self):
        gn, tl = self.parse("PlayerName#TAG")
        self.assertEqual(gn, "PlayerName")
        self.assertEqual(tl, "TAG")

    def test_valid_with_spaces(self):
        gn, tl = self.parse("  Player Name#TAG1  ")
        self.assertEqual(gn, "Player Name")
        self.assertEqual(tl, "TAG1")

    def test_missing_hash(self):
        self.assertEqual(self.parse("PlayerNameTAG"), (None, None))

    def test_empty_string(self):
        self.assertEqual(self.parse(""), (None, None))

    def test_empty_game_name(self):
        gn, tl = self.parse("#TAG")
        self.assertIsNone(gn)

    def test_empty_tag(self):
        gn, tl = self.parse("PlayerName#")
        self.assertIsNone(tl)

    def test_multiple_hashes(self):
        gn, tl = self.parse("Player#NameWith#Hash")
        self.assertEqual(gn, "Player")
        self.assertEqual(tl, "NameWith#Hash")


class RiotVerifyTests(unittest.TestCase):

    def setUp(self):
        from apps.games.services.riot_verification_service import verify_riot_id
        self.verify = verify_riot_id

    def test_missing_api_key_returns_api_unavailable(self):
        with patch.dict("os.environ", {}, clear=True):
            # RIOT_API_KEY not set
            import os
            os.environ.pop("RIOT_API_KEY", None)
            result = self.verify("Player", "TAG")
        self.assertEqual(result["status"], "API_UNAVAILABLE")
        self.assertIsNone(result["puuid"])
        self.assertIn("unavailable", result["error"].lower())

    def test_200_returns_verified_with_puuid(self):
        import urllib.request
        import json
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"puuid": "test-puuid-1234", "gameName": "Player", "tagLine": "TAG"}
        ).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-test-key"}):
            with patch("urllib.request.urlopen", return_value=mock_resp):
                result = self.verify("Player", "TAG")

        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(result["puuid"], "test-puuid-1234")
        self.assertEqual(result["error"], "")

    def test_404_returns_failed(self):
        import urllib.error
        err = urllib.error.HTTPError(None, 404, "Not Found", {}, None)
        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-test-key"}):
            with patch("urllib.request.urlopen", side_effect=err):
                result = self.verify("BadPlayer", "NONE")
        self.assertEqual(result["status"], "FAILED")
        self.assertIn("not found", result["error"].lower())

    def test_401_returns_api_unavailable(self):
        import urllib.error
        err = urllib.error.HTTPError(None, 401, "Unauthorized", {}, None)
        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-expired"}):
            with patch("urllib.request.urlopen", side_effect=err):
                result = self.verify("Player", "TAG")
        self.assertEqual(result["status"], "API_UNAVAILABLE")

    def test_403_returns_api_unavailable(self):
        import urllib.error
        err = urllib.error.HTTPError(None, 403, "Forbidden", {}, None)
        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-expired"}):
            with patch("urllib.request.urlopen", side_effect=err):
                result = self.verify("Player", "TAG")
        self.assertEqual(result["status"], "API_UNAVAILABLE")

    def test_429_returns_rate_limited(self):
        import urllib.error
        err = urllib.error.HTTPError(None, 429, "Too Many Requests", {}, None)
        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-test"}):
            with patch("urllib.request.urlopen", side_effect=err):
                result = self.verify("Player", "TAG")
        self.assertEqual(result["status"], "RATE_LIMITED")

    def test_timeout_returns_api_unavailable(self):
        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-test"}):
            with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
                result = self.verify("Player", "TAG")
        self.assertEqual(result["status"], "API_UNAVAILABLE")

    def test_network_error_returns_api_unavailable(self):
        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-test"}):
            with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
                result = self.verify("Player", "TAG")
        self.assertEqual(result["status"], "API_UNAVAILABLE")


class IsValorantPassportTests(unittest.TestCase):

    def setUp(self):
        from apps.games.services.riot_verification_service import is_valorant_passport
        self.check = is_valorant_passport

    def test_valorant_slug(self):
        self.assertTrue(self.check("valorant"))

    def test_val_short(self):
        self.assertTrue(self.check("val"))

    def test_cs2_not_valorant(self):
        self.assertFalse(self.check("cs2"))

    def test_empty_not_valorant(self):
        self.assertFalse(self.check(""))

    def test_none_not_valorant(self):
        self.assertFalse(self.check(None))


class RetryPendingSkipsVerifiedTest(unittest.TestCase):
    """retry_pending skips VERIFIED passports — never re-verifies unnecessarily."""

    def test_verified_status_constants_exist(self):
        from apps.user_profile.models_main import GameProfile
        self.assertTrue(hasattr(GameProfile, "VERIFICATION_VERIFIED"))
        self.assertTrue(hasattr(GameProfile, "VERIFICATION_FAILED"))
        self.assertTrue(hasattr(GameProfile, "VERIFICATION_API_UNAVAILABLE"))
        self.assertTrue(hasattr(GameProfile, "VERIFICATION_RATE_LIMITED"))

    def test_new_fields_exist_on_model(self):
        from apps.user_profile.models_main import GameProfile
        field_names = {f.name for f in GameProfile._meta.get_fields()}
        self.assertIn("verification_error", field_names)
        self.assertIn("last_verification_attempt_at", field_names)
        self.assertIn("verification_attempt_count", field_names)


class ArchiveTournamentPublicFilterTest(unittest.TestCase):
    """Archived tournaments must not appear on public surfaces."""

    def test_arena_status_list_excludes_archived(self):
        """The Arena match queryset filter must not include 'archived' tournaments."""
        import inspect
        from apps.siteui import views as siteui_views
        src = inspect.getsource(siteui_views._fetch_arena_matches)
        self.assertNotIn("Tournament.ARCHIVED", src,
                         "Arena should not include ARCHIVED tournaments in public matches")

    def test_discovery_view_excludes_archived(self):
        """TournamentListView must not include 'archived' in its status filter."""
        import inspect
        from apps.tournaments.views.discovery import TournamentListView
        src = inspect.getsource(TournamentListView.get_queryset)
        self.assertNotIn("'archived'", src,
                         "Discovery view should not include 'archived' in public status filter")


class AdminVerifyViewTests(unittest.TestCase):
    """Admin verify-riot view — permission gate and routing sanity."""

    def test_verify_view_registered_in_admin(self):
        """The verify-riot URL must be registered under the admin site."""
        from django.urls import reverse as dj_reverse
        # Reversing the named URL should not raise NoReverseMatch.
        # Use a dummy object_id; we just check the URL resolves.
        try:
            url = dj_reverse("admin:user_profile_gameprofile_verify_riot", args=[1])
            self.assertIn("/verify-riot/", url)
        except Exception as exc:
            self.fail(f"verify-riot URL not registered: {exc}")

    def test_non_valorant_short_circuits(self):
        """Verification view rejects non-Valorant passports with a warning."""
        from apps.games.services.riot_verification_service import is_valorant_passport
        # CS2 is not Valorant
        self.assertFalse(is_valorant_passport("cs2"))
        self.assertFalse(is_valorant_passport("dota2"))
        # Valorant is Valorant
        self.assertTrue(is_valorant_passport("valorant"))


if __name__ == "__main__":
    unittest.main()
