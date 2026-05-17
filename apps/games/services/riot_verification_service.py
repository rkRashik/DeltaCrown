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
"""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger("games.riot_verification")

# Valorant game slugs that trigger Riot verification
VALORANT_SLUGS = {"valorant", "val"}

# Riot Account API base URL per region
_REGION_BASE = {
    "americas": "https://americas.api.riotgames.com",
    "europe":   "https://europe.api.riotgames.com",
    "asia":     "https://asia.api.riotgames.com",
    "sea":      "https://sea.api.riotgames.com",
}


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


def verify_riot_id(game_name: str, tag_line: str) -> dict:
    """
    Call Riot Account API and return a verification result dict:

    {
      "status":   "VERIFIED" | "FAILED" | "API_UNAVAILABLE" | "RATE_LIMITED",
      "puuid":    str | None,
      "error":    str,          # user-safe error text (empty on success)
    }

    Never raises — all errors are caught and mapped to a safe status.
    """
    key = _api_key()
    if not key:
        logger.info("riot_verification: RIOT_API_KEY not set — marking API_UNAVAILABLE")
        return {
            "status": "API_UNAVAILABLE",
            "puuid":  None,
            "error":  "Verification service unavailable. Your Riot ID will be verified automatically once the service is configured.",
        }

    url = f"{_region_base()}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": key, "Accept": "application/json"}

    try:
        import urllib.request
        import urllib.error
        import json as _json

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            body = _json.loads(resp.read().decode("utf-8"))
            puuid = str(body.get("puuid") or "").strip()
            logger.info(
                "riot_verification: verified game_name=%s tag=%s puuid_prefix=%s",
                game_name, tag_line, puuid[:8] if puuid else "?",
            )
            return {"status": "VERIFIED", "puuid": puuid or None, "error": ""}

    except urllib.error.HTTPError as exc:
        code = exc.code
        if code == 404:
            logger.info("riot_verification: 404 — Riot ID not found game_name=%s tag=%s", game_name, tag_line)
            return {
                "status": "FAILED",
                "puuid":  None,
                "error":  "Riot ID not found. Please check your game name and tag and try again.",
            }
        if code in (401, 403):
            logger.warning("riot_verification: API key rejected (%d) — marking API_UNAVAILABLE", code)
            return {
                "status": "API_UNAVAILABLE",
                "puuid":  None,
                "error":  "Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
            }
        if code == 429:
            logger.warning("riot_verification: rate limited (429)")
            return {
                "status": "RATE_LIMITED",
                "puuid":  None,
                "error":  "Verification is rate-limited. Your Riot ID has been queued and will be verified shortly.",
            }
        # 5xx or unexpected
        logger.warning("riot_verification: unexpected HTTP %d for game_name=%s", code, game_name)
        return {
            "status": "API_UNAVAILABLE",
            "puuid":  None,
            "error":  "Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
        }

    except (TimeoutError, OSError, Exception) as exc:
        logger.warning("riot_verification: network/timeout error — %s", type(exc).__name__)
        return {
            "status": "API_UNAVAILABLE",
            "puuid":  None,
            "error":  "Verification service temporarily unavailable. Your Riot ID will be verified automatically.",
        }


def apply_verification_result(passport, result: dict) -> None:
    """
    Write the verification result from `verify_riot_id` onto a GameProfile
    instance and save. Does NOT commit if the passport is already VERIFIED.

    PUUID is stored in `provider_data['riot']['puuid']` (never in a plain
    user-editable column).
    """
    from apps.user_profile.models_main import GameProfile
    from django.utils import timezone

    status = result["status"]
    error  = result.get("error", "")
    puuid  = result.get("puuid")

    # Map result status to model constant
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
        # Store PUUID in provider_data — never in a user-editable field.
        provider = passport.provider_data if isinstance(passport.provider_data, dict) else {}
        riot_data = provider.get("riot") if isinstance(provider.get("riot"), dict) else {}
        if puuid:
            riot_data["puuid"] = puuid
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
    fall back to a synchronous check if no broker is reachable.
    Designed to be called from passport save() without blocking the request.
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

    raw_id = f"{passport.ign or ''}#{passport.discriminator or ''}".strip("#")
    game_name, tag_line = parse_riot_id(raw_id)
    if not game_name or not tag_line:
        return

    result = verify_riot_id(game_name, tag_line)
    apply_verification_result(passport, result)
