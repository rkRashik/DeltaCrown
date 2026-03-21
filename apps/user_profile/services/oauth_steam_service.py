"""Steam OpenID helpers for linking CS2 and Dota 2 passports."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.games.models import Game
from apps.user_profile.models import GameOAuthConnection, GameProfile, ProviderAccount

logger = logging.getLogger(__name__)

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
STEAM_SUMMARIES_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
STEAM_ID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(?P<steam_id>\d{17,25})/?$")
STEAM_SUPPORTED_GAMES = {"cs2", "dota2"}
STEAM_OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
STEAM_GAME_APPIDS = {"cs2": 730, "dota2": 570}
STEAM_OPENID_NS = "http://specs.openid.net/auth/2.0"
STEAM_IDENTIFIER_SELECT = "http://specs.openid.net/auth/2.0/identifier_select"


@dataclass
class SteamOpenIDError(Exception):
    error_code: str
    message: str
    status_code: int = 400
    metadata: dict[str, Any] | None = None


@dataclass
class SteamProfileSummary:
    steam_id: str
    personaname: str
    avatar: str
    avatar_medium: str
    avatar_full: str
    profile_url: str


def _timeout_seconds() -> int:
    return 10


def validate_game_slug(game_slug: str) -> str:
    normalized = str(game_slug or "").strip().lower()
    if normalized not in STEAM_SUPPORTED_GAMES:
        raise SteamOpenIDError(
            "UNSUPPORTED_STEAM_GAME",
            "Steam OpenID currently supports cs2 and dota2 only",
            400,
            metadata={"supported_games": sorted(STEAM_SUPPORTED_GAMES)},
        )
    return normalized


def build_steam_openid_redirect_url(*, return_to: str, realm: str) -> str:
    params = {
        "openid.ns": STEAM_OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.identity": STEAM_IDENTIFIER_SELECT,
        "openid.claimed_id": STEAM_IDENTIFIER_SELECT,
        "openid.return_to": return_to,
        "openid.realm": realm,
    }
    return f"{STEAM_OPENID_URL}?{urlencode(params)}"


def verify_steam_callback(query_params: dict[str, Any]) -> str:
    if not query_params:
        raise SteamOpenIDError("INVALID_OPENID_CALLBACK", "Steam callback parameters are missing", 400)

    payload = {}
    for key, value in query_params.items():
        if isinstance(value, (list, tuple)):
            payload[key] = value[-1]
        else:
            payload[key] = value

    claimed_id = str(payload.get("openid.claimed_id", "")).strip()
    if not claimed_id:
        raise SteamOpenIDError("INVALID_OPENID_CALLBACK", "Steam claimed_id is missing", 400)

    verify_payload = payload.copy()
    verify_payload["openid.mode"] = "check_authentication"

    try:
        response = requests.post(
            STEAM_OPENID_URL,
            data=verify_payload,
            timeout=_timeout_seconds(),
        )
    except requests.Timeout as exc:
        raise SteamOpenIDError("STEAM_TIMEOUT", "Steam OpenID verification timed out", 504) from exc
    except requests.RequestException as exc:
        raise SteamOpenIDError(
            "STEAM_NETWORK_ERROR",
            "Unable to reach Steam OpenID endpoint",
            502,
        ) from exc

    if response.status_code >= 400:
        raise SteamOpenIDError(
            "STEAM_VERIFICATION_FAILED",
            "Steam OpenID verification failed",
            502,
            metadata={"status_code": response.status_code},
        )

    if "is_valid:true" not in response.text:
        raise SteamOpenIDError(
            "STEAM_INVALID_SIGNATURE",
            "Steam OpenID signature was not accepted",
            400,
        )

    match = STEAM_ID_RE.match(claimed_id)
    if not match:
        raise SteamOpenIDError(
            "STEAM_INVALID_CLAIMED_ID",
            "Could not extract Steam ID from claimed_id",
            400,
        )

    return match.group("steam_id")


def fetch_player_summary(steam_id: str) -> SteamProfileSummary:
    api_key = getattr(settings, "STEAM_API_KEY", "").strip()
    if not api_key:
        raise SteamOpenIDError(
            "STEAM_CONFIG_MISSING",
            "STEAM_API_KEY is not configured",
            500,
            metadata={"missing": ["STEAM_API_KEY"]},
        )

    try:
        response = requests.get(
            STEAM_SUMMARIES_URL,
            params={"key": api_key, "steamids": steam_id},
            timeout=_timeout_seconds(),
        )
    except requests.Timeout as exc:
        raise SteamOpenIDError("STEAM_TIMEOUT", "Steam summary lookup timed out", 504) from exc
    except requests.RequestException as exc:
        raise SteamOpenIDError(
            "STEAM_NETWORK_ERROR",
            "Unable to reach Steam Web API",
            502,
        ) from exc

    if response.status_code >= 400:
        raise SteamOpenIDError(
            "STEAM_SUMMARY_LOOKUP_FAILED",
            "Steam player summary lookup failed",
            502,
            metadata={"status_code": response.status_code},
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise SteamOpenIDError(
            "STEAM_SUMMARY_LOOKUP_FAILED",
            "Steam player summary response was not valid JSON",
            502,
        ) from exc

    players = payload.get("response", {}).get("players", []) if isinstance(payload, dict) else []
    if not players:
        raise SteamOpenIDError(
            "STEAM_PROFILE_NOT_FOUND",
            "Steam player summary was not found",
            404,
            metadata={"steam_id": steam_id},
        )

    player = players[0]
    return SteamProfileSummary(
        steam_id=steam_id,
        personaname=str(player.get("personaname", "")).strip() or steam_id,
        avatar=str(player.get("avatar", "")).strip(),
        avatar_medium=str(player.get("avatarmedium", "")).strip(),
        avatar_full=str(player.get("avatarfull", "")).strip(),
        profile_url=str(player.get("profileurl", "")).strip(),
    )


def _fetch_owned_appids(steam_id: str) -> set[int]:
    """Return the set of appids owned by this Steam account; empty set on any failure."""
    api_key = getattr(settings, "STEAM_API_KEY", "").strip()
    if not api_key:
        logger.warning("[Steam] STEAM_API_KEY not configured — skipping ownership check")
        return set()
    try:
        response = requests.get(
            STEAM_OWNED_GAMES_URL,
            params={"key": api_key, "steamid": steam_id, "include_appinfo": 0},
            timeout=_timeout_seconds(),
        )
        if response.status_code >= 400:
            logger.warning(
                "[Steam] GetOwnedGames returned %s — proceeding without ownership check",
                response.status_code,
            )
            return set()
        data = response.json()
        return {g["appid"] for g in data.get("response", {}).get("games", []) if "appid" in g}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[Steam] GetOwnedGames failed — proceeding without ownership check: %s", exc)
        return set()


def upsert_steam_passports(
    *, user, summary: SteamProfileSummary
) -> list[tuple[GameProfile, GameOAuthConnection, bool]]:
    """
    Create/update the ProviderAccount for this Steam identity, then iterate over
    every game in STEAM_SUPPORTED_GAMES and ensure a GameProfile + GameOAuthConnection
    exists for each one.  Returns a list of (passport, oauth_conn, created) tuples.
    """
    steam_provider_data = {
        "steam_id": summary.steam_id,
        "persona_name": summary.personaname,
        "profile_url": summary.profile_url,
        "avatar": summary.avatar,
        "avatar_medium": summary.avatar_medium,
        "avatar_full": summary.avatar_full,
        "oauth_provider": GameOAuthConnection.Provider.STEAM,
        "synced_at": timezone.now().isoformat(),
    }

    # Backward-compat metadata dict kept so legacy readers still work
    metadata_update = {
        "steam_id": summary.steam_id,
        "steam_persona_name": summary.personaname,
        "steam_profile_url": summary.profile_url,
        "steam_avatar": summary.avatar,
        "steam_avatar_medium": summary.avatar_medium,
        "steam_avatar_full": summary.avatar_full,
        "oauth_provider": GameOAuthConnection.Provider.STEAM,
    }

    # Fetch outside the transaction to avoid holding a DB connection during HTTP I/O.
    owned_appids = _fetch_owned_appids(summary.steam_id)

    with transaction.atomic():
        # Guard: this Steam account must not be linked to a different user
        linked_to_another = ProviderAccount.objects.filter(
            provider=GameOAuthConnection.Provider.STEAM,
            provider_account_id=summary.steam_id,
        ).exclude(user=user).first()
        if linked_to_another:
            raise SteamOpenIDError(
                "STEAM_ACCOUNT_ALREADY_LINKED",
                "This Steam account is already linked to another profile",
                409,
            )

        # Upsert the single cross-game provider identity anchor
        provider_account, _ = ProviderAccount.objects.update_or_create(
            provider=GameOAuthConnection.Provider.STEAM,
            provider_account_id=summary.steam_id,
            defaults={
                "user": user,
                "provider_data": steam_provider_data,
            },
        )

        results: list[tuple[GameProfile, GameOAuthConnection, bool]] = []

        for game_slug in STEAM_SUPPORTED_GAMES:
            game = Game.objects.filter(slug__iexact=game_slug).first()
            if game is None:
                logger.warning(
                    "[Steam upsert] Game '%s' not found in games_game table — skipping.",
                    game_slug,
                )
                continue

            required_appid = STEAM_GAME_APPIDS.get(game_slug)
            if required_appid is not None and required_appid not in owned_appids:
                logger.info(
                    "[Steam upsert] User does not own %s (appid %s) — skipping passport creation.",
                    game_slug,
                    required_appid,
                )
                continue

            # Create or update the GameProfile for this (user, game) pair
            try:
                passport, created = GameProfile.objects.get_or_create(
                    user=user,
                    game=game,
                    defaults={
                        "game_display_name": game.display_name,
                        "ign": summary.personaname,
                        "platform": "PC",
                        "in_game_name": summary.personaname,
                        "identity_key": summary.steam_id,
                        "visibility": GameProfile.VISIBILITY_PUBLIC,
                        "metadata": metadata_update,
                        "provider_data": {"steam": steam_provider_data},
                        # OAuth-sourced passports are pre-verified — never leave them as PENDING
                        "verification_status": "VERIFIED",
                        "verified_at": timezone.now(),
                    },
                )
            except IntegrityError as exc:
                raise SteamOpenIDError(
                    "STEAM_PASSPORT_CONFLICT",
                    f"Could not create Steam passport for {game_slug}",
                    409,
                ) from exc

            if not created:
                existing_metadata = (
                    passport.metadata.copy() if isinstance(passport.metadata, dict) else {}
                )
                existing_metadata.update(metadata_update)

                existing_provider_data = (
                    passport.provider_data.copy()
                    if isinstance(passport.provider_data, dict)
                    else {}
                )
                existing_provider_data["steam"] = steam_provider_data

                passport.game_display_name = game.display_name
                passport.ign = summary.personaname
                passport.platform = passport.platform or "PC"
                passport.in_game_name = summary.personaname
                passport.identity_key = summary.steam_id
                passport.metadata = existing_metadata
                passport.provider_data = existing_provider_data
                # Re-sync always re-verifies: OAuth identity is authoritative
                passport.verification_status = "VERIFIED"
                passport.verified_at = timezone.now()
                try:
                    passport.save(
                        update_fields=[
                            "game_display_name",
                            "ign",
                            "platform",
                            "in_game_name",
                            "identity_key",
                            "metadata",
                            "provider_data",
                            "verification_status",
                            "verified_at",
                            "updated_at",
                        ]
                    )
                except IntegrityError as exc:
                    raise SteamOpenIDError(
                        "STEAM_IDENTITY_CONFLICT",
                        "This Steam ID is already linked to another account",
                        409,
                    ) from exc

            # Link ProviderAccount ↔ GameProfile via GameOAuthConnection
            oauth_conn, _ = GameOAuthConnection.objects.update_or_create(
                provider_account=provider_account,
                game_profile=passport,
                defaults={
                    "provider": GameOAuthConnection.Provider.STEAM,
                    "access_token": "",
                    "refresh_token": "",
                    "token_type": "openid",
                    "scopes": "openid2",
                    "expires_at": None,
                    "last_synced_at": timezone.now(),
                    "game_shard": "",
                },
            )

            results.append((passport, oauth_conn, created))

    return results
