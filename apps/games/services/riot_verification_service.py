"""
Riot API — Valorant Game Passport Verification Service (P7-B)

Verifies that a Riot ID (gameName#tagLine) exists via the Riot Account API.
Only runs for Valorant passports. Gracefully degrades when the API key is
missing, expired, rate-limited, or blocked by Cloudflare.

Environment variables:
  RIOT_API_KEY              — Riot developer/production key (required for live checks)
  RIOT_ACCOUNT_REGION       — API routing region, default: asia
  RIOT_API_TIMEOUT_SECONDS  — HTTP timeout, default: 6
  RIOT_API_USER_AGENT       — User-Agent header, default: DeltaCrown/1.0 (+https://deltacrown.xyz)

PUUID storage:  provider_data['riot']['puuid']
Error storage:  verification_error (user-safe text, never raw API response)
Diag storage:   provider_data['riot']['last_*'] fields — admin-only

Error codes (result["code"])
-----------------------------
  ok                        200 success
  missing_env_key           RIOT_API_KEY absent from env
  riot_401_invalid_key      Riot 401 Unauthorized
  riot_403_forbidden        Riot 403 with normal Riot JSON body
  cloudflare_1010_blocked   Riot 403 with Cloudflare Error 1010 body
  riot_404_not_found        Riot 404 — Riot ID does not exist
  riot_429_rate_limited     Riot 429 Too Many Requests
  riot_5xx_service_error    Riot 5xx server error
  timeout_network_error     Timeout or network failure
  url_error                 URL/connection error (used internally, rare)
  unexpected_exception      Uncaught exception
"""

from __future__ import annotations

import json as _json
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger("games.riot_verification")

VALORANT_SLUGS = {"valorant", "val"}

_REGION_BASE = {
    "americas": "https://americas.api.riotgames.com",
    "europe":   "https://europe.api.riotgames.com",
    "asia":     "https://asia.api.riotgames.com",
    "sea":      "https://sea.api.riotgames.com",
}

# ── Error codes ──────────────────────────────────────────────────────────────
CODE_OK                  = "ok"
CODE_MISSING_KEY         = "missing_env_key"
CODE_INVALID_KEY_401     = "riot_401_invalid_key"
CODE_FORBIDDEN_403       = "riot_403_forbidden"
CODE_CLOUDFLARE_1010     = "cloudflare_1010_blocked"
CODE_NOT_FOUND_404       = "riot_404_not_found"
CODE_RATE_LIMITED_429    = "riot_429_rate_limited"
CODE_SERVER_5XX          = "riot_5xx_service_error"
CODE_TIMEOUT             = "timeout_network_error"
CODE_URL_ERROR           = "url_error"
CODE_BAD_FORMAT          = "invalid_riot_id_format"
CODE_UNEXPECTED          = "unexpected_exception"


# ── Config helpers ───────────────────────────────────────────────────────────

def _api_key() -> str:
    return os.environ.get("RIOT_API_KEY", "").strip()


def _region_base() -> str:
    region = os.environ.get("RIOT_ACCOUNT_REGION", "asia").strip().lower()
    return _REGION_BASE.get(region, _REGION_BASE["asia"])


def _timeout() -> int:
    try:
        return max(1, int(os.environ.get("RIOT_API_TIMEOUT_SECONDS", "6")))
    except (ValueError, TypeError):
        return 6


def _user_agent() -> str:
    return os.environ.get(
        "RIOT_API_USER_AGENT",
        "DeltaCrown/1.0 (+https://deltacrown.xyz)",
    ).strip() or "DeltaCrown/1.0 (+https://deltacrown.xyz)"


def _key_diagnostic() -> str:
    """Safe key info for logging — never exposes the key itself."""
    key = _api_key()
    if not key:
        return "MISSING"
    return f"length={len(key)} prefix={key[:4]}…"


# ── Identity helpers ─────────────────────────────────────────────────────────

def is_valorant_passport(game_slug: str) -> bool:
    return (game_slug or "").lower().strip() in VALORANT_SLUGS


def parse_riot_id(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse 'gameName#tagLine' → (gameName, tagLine).
    Trims leading/trailing whitespace from each part; preserves internal spaces.
    Returns (None, None) on invalid format.
    """
    raw = (raw or "").strip()
    if "#" not in raw:
        return None, None
    game_name, _, tag_line = raw.partition("#")
    game_name = game_name.strip()
    tag_line  = tag_line.strip()
    if not game_name or not tag_line:
        return None, None
    return game_name, tag_line


def resolve_riot_id_parts(passport) -> Tuple[Optional[str], Optional[str]]:
    """
    Derive (gameName, tagLine) from a GameProfile instance.

    Priority:
      1. ign + discriminator (split fields — canonical for Valorant)
      2. in_game_name parsed as 'name#TAG'
    """
    ign           = (passport.ign or "").strip()
    discriminator = (passport.discriminator or "").strip()

    if ign and discriminator:
        return ign, discriminator

    combined = (passport.in_game_name or passport.ign or "").strip()
    if combined and "#" in combined:
        return parse_riot_id(combined)

    return None, None


# ── Result builder ────────────────────────────────────────────────────────────

def _make_result(
    status: str,
    code: str,
    puuid: Optional[str] = None,
    error: str = "",
    admin_msg: str = "",
    http_status: Optional[int] = None,
    error_body: str = "",
) -> dict:
    return {
        "status":      status,
        "code":        code,
        "puuid":       puuid,
        "error":       error,
        "admin_msg":   admin_msg,
        "http_status": http_status,
        "error_body":  error_body[:500] if error_body else "",
    }


# ── Cloudflare 1010 detection ─────────────────────────────────────────────────

def _is_cloudflare_1010(body_text: str) -> bool:
    """
    Return True if the response body indicates Cloudflare Error 1010
    (browser_signature_banned / access denied by WAF).
    Checks for multiple Cloudflare-specific markers — never for API key content.
    """
    if not body_text:
        return False
    lower = body_text.lower()
    markers = (
        "error 1010",
        "browser_signature_banned",
        "error_code\":1010",
        "error_code\": 1010",
        "access denied",
        "cloudflare",
    )
    return any(m in lower for m in markers)


# ── Core verification ─────────────────────────────────────────────────────────

def verify_riot_id(game_name: str, tag_line: str) -> dict:
    """
    Call Riot Account-V1 API via the `requests` library.

    game_name and tag_line may contain spaces; they are URL-encoded before
    the request is sent. Preserves internal spaces (e.g. '1W ProfXoR').

    Never raises. Never logs or returns the API key.
    """
    import urllib.parse
    import requests as _requests

    key = _api_key()
    if not key:
        logger.warning(
            "riot_verification: RIOT_API_KEY not found in environment "
            "(key_diag=%s). Server restart/redeploy required after Render update.",
            _key_diagnostic(),
        )
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_MISSING_KEY,
            error="Verification is queued. We'll retry once the verification service is available.",
            admin_msg=(
                "RIOT_API_KEY is not loaded in the running server process. "
                "Add the key in Render environment variables, then redeploy/restart the server."
            ),
        )

    encoded_name = urllib.parse.quote(game_name, safe="")
    encoded_tag  = urllib.parse.quote(tag_line, safe="")
    region_base  = _region_base()
    ua           = _user_agent()
    url = f"{region_base}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"

    headers = {
        "X-Riot-Token":  key,
        "Accept":        "application/json",
        "User-Agent":    ua,
        "Cache-Control": "no-cache",
    }

    logger.info(
        "riot_verification: calling endpoint=%s game=%r tag=%r timeout=%ds "
        "key_diag=%s ua=%r",
        url, game_name, tag_line, _timeout(), _key_diagnostic(), ua,
    )

    try:
        resp = _requests.get(url, headers=headers, timeout=_timeout())
        body_text = resp.text or ""
        http_code = resp.status_code

        if resp.ok:
            try:
                body = resp.json()
            except Exception:
                body = {}
            puuid = str(body.get("puuid") or "").strip()
            logger.info(
                "riot_verification: VERIFIED game=%r tag=%r puuid_prefix=%s",
                game_name, tag_line, puuid[:8] if puuid else "?",
            )
            return _make_result(
                status="VERIFIED",
                code=CODE_OK,
                puuid=puuid or None,
                http_status=200,
            )

        # Non-2xx — classify by status code + body content.
        body_safe = body_text[:500].strip()
        logger.warning(
            "riot_verification: HTTP %d for game=%r tag=%r url=%s body=%r",
            http_code, game_name, tag_line, url, body_safe[:120],
        )

        if http_code == 403 and _is_cloudflare_1010(body_safe):
            return _make_result(
                status="API_UNAVAILABLE",
                code=CODE_CLOUDFLARE_1010,
                error="Verification is queued. We'll retry once the verification service is available.",
                admin_msg=(
                    "Riot/Cloudflare blocked this server request with Error 1010 "
                    "(browser_signature_banned / access denied). "
                    "The API key is loaded and the endpoint was reached — "
                    "this is a request-signature / WAF / IP reputation issue, not a missing key. "
                    "Possible fixes: (1) Change RIOT_API_USER_AGENT; "
                    "(2) Test locally with the same key — if local works, "
                    "Render's egress IP fingerprint is blocked by Riot/Cloudflare; "
                    "(3) Contact Riot support with the Ray-ID from the response body."
                ),
                http_status=403,
                error_body=body_safe,
            )

        if http_code == 403:
            return _make_result(
                status="API_UNAVAILABLE",
                code=CODE_FORBIDDEN_403,
                error="Verification is queued. We'll retry once the verification service is available.",
                admin_msg=(
                    "Riot API returned 403 Forbidden (normal Riot response, not Cloudflare). "
                    "The key is loaded — Riot rejected access to Account-V1. "
                    "Fix: go to developer.riotgames.com → your application → "
                    "ensure 'Account' (Account-V1) product is enabled. "
                    f"Riot response: {body_safe or '(empty)'}"
                ),
                http_status=403,
                error_body=body_safe,
            )

        if http_code == 404:
            return _make_result(
                status="FAILED",
                code=CODE_NOT_FOUND_404,
                error="Riot ID not found. Please check your game name and tag and try again.",
                admin_msg=(
                    f"Riot API returned 404 for '{game_name}#{tag_line}'. "
                    f"Riot ID does not exist on region {region_base}. "
                    f"Riot response: {body_safe or '(empty)'}"
                ),
                http_status=404,
                error_body=body_safe,
            )

        if http_code == 401:
            return _make_result(
                status="API_UNAVAILABLE",
                code=CODE_INVALID_KEY_401,
                error="Verification is queued. We'll retry once the verification service is available.",
                admin_msg=(
                    "Riot API rejected the key with 401 Unauthorized. "
                    "The RIOT_API_KEY is invalid or has expired. "
                    "Update the key in Render env vars and redeploy. "
                    f"Riot response: {body_safe or '(empty)'}"
                ),
                http_status=401,
                error_body=body_safe,
            )

        if http_code == 429:
            logger.warning("riot_verification: rate limited (429) for game=%r", game_name)
            return _make_result(
                status="RATE_LIMITED",
                code=CODE_RATE_LIMITED_429,
                error="Verification is rate-limited. Your Riot ID has been queued and will be verified shortly.",
                admin_msg="Riot API returned 429 Too Many Requests. Wait a moment and retry.",
                http_status=429,
                error_body=body_safe,
            )

        if 500 <= http_code < 600:
            return _make_result(
                status="API_UNAVAILABLE",
                code=CODE_SERVER_5XX,
                error="Riot verification service is temporarily down. Your Riot ID will be verified automatically.",
                admin_msg=f"Riot API returned {http_code} server error. This is a Riot-side outage — retry later.",
                http_status=http_code,
                error_body=body_safe,
            )

        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_UNEXPECTED,
            error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
            admin_msg=f"Riot API returned unexpected HTTP {http_code}. Body: {body_safe or '(empty)'}",
            http_status=http_code,
            error_body=body_safe,
        )

    except _requests.exceptions.Timeout:
        logger.warning("riot_verification: timeout for game=%r url=%s", game_name, url)
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_TIMEOUT,
            error="Verification is queued. We'll retry once the verification service is available.",
            admin_msg=f"Riot API timed out after {_timeout()}s. Retry later or increase RIOT_API_TIMEOUT_SECONDS.",
        )

    except _requests.exceptions.ConnectionError as exc:
        logger.warning("riot_verification: ConnectionError for game=%r: %s", game_name, type(exc).__name__)
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_URL_ERROR,
            error="Verification is queued. We'll retry once the verification service is available.",
            admin_msg=f"Network/connection error reaching Riot API: {type(exc).__name__}. Check server outbound connectivity.",
        )

    except _requests.exceptions.RequestException as exc:
        logger.warning("riot_verification: RequestException for game=%r: %s", game_name, type(exc).__name__)
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_URL_ERROR,
            error="Verification is queued. We'll retry once the verification service is available.",
            admin_msg=f"requests error: {type(exc).__name__}. Check server logs.",
        )

    except Exception as exc:
        logger.exception("riot_verification: unexpected %s for game=%r", type(exc).__name__, game_name)
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_UNEXPECTED,
            error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
            admin_msg=f"Unexpected error: {type(exc).__name__}. Check server logs.",
        )


# ── Result persistence ────────────────────────────────────────────────────────

def apply_verification_result(passport, result: dict) -> None:
    """
    Persist the verification result onto a GameProfile instance.

    Storage:
      - verification_status / verification_error / timestamps → model fields
      - PUUID → provider_data['riot']['puuid']
      - Diagnostics (http_status, code, admin_msg, error_body) → provider_data['riot']
    """
    from apps.user_profile.models_main import GameProfile
    from django.utils import timezone

    status     = result["status"]
    error      = result.get("error", "")
    puuid      = result.get("puuid")
    http_code  = result.get("http_status")
    admin_msg  = result.get("admin_msg", "")
    error_body = result.get("error_body", "")

    status_map = {
        "VERIFIED":        GameProfile.VERIFICATION_VERIFIED,
        "FAILED":          GameProfile.VERIFICATION_FAILED,
        "API_UNAVAILABLE": GameProfile.VERIFICATION_API_UNAVAILABLE,
        "RATE_LIMITED":    GameProfile.VERIFICATION_RATE_LIMITED,
    }
    new_status = status_map.get(status, GameProfile.VERIFICATION_API_UNAVAILABLE)

    passport.verification_status          = new_status
    passport.verification_error           = error[:300]
    passport.last_verification_attempt_at = timezone.now()
    passport.verification_attempt_count   = (passport.verification_attempt_count or 0) + 1

    if status == "VERIFIED":
        passport.verified_at = timezone.now()

    provider  = passport.provider_data if isinstance(passport.provider_data, dict) else {}
    riot_data = provider.get("riot") if isinstance(provider.get("riot"), dict) else {}

    if puuid:
        riot_data["puuid"] = puuid
    if http_code is not None:
        riot_data["last_http_status"] = http_code
    if result.get("code"):
        riot_data["last_code"] = result["code"]
    if admin_msg:
        riot_data["last_admin_msg"] = admin_msg[:500]
    if error_body:
        riot_data["last_error_body"] = error_body[:500]
    else:
        riot_data.pop("last_error_body", None)

    provider["riot"] = riot_data
    passport.provider_data = provider

    passport.save(update_fields=[
        "verification_status", "verification_error",
        "last_verification_attempt_at", "verification_attempt_count",
        "verified_at", "provider_data",
    ])


# ── Async/sync entry points ───────────────────────────────────────────────────

def enqueue_or_verify_sync(passport_id: int) -> None:
    """Enqueue via Celery if available; fall back to inline synchronous check."""
    try:
        from apps.games.tasks.riot_verification_tasks import verify_game_passport_task
        verify_game_passport_task.delay(passport_id)
        logger.info("riot_verification: queued passport_id=%s", passport_id)
    except Exception as enqueue_err:
        logger.warning(
            "riot_verification: Celery enqueue failed (%s) — running inline for passport_id=%s",
            enqueue_err, passport_id,
        )
        _verify_inline(passport_id)


def _verify_inline(passport_id: int) -> None:
    """Synchronous fallback — runs in the HTTP request thread."""
    from apps.user_profile.models_main import GameProfile
    try:
        passport = GameProfile.objects.select_related("game").get(pk=passport_id)
    except GameProfile.DoesNotExist:
        return

    game_slug = getattr(passport.game, "slug", "") if passport.game else ""
    if not is_valorant_passport(game_slug):
        return

    game_name, tag_line = resolve_riot_id_parts(passport)
    if not game_name or not tag_line:
        logger.warning(
            "riot_verification: cannot resolve Riot ID parts for passport_id=%s "
            "(ign=%r discriminator=%r in_game_name=%r)",
            passport_id, passport.ign, passport.discriminator, passport.in_game_name,
        )
        return

    result = verify_riot_id(game_name, tag_line)
    apply_verification_result(passport, result)
