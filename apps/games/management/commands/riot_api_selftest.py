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
            help='Combined Riot ID to test, e.g. "1W ProfXoR#SIUU"',
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

    def handle(self, *args, **options):
        import os
        import urllib.parse
        import urllib.request
        import urllib.error
        import json

        from apps.games.services.riot_verification_service import (
            parse_riot_id,
            _api_key,
            _key_diagnostic,
            _region_base,
            _timeout,
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

        self.stdout.write(f"    RIOT_ACCOUNT_REGION : {region_env}")
        self.stdout.write(f"    Base URL            : {region_base}")
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

        # ── C. API call ────────────────────────────────────────────────────
        self.stdout.write("\n[C] Riot API call")
        headers = {"X-Riot-Token": key, "Accept": "application/json"}

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout_s) as resp:
                status_code = resp.getcode()
                body_raw    = resp.read().decode("utf-8", errors="replace")
                try:
                    body = json.loads(body_raw)
                except json.JSONDecodeError:
                    body = {"raw": body_raw[:300]}

                puuid = str(body.get("puuid") or "").strip()
                self.stdout.write(self.style.SUCCESS(f"    HTTP status : {status_code} OK"))
                if puuid:
                    self.stdout.write(self.style.SUCCESS(f"    PUUID prefix: {puuid[:16]}…"))
                    self.stdout.write(self.style.SUCCESS(
                        f"\n    ✅ SUCCESS — '{game_name}#{tag_line}' is a valid Riot ID."
                    ))
                else:
                    self.stdout.write(self.style.WARNING(
                        "    200 returned but PUUID is empty — unusual, check Riot response."
                    ))
                    self.stdout.write(f"    Body: {body_raw[:300]}")

        except urllib.error.HTTPError as exc:
            status_code = exc.code
            try:
                body_raw = exc.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                body_raw = "(could not read body)"

            self.stdout.write(self.style.ERROR(f"    HTTP status : {status_code}"))
            self.stdout.write(f"    Body        : {body_raw}")

            # ── D. Recommendation ─────────────────────────────────────────
            self.stdout.write("\n[D] Recommendation")
            if status_code == 404:
                self.stdout.write(self.style.WARNING(
                    f"    Riot ID '{game_name}#{tag_line}' was not found on {region_base}.\n"
                    "    Check spelling — gameName and tagLine are case-insensitive but must be exact.\n"
                    "    Also confirm the correct RIOT_ACCOUNT_REGION for this account's region."
                ))
            elif status_code == 401:
                self.stdout.write(self.style.ERROR(
                    "    API key was rejected (401 Unauthorized).\n"
                    "    The key may have expired (development keys last 24 h).\n"
                    "    → Regenerate the key at developer.riotgames.com and update RIOT_API_KEY in Render."
                ))
            elif status_code == 403:
                self.stdout.write(self.style.ERROR(
                    "    403 Forbidden — the key is valid but lacks Account-V1 access.\n"
                    "\n"
                    "    Possible causes:\n"
                    "    1. Personal/Development key: go to developer.riotgames.com → Dashboard\n"
                    "       → make sure 'Account' (Account-V1) is listed in your app's Products.\n"
                    "       If it is not, edit the app and add Account-V1.\n"
                    "\n"
                    "    2. Production key: the application must have Account-V1 approved.\n"
                    "       Submit a production key request at developer.riotgames.com.\n"
                    "\n"
                    "    3. Routing region mismatch: the region must match the player's account.\n"
                    "       APAC players → RIOT_ACCOUNT_REGION=asia (default).\n"
                    "       EU players   → RIOT_ACCOUNT_REGION=europe.\n"
                    "       NA players   → RIOT_ACCOUNT_REGION=americas.\n"
                    "\n"
                    "    4. The Riot ID may belong to a different routing region.\n"
                    "       Try: python manage.py riot_api_selftest "
                    f'--riot-id "{game_name}#{tag_line}" '
                    "after setting RIOT_ACCOUNT_REGION=americas or europe."
                ))
            elif status_code == 429:
                self.stdout.write(self.style.WARNING(
                    "    Rate limited (429). Wait a minute and retry."
                ))
            elif 500 <= status_code < 600:
                self.stdout.write(self.style.WARNING(
                    f"    Riot server error ({status_code}). This is a Riot-side outage. Retry later."
                ))
            else:
                self.stdout.write(
                    f"    Unexpected HTTP {status_code}. Body: {body_raw[:200]}"
                )

        except urllib.error.URLError as exc:
            self.stdout.write(self.style.ERROR(f"    Network error: {exc.reason}"))
            self.stdout.write("\n[D] Recommendation")
            self.stdout.write("    Check server outbound connectivity to api.riotgames.com on port 443.")

        except TimeoutError:
            self.stdout.write(self.style.ERROR(f"    Timeout after {timeout_s}s"))
            self.stdout.write(
                f"\n[D] Recommendation\n"
                "    Increase RIOT_API_TIMEOUT_SECONDS or check network connectivity."
            )

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"    Unexpected error: {type(exc).__name__}: {exc}"))
