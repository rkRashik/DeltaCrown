"""
Riot API — Valorant Game Passport Verification Service (P7-B)

Verifies that a Riot ID (gameName#tagLine) exists via the Riot Account API.
Only runs for Valorant passports. Gracefully degrades when the API key is
missing, expired, or rate-limited — the user's passport is never permanently
rejected due to an infrastructure issue.

Environment variables:
  RIOT_API_KEY              — Riot developer/production key (required for live checks)
  RIOT_ACCOUNT_REGION       — API routing region, default: asia
  RIOT_API_TIMEOUT_SECONDS  — HTTP timeout, default: 6

PUUID storage: provider_data['riot']['puuid'] on GameProfile
Error storage:  GameProfile.verification_error (user-safe text, never raw API response)

Result dict schema
------------------
{
  "status":    "VERIFIED" | "FAILED" | "API_UNAVAILABLE" | "RATE_LIMITED",
  "code":      str,   # granular machine code for admin feedback (see CODES below)
  "puuid":     str | None,
  "error":     str,   # user-safe text
  "admin_msg": str,   # staff-facing detail (never leaked to users)
  "http_status": int | None,  # raw HTTP code for admin diagnostics
}
"""

from __future__ import annotations

import logging
import os
import urllib.error
import urllib.parse
import urllib.request
import json as _json
from typing import Optional, Tuple

logger = logging.getLogger("games.riot_verification")

# Valorant game slugs that trigger Riot verification
VALORANT_SLUGS = {"valorant", "val"}

# Riot Account API base URL per routing region
_REGION_BASE = {
    "americas": "https://americas.api.riotgames.com",
    "europe":   "https://europe.api.riotgames.com",
    "asia":     "https://asia.api.riotgames.com",
    "sea":      "https://sea.api.riotgames.com",
}

# Granular error codes surfaced to admin only, never to users.
CODE_OK               = "ok"
CODE_MISSING_KEY      = "missing_env_key"
CODE_INVALID_KEY_401  = "riot_401_invalid_or_expired_key"
CODE_FORBIDDEN_403    = "riot_403_forbidden"
CODE_NOT_FOUND_404    = "riot_404_riot_id_not_found"
CODE_RATE_LIMITED_429 = "riot_429_rate_limited"
CODE_SERVER_5XX       = "riot_5xx_service_error"
CODE_TIMEOUT          = "timeout_network_error"
CODE_URL_ERROR        = "url_encoding_or_network_error"
CODE_UNEXPECTED       = "unexpected_exception"
CODE_BAD_FORMAT       = "invalid_riot_id_format"


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


def _key_diagnostic() -> str:
    """Return safe key info for logging — never exposes the key itself."""
    key = _api_key()
    if not key:
        return "MISSING"
    return f"length={len(key)} prefix={key[:4]}…"


def is_valorant_passport(game_slug: str) -> bool:
    return (game_slug or "").lower().strip() in VALORANT_SLUGS


def parse_riot_id(raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse 'gameName#tagLine' into (gameName, tagLine).
    Returns (None, None) if the format is invalid.
    Both parts must be non-empty after stripping.
    """
    raw = (raw or "").strip()
    if "#" not in raw:
        return None, None
    parts = raw.split("#", 1)
    game_name = parts[0].strip()
    tag_line  = parts[1].strip()
    if not game_name or not tag_line:
        return None, None
    return game_name, tag_line


def resolve_riot_id_parts(passport) -> Tuple[Optional[str], Optional[str]]:
    """
    Derive (gameName, tagLine) from a GameProfile instance.

    Supports two storage layouts:
      1. Split fields:   passport.ign + passport.discriminator  (preferred)
      2. Combined field: passport.in_game_name as 'name#TAG'

    For Valorant the split-field layout is canonical (ign = '1W ProfXoR',
    discriminator = 'SIIU'). Never trust only combined field — it may be stale.
    """
    ign           = (passport.ign or "").strip()
    discriminator = (passport.discriminator or "").strip()

    # Prefer split fields when both are present.
    if ign and discriminator:
        return ign, discriminator

    # Fall back to combined in_game_name or ign with embedded '#'.
    combined = (passport.in_game_name or passport.ign or "").strip()
    if combined and "#" in combined:
        return parse_riot_id(combined)

    return None, None


def _make_result(
    status: str,
    code: str,
    puuid: Optional[str] = None,
    error: str = "",
    admin_msg: str = "",
    http_status: Optional[int] = None,
) -> dict:
    return {
        "status":      status,
        "code":        code,
        "puuid":       puuid,
        "error":       error,
        "admin_msg":   admin_msg,
        "http_status": http_status,
    }


def verify_riot_id(game_name: str, tag_line: str) -> dict:
    """
    Call Riot Account API and return a structured verification result dict.

    game_name and tag_line are stored raw (may contain spaces).
    This function URL-encodes them before constructing the request URL.

    Never raises. Never logs or returns the API key.
    """
    key = _api_key()
    if not key:
        logger.warning(
            "riot_verification: RIOT_API_KEY not found in environment "
            "(key_diag=%s). Env vars require server restart/redeploy after Render update.",
            _key_diagnostic(),
        )
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_MISSING_KEY,
            error="Verification service unavailable. Your Riot ID will be verified automatically once the service is configured.",
            admin_msg="RIOT_API_KEY is not loaded in the running server process. Add the key in Render env vars and redeploy/restart the server.",
        )

    # URL-encode both parts so names with spaces (e.g. '1W ProfXoR') work correctly.
    encoded_name = urllib.parse.quote(game_name, safe="")
    encoded_tag  = urllib.parse.quote(tag_line, safe="")
    region_base  = _region_base()
    url = f"{region_base}/riot/account/v1/accounts/by-riot-id/{encoded_name}/{encoded_tag}"

    # Log the endpoint (safe) but never the key.
    logger.info(
        "riot_verification: calling endpoint=%s game=%s tag=%s timeout=%ds key_diag=%s",
        url, game_name, tag_line, _timeout(), _key_diagnostic(),
    )

    headers = {"X-Riot-Token": key, "Accept": "application/json"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            body = _json.loads(resp.read().decode("utf-8"))
            puuid = str(body.get("puuid") or "").strip()
            logger.info(
                "riot_verification: VERIFIED game=%s tag=%s puuid_prefix=%s",
                game_name, tag_line, puuid[:8] if puuid else "?",
            )
            return _make_result(
                status="VERIFIED",
                code=CODE_OK,
                puuid=puuid or None,
                http_status=200,
            )

    except urllib.error.HTTPError as exc:
        code = exc.code
        logger.warning(
            "riot_verification: HTTP %d for game=%s tag=%s url=%s",
            code, game_name, tag_line, url,
        )

        if code == 404:
            return _make_result(
                status="FAILED",
                code=CODE_NOT_FOUND_404,
                error="Riot ID not found. Please check your game name and tag and try again.",
                admin_msg=f"Riot API returned 404 for '{game_name}#{tag_line}'. Riot ID does not exist on this account region ({region_base}).",
                http_status=404,
            )
        if code == 401:
            return _make_result(
                status="API_UNAVAILABLE",
                code=CODE_INVALID_KEY_401,
                error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
                admin_msg="Riot API rejected the key with 401 Unauthorized. The RIOT_API_KEY is invalid or expired. Update the key in Render env vars and redeploy.",
                http_status=401,
            )
        if code == 403:
            return _make_result(
                status="API_UNAVAILABLE",
                code=CODE_FORBIDDEN_403,
                error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
                admin_msg="Riot API returned 403 Forbidden. Check that the key has access to the Riot Account-V1 endpoint and the correct product/application settings in the Riot developer portal.",
                http_status=403,
            )
        if code == 429:
            logger.warning("riot_verification: rate limited (429) for game=%s", game_name)
            return _make_result(
                status="RATE_LIMITED",
                code=CODE_RATE_LIMITED_429,
                error="Verification is rate-limited. Your Riot ID has been queued and will be verified shortly.",
                admin_msg="Riot API returned 429 Too Many Requests. Wait a moment and retry.",
                http_status=429,
            )
        if 500 <= code < 600:
            return _make_result(
                status="API_UNAVAILABLE",
                code=CODE_SERVER_5XX,
                error="Riot verification service is temporarily down. Your Riot ID will be verified automatically.",
                admin_msg=f"Riot API returned {code} server error. This is a Riot-side outage — retry later.",
                http_status=code,
            )
        # Other unexpected HTTP codes
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_UNEXPECTED,
            error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
            admin_msg=f"Riot API returned unexpected HTTP {code}.",
            http_status=code,
        )

    except urllib.error.URLError as exc:
        # Covers malformed URLs, DNS failures, refused connections.
        logger.warning(
            "riot_verification: URLError for game=%s url=%s reason=%s",
            game_name, url, exc.reason,
        )
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_URL_ERROR,
            error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
            admin_msg=f"Network/URL error reaching Riot API: {type(exc).__name__}: {exc.reason}. Check server outbound connectivity.",
        )

    except TimeoutError:
        logger.warning("riot_verification: timeout for game=%s url=%s", game_name, url)
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_TIMEOUT,
            error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
            admin_msg=f"Riot API timed out after {_timeout()}s. Retry later or increase RIOT_API_TIMEOUT_SECONDS.",
        )

    except Exception as exc:
        logger.exception("riot_verification: unexpected %s for game=%s", type(exc).__name__, game_name)
        return _make_result(
            status="API_UNAVAILABLE",
            code=CODE_UNEXPECTED,
            error="Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
            admin_msg=f"Unexpected error: {type(exc).__name__}. Check server logs.",
        )


def apply_verification_result(passport, result: dict) -> None:
    """
    Persist the verification result onto a GameProfile instance.

    PUUID stored in provider_data['riot']['puuid'].
    Last HTTP status code stored in provider_data['riot']['last_http_status'].
    Admin message stored in provider_data['riot']['last_admin_msg'] — never surfaced to users.
    """
    from apps.user_profile.models_main import GameProfile
    from django.utils import timezone

    status     = result["status"]
    error      = result.get("error", "")
    puuid      = result.get("puuid")
    http_code  = result.get("http_status")
    admin_msg  = result.get("admin_msg", "")

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

    # Store rich Riot data in provider_data — admin-safe, never user-editable.
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

    provider["riot"] = riot_data
    passport.provider_data = provider

    passport.save(update_fields=[
        "verification_status", "verification_error",
        "last_verification_attempt_at", "verification_attempt_count",
        "verified_at", "provider_data",
    ])


def enqueue_or_verify_sync(passport_id: int) -> None:
    """
    Enqueue async verification via Celery if a worker is available;
    fall back to a synchronous inline check if no broker is reachable.
    """
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
