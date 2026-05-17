"""
P7-B — Riot API verification service unit tests.

Uses unittest (no DB needed) and unittest.mock to avoid network calls.
Covers: parse, URL encoding, all HTTP error codes, env var loading,
admin URL registration, and archive public filter.
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

    def test_valid_with_spaces_in_name(self):
        """Riot names may contain spaces — e.g. '1W ProfXoR'."""
        gn, tl = self.parse("1W ProfXoR#SIIU")
        self.assertEqual(gn, "1W ProfXoR")
        self.assertEqual(tl, "SIIU")

    def test_leading_trailing_whitespace_stripped(self):
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

    def test_multiple_hashes_splits_on_first(self):
        gn, tl = self.parse("Player#NameWith#Hash")
        self.assertEqual(gn, "Player")
        self.assertEqual(tl, "NameWith#Hash")


class URLEncodingTests(unittest.TestCase):
    """Spaces in game_name must be percent-encoded; requests client must be used."""

    def _make_ok_response(self, puuid="test-puuid"):
        import json
        resp = MagicMock()
        resp.ok = True
        resp.status_code = 200
        resp.text = json.dumps({"puuid": puuid})
        resp.json.return_value = {"puuid": puuid}
        return resp

    def test_space_in_name_url_encoded(self):
        """'1W ProfXoR' must reach Riot as '1W%20ProfXoR', not a raw space."""
        captured_urls = []

        def fake_get(url, headers=None, timeout=None):
            captured_urls.append(url)
            return self._make_ok_response()

        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-test"}):
            with patch("requests.get", side_effect=fake_get):
                from apps.games.services.riot_verification_service import verify_riot_id
                verify_riot_id("1W ProfXoR", "SIIU")

        self.assertTrue(captured_urls, "requests.get was never called")
        url = captured_urls[0]
        self.assertIn("1W%20ProfXoR", url, f"Space not encoded in URL: {url}")
        self.assertNotIn("1W ProfXoR", url, f"Raw space found in URL: {url}")

    def test_correct_headers_sent(self):
        """Requests client must send X-Riot-Token, Accept, User-Agent."""
        captured_headers = {}

        def fake_get(url, headers=None, timeout=None):
            captured_headers.update(headers or {})
            return self._make_ok_response()

        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-testkey123"}):
            with patch("requests.get", side_effect=fake_get):
                from apps.games.services.riot_verification_service import verify_riot_id
                verify_riot_id("Player", "TAG")

        self.assertIn("X-Riot-Token", captured_headers)
        self.assertEqual(captured_headers["X-Riot-Token"], "RGAPI-testkey123")
        self.assertIn("Accept", captured_headers)
        self.assertIn("User-Agent", captured_headers)
        # Key must not appear in User-Agent or Accept
        self.assertNotIn("RGAPI-testkey123", captured_headers["User-Agent"])

    def test_api_key_never_in_url(self):
        """API key must only be in X-Riot-Token header, never in the URL."""
        captured_urls = []

        def fake_get(url, headers=None, timeout=None):
            captured_urls.append(url)
            return self._make_ok_response()

        secret = "RGAPI-secret-never-in-url"
        with patch.dict("os.environ", {"RIOT_API_KEY": secret}):
            with patch("requests.get", side_effect=fake_get):
                from apps.games.services.riot_verification_service import verify_riot_id
                verify_riot_id("Player", "TAG")

        self.assertTrue(captured_urls)
        self.assertNotIn(secret, captured_urls[0])


class ResolveRiotIdPartsTests(unittest.TestCase):
    """resolve_riot_id_parts reads split fields (ign + discriminator) correctly."""

    def setUp(self):
        from apps.games.services.riot_verification_service import resolve_riot_id_parts
        self.resolve = resolve_riot_id_parts

    def _passport(self, ign="", discriminator="", in_game_name=""):
        p = MagicMock()
        p.ign = ign
        p.discriminator = discriminator
        p.in_game_name = in_game_name
        return p

    def test_split_fields_preferred(self):
        gn, tl = self.resolve(self._passport(ign="1W ProfXoR", discriminator="SIIU"))
        self.assertEqual(gn, "1W ProfXoR")
        self.assertEqual(tl, "SIIU")

    def test_combined_fallback(self):
        gn, tl = self.resolve(self._passport(in_game_name="Player#TAG"))
        self.assertEqual(gn, "Player")
        self.assertEqual(tl, "TAG")

    def test_empty_returns_none(self):
        gn, tl = self.resolve(self._passport())
        self.assertIsNone(gn)
        self.assertIsNone(tl)


class RiotVerifyHTTPStatusTests(unittest.TestCase):
    """Each HTTP status maps to the correct granular code and status."""

    def _make_resp(self, status_code, body_text=""):
        resp = MagicMock()
        resp.status_code = status_code
        resp.ok = (200 <= status_code < 300)
        resp.text = body_text
        try:
            import json
            resp.json.return_value = json.loads(body_text) if body_text else {}
        except Exception:
            resp.json.side_effect = ValueError("not json")
        return resp

    def _call(self, status_code, body="", network_exc=None, puuid="p-uuid"):
        from apps.games.services.riot_verification_service import verify_riot_id

        def fake_get(url, headers=None, timeout=None):
            if network_exc:
                raise network_exc
            if status_code == 200:
                import json
                return self._make_resp(200, json.dumps({"puuid": puuid}))
            return self._make_resp(status_code, body)

        with patch.dict("os.environ", {"RIOT_API_KEY": "RGAPI-test"}):
            with patch("requests.get", side_effect=fake_get):
                return verify_riot_id("Player", "TAG")

    def test_200_verified(self):
        r = self._call(200, puuid="test-puuid")
        self.assertEqual(r["status"], "VERIFIED")
        self.assertEqual(r["code"], "ok")
        self.assertEqual(r["puuid"], "test-puuid")
        self.assertEqual(r["http_status"], 200)

    def test_404_failed_with_body(self):
        from apps.games.services.riot_verification_service import CODE_NOT_FOUND_404
        body = '{"status":{"message":"Data not found","status_code":404}}'
        r = self._call(404, body=body)
        self.assertEqual(r["status"], "FAILED")
        self.assertEqual(r["code"], CODE_NOT_FOUND_404)
        self.assertEqual(r["http_status"], 404)
        self.assertIn("not found", r["error"].lower())
        self.assertIn("Data not found", r["error_body"])

    def test_401_api_unavailable(self):
        from apps.games.services.riot_verification_service import CODE_INVALID_KEY_401
        r = self._call(401)
        self.assertEqual(r["status"], "API_UNAVAILABLE")
        self.assertEqual(r["code"], CODE_INVALID_KEY_401)
        self.assertIn("401", r["admin_msg"])

    def test_403_normal_riot_forbidden(self):
        """Normal Riot 403 without Cloudflare markers → riot_403_forbidden."""
        from apps.games.services.riot_verification_service import CODE_FORBIDDEN_403
        body = '{"status":{"message":"Forbidden","status_code":403}}'
        r = self._call(403, body=body)
        self.assertEqual(r["status"], "API_UNAVAILABLE")
        self.assertEqual(r["code"], CODE_FORBIDDEN_403)
        self.assertIn("Account-V1", r["admin_msg"])
        self.assertIn("developer.riotgames.com", r["admin_msg"])
        self.assertNotIn("403", r["error"])

    def test_403_cloudflare_1010_classified_separately(self):
        """403 with Cloudflare Error 1010 body → cloudflare_1010_blocked, not riot_403_forbidden."""
        from apps.games.services.riot_verification_service import CODE_CLOUDFLARE_1010, CODE_FORBIDDEN_403
        cf_body = (
            '{"error_code":1010,"error_name":"browser_signature_banned",'
            '"error_category":"access_denied","title":"Error 1010: Access denied"}'
        )
        r = self._call(403, body=cf_body)
        self.assertEqual(r["status"], "API_UNAVAILABLE")
        self.assertEqual(r["code"], CODE_CLOUDFLARE_1010)
        self.assertNotEqual(r["code"], CODE_FORBIDDEN_403)
        self.assertIn("Cloudflare", r["admin_msg"])
        self.assertIn("1010", r["admin_msg"])
        self.assertNotIn("Account-V1", r["admin_msg"])
        # User-facing message stays calm
        self.assertNotIn("1010", r["error"])

    def test_403_cloudflare_stores_error_body(self):
        cf_body = '{"error_code":1010,"error_name":"browser_signature_banned"}'
        r = self._call(403, body=cf_body)
        self.assertIn("browser_signature_banned", r["error_body"])

    def test_429_rate_limited(self):
        from apps.games.services.riot_verification_service import CODE_RATE_LIMITED_429
        r = self._call(429)
        self.assertEqual(r["status"], "RATE_LIMITED")
        self.assertEqual(r["code"], CODE_RATE_LIMITED_429)

    def test_503_server_error(self):
        from apps.games.services.riot_verification_service import CODE_SERVER_5XX
        r = self._call(503)
        self.assertEqual(r["status"], "API_UNAVAILABLE")
        self.assertEqual(r["code"], CODE_SERVER_5XX)

    def test_timeout_error(self):
        import requests
        from apps.games.services.riot_verification_service import CODE_TIMEOUT
        r = self._call(None, network_exc=requests.exceptions.Timeout("timeout"))
        self.assertEqual(r["status"], "API_UNAVAILABLE")
        self.assertEqual(r["code"], CODE_TIMEOUT)

    def test_connection_error(self):
        import requests
        from apps.games.services.riot_verification_service import CODE_URL_ERROR
        r = self._call(None, network_exc=requests.exceptions.ConnectionError("refused"))
        self.assertEqual(r["status"], "API_UNAVAILABLE")
        self.assertEqual(r["code"], CODE_URL_ERROR)

    def test_error_body_never_exposes_api_key(self):
        """Even if Riot echoes our key, it must not appear in stored fields."""
        secret = "RGAPI-secret-must-not-leak"
        body = '{"message":"forbidden"}'

        def fake_get(url, headers=None, timeout=None):
            return self._make_resp(403, body)

        with patch.dict("os.environ", {"RIOT_API_KEY": secret}):
            with patch("requests.get", side_effect=fake_get):
                from apps.games.services.riot_verification_service import verify_riot_id
                r = verify_riot_id("Player", "TAG")
        self.assertNotIn(secret, r["error_body"])
        self.assertNotIn(secret, r["admin_msg"])


class MissingKeyTests(unittest.TestCase):

    def test_missing_api_key_returns_missing_code(self):
        from apps.games.services.riot_verification_service import verify_riot_id, CODE_MISSING_KEY
        import os
        env = {k: v for k, v in os.environ.items() if k != "RIOT_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            r = verify_riot_id("Player", "TAG")
        self.assertEqual(r["status"], "API_UNAVAILABLE")
        self.assertEqual(r["code"], CODE_MISSING_KEY)
        self.assertIn("RIOT_API_KEY", r["admin_msg"])

    def test_admin_msg_never_contains_key_value(self):
        """The API key value must never appear in admin_msg or error."""
        import requests
        from apps.games.services.riot_verification_service import verify_riot_id
        secret = "RGAPI-super-secret-key"
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 401
        mock_resp.text = '{"status":{"message":"Unauthorized"}}'
        with patch.dict("os.environ", {"RIOT_API_KEY": secret}):
            with patch("requests.get", return_value=mock_resp):
                r = verify_riot_id("Player", "TAG")
        self.assertNotIn(secret, r["admin_msg"])
        self.assertNotIn(secret, r["error"])


class IsValorantPassportTests(unittest.TestCase):

    def setUp(self):
        from apps.games.services.riot_verification_service import is_valorant_passport
        self.check = is_valorant_passport

    def test_valorant_slug(self):   self.assertTrue(self.check("valorant"))
    def test_val_short(self):       self.assertTrue(self.check("val"))
    def test_cs2_not_valorant(self):self.assertFalse(self.check("cs2"))
    def test_empty(self):           self.assertFalse(self.check(""))
    def test_none(self):            self.assertFalse(self.check(None))


class ModelFieldsTest(unittest.TestCase):

    def test_new_verification_fields_exist(self):
        from apps.user_profile.models_main import GameProfile
        field_names = {f.name for f in GameProfile._meta.get_fields()}
        for f in ("verification_error", "last_verification_attempt_at", "verification_attempt_count"):
            self.assertIn(f, field_names, f"Missing field: {f}")

    def test_new_status_constants_exist(self):
        from apps.user_profile.models_main import GameProfile
        for attr in ("VERIFICATION_VERIFIED", "VERIFICATION_FAILED",
                     "VERIFICATION_API_UNAVAILABLE", "VERIFICATION_RATE_LIMITED"):
            self.assertTrue(hasattr(GameProfile, attr), f"Missing constant: {attr}")


class AdminUrlTest(unittest.TestCase):

    def test_verify_riot_url_registered(self):
        from django.urls import reverse
        try:
            url = reverse("admin:user_profile_gameprofile_verify_riot", args=[1])
            self.assertIn("/verify-riot/", url)
        except Exception as exc:
            self.fail(f"verify-riot URL not registered: {exc}")


class ArchivePublicFilterTest(unittest.TestCase):

    def test_arena_excludes_archived(self):
        import inspect
        from apps.siteui import views as sv
        src = inspect.getsource(sv._fetch_arena_matches)
        self.assertNotIn("Tournament.ARCHIVED", src)

    def test_discovery_excludes_archived(self):
        import inspect
        from apps.tournaments.views.discovery import TournamentListView
        src = inspect.getsource(TournamentListView.get_queryset)
        self.assertNotIn("'archived'", src)


if __name__ == "__main__":
    unittest.main()
