"""
Management command: riot_api_selftest

Diagnoses the Riot Account-V1 API integration without touching the database
or leaking the API key. Safe to run in production for debugging.

Usage:
    python manage.py riot_api_selftest --riot-id "1W ProfXoR#SIUU"
    python manage.py riot_api_selftest --game-name "1W ProfXoR" --tag-line "SIUU"

Output:
    A. Environment check  — key loaded? region configured?
    B. API call result    — HTTP status, Riot response body (safe), PUUID prefix
    C. Recommendation     — what to do next

Never logs or prints the API key.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Test Riot Account-V1 API connectivity and diagnose 4xx errors."

    def add_arguments(self, parser):
        parser.add_argument(
            "--riot-id",
            type=str,
            default="",
            help='Combined Riot ID, e.g. "1W ProfXoR#SIUU"',
        )
        parser.add_argument(
            "--game-name",
            type=str,
            default="",
            help='Riot game name (gameName), e.g. "1W ProfXoR"',
        )
        parser.add_argument(
            "--tag-line",
            type=str,
            default="",
            help='Riot tag line (tagLine), e.g. "SIUU"',
        )
        parser.add_argument(
            "--region",
            type=str,
            default="",
            help='Override RIOT_ACCOUNT_REGION for this run (asia/americas/europe/sea)',
        )

    def handle(self, *args, **options):
        import os
        import urllib.parse
        import requests as _requests

        from apps.games.services.riot_verification_service import (
            parse_riot_id,
            _api_key,
            _key_diagnostic,
            _region_base,
            _timeout,
            _user_agent,
            _is_cloudflare_1010,
            CODE_CLOUDFLARE_1010,
            _REGION_BASE,
        )

        self.stdout.write(self.style.MIGRATE_HEADING("\n── Riot API Self-Test ──────────────────────────────────────"))

        # ── A. Environment ────────────────────────────────────────────────
        self.stdout.write("\n[A] Environment")
        key = _api_key()
        region_base = _region_base()
        timeout_s = _timeout()
        region_env = os.environ.get("RIOT_ACCOUNT_REGION", "asia (default)")

        if key:
            self.stdout.write(f"    RIOT_API_KEY : ✓ loaded  ({_key_diagnostic()})")
        else:
            self.stdout.write(self.style.ERROR(
                "    RIOT_API_KEY : ✗ MISSING — add to Render env vars and redeploy"
            ))
            self.stdout.write(self.style.WARNING(
                "\n    Selftest cannot call Riot without a key. Aborting."
            ))
            return

        ua = _user_agent()
        # Allow --region override for cross-region testing.
        region_override = (options.get("region") or "").strip().lower()
        if region_override and region_override in _REGION_BASE:
            region_base = _REGION_BASE[region_override]
            self.stdout.write(f"    (region overridden to: {region_override})")

        self.stdout.write(f"    RIOT_ACCOUNT_REGION : {region_env}")
        self.stdout.write(f"    Base URL            : {region_base}")
        self.stdout.write(f"    User-Agent          : {ua}")
        self.stdout.write(f"    Timeout             : {timeout_s}s")

        # ── B. Resolve Riot ID ────────────────────────────────────────────
        self.stdout.write("\n[B] Riot ID")
        riot_id_str = (options.get("riot_id") or "").strip()
        game_name   = (options.get("game_name") or "").strip()
        tag_line    = (options.get("tag_line") or "").strip()

        if riot_id_str:
            gn, tl = parse_riot_id(riot_id_str)
            if gn and tl:
                game_name, tag_line = gn, tl
            else:
                self.stdout.write(self.style.ERROR(
                    f"    Cannot parse '{riot_id_str}' — expected 'gameName#tagLine'"
                ))
                return

        if not game_name or not tag_line:
            self.stdout.write(self.style.WARNING(
                "    No Riot ID provided. Provide --riot-id 'gameName#tagLine' or "
                "--game-name / --tag-line."
            ))
            self.stdout.write("    Skipping API call — env check complete.")
            return

        # Trim but preserve internal spaces.
        game_name = game_name.strip()
        tag_line  = tag_line.strip()
        self.stdout.write(f"    gameName : {game_name!r}")
        self.stdout.write(f"    tagLine  : {tag_line!r}")

        encoded_name = urllib.parse.quote(game_name, safe="")
        encoded_tag  = urllib.parse.quote(tag_line, safe="")
        url = f"{region_base}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"
        self.stdout.write(f"    URL      : {url}")

        # ── C. API call (via requests, same as the production service) ──────
        self.stdout.write("\n[C] Riot API call")
        headers = {
            "X-Riot-Token":  key,
            "Accept":        "application/json",
            "User-Agent":    ua,
            "Cache-Control": "no-cache",
        }

        try:
            resp     = _requests.get(url, headers=headers, timeout=timeout_s)
            body_raw = resp.text or ""
            status_code = resp.status_code

            if resp.ok:
                try:
                    body = resp.json()
                except Exception:
                    body = {}
                puuid = str(body.get("puuid") or "").strip()
                self.stdout.write(self.style.SUCCESS(f"    HTTP status : {status_code} OK"))
                if puuid:
                    self.stdout.write(self.style.SUCCESS(f"    PUUID prefix: {puuid[:16]}…"))
                    self.stdout.write(self.style.SUCCESS(
                        f"\n    ✅ SUCCESS — '{game_name}#{tag_line}' is a valid Riot ID."
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        "    200 returned but PUUID is empty — unusual. Body: " + body_raw[:200]
                    ))
                return

            # Non-2xx
            self.stdout.write(self.style.ERROR(f"    HTTP status : {status_code}"))
            self.stdout.write(f"    Body        : {body_raw[:500]}")

            # ── D. Classification + recommendation ────────────────────────
            self.stdout.write("\n[D] Classification & Recommendation")

            if status_code == 403 and _is_cloudflare_1010(body_raw):
                self.stdout.write(self.style.ERROR(
                    f"    Code        : {CODE_CLOUDFLARE_1010}"
                ))
                self.stdout.write(self.style.WARNING(
                    "\n    Cloudflare Error 1010 (browser_signature_banned).\n"
                    "    The key is loaded and the endpoint was reached,\n"
                    "    but Cloudflare/Riot WAF blocked the request based on\n"
                    "    request signature / IP reputation / User-Agent.\n"
                    "\n"
                    "    Steps to resolve:\n"
                    "    1. Change RIOT_API_USER_AGENT env var and redeploy.\n"
                    "    2. Run this selftest LOCALLY with the same key:\n"
                    f"       RIOT_API_KEY=<key> python manage.py riot_api_selftest --riot-id \"{game_name}#{tag_line}\"\n"
                    "       If local works → Render egress IP is blocked.\n"
                    "       If local also fails → request signature issue.\n"
                    "    3. Extract the Ray-ID from the body above and file a\n"
                    "       Riot developer support ticket.\n"
                    "    4. Passport stays PENDING — do not mark user's Riot ID invalid.\n"
                ))
            elif status_code == 403:
                self.stdout.write(self.style.ERROR(
                    "    Code        : riot_403_forbidden\n"
                    "    403 Forbidden (normal Riot response — not Cloudflare).\n"
                    "    The key is valid but the application lacks Account-V1 access.\n"
                    "    → go to developer.riotgames.com → app → enable 'Account' product."
                ))
            elif status_code == 404:
                self.stdout.write(self.style.WARNING(
                    f"    Code        : riot_404_not_found\n"
                    f"    Riot ID '{game_name}#{tag_line}' was not found on {region_base}.\n"
                    "    Check spelling / region. Try --region americas or --region europe."
                ))
            elif status_code == 401:
                self.stdout.write(self.style.ERROR(
                    "    Code        : riot_401_invalid_key\n"
                    "    API key rejected (401 Unauthorized). Key expired or invalid.\n"
                    "    → Regenerate at developer.riotgames.com → update RIOT_API_KEY in Render."
                ))
            elif status_code == 429:
                self.stdout.write(self.style.WARNING(
                    "    Code        : riot_429_rate_limited\n"
                    "    Rate limited. Wait a minute and retry."
                ))
            elif 500 <= status_code < 600:
                self.stdout.write(self.style.WARNING(
                    f"    Code        : riot_5xx_service_error\n"
                    f"    Riot server error ({status_code}). Retry later."
                ))
            else:
                self.stdout.write(f"    Unexpected HTTP {status_code}.")

        except _requests.exceptions.Timeout:
            self.stdout.write(self.style.ERROR(f"    Timeout after {timeout_s}s"))
            self.stdout.write("\n[D] Recommendation\n    Increase RIOT_API_TIMEOUT_SECONDS or check connectivity.")

        except _requests.exceptions.ConnectionError as exc:
            self.stdout.write(self.style.ERROR(f"    Connection error: {type(exc).__name__}"))
            self.stdout.write("\n[D] Recommendation\n    Check server outbound connectivity to api.riotgames.com on port 443.")

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"    Unexpected error: {type(exc).__name__}: {exc}"))
