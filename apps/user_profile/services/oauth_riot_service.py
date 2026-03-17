"""Riot OAuth service helpers for Authorization Code flow."""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.games.models import Game
from apps.user_profile.models import GameOAuthConnection, GameProfile

logger = logging.getLogger(__name__)

RIOT_AUTHORIZE_URL = "https://auth.riotgames.com/authorize"
RIOT_TOKEN_URL = "https://auth.riotgames.com/token"
RIOT_USERINFO_URL = "https://auth.riotgames.com/userinfo"


@dataclass
class RiotOAuthError(Exception):
    error_code: str
    message: str
    status_code: int = 400
    metadata: dict[str, Any] | None = None


@dataclass
class RiotIdentity:
    puuid: str
    game_name: str
    tag_line: str

    @property
    def riot_id(self) -> str:
        return f"{self.game_name}#{self.tag_line}"


def _oauth_timeout_seconds() -> int:
    timeout = getattr(settings, "RIOT_OAUTH_TIMEOUT_SECONDS", 10)
    try:
        return max(3, int(timeout))
    except (TypeError, ValueError):
        return 10


def _require_riot_settings() -> None:
    missing = []
    if not getattr(settings, "RIOT_CLIENT_ID", ""):
        missing.append("RIOT_CLIENT_ID")
    if not getattr(settings, "RIOT_CLIENT_SECRET", ""):
        missing.append("RIOT_CLIENT_SECRET")
    if not getattr(settings, "RIOT_REDIRECT_URI", ""):
        missing.append("RIOT_REDIRECT_URI")

    if missing:
        raise RiotOAuthError(
            error_code="RIOT_CONFIG_MISSING",
            message="Missing Riot OAuth configuration.",
            status_code=500,
            metadata={"missing": missing},
        )


def build_riot_authorization_url(state: str) -> str:
    """Build Riot authorization URL for frontend redirect."""
    _require_riot_settings()

    scope = getattr(settings, "RIOT_OAUTH_SCOPES", "openid offline_access")
    scope = scope.strip() or "openid offline_access"

    params = {
        "client_id": settings.RIOT_CLIENT_ID,
        "redirect_uri": settings.RIOT_REDIRECT_URI,
        "response_type": "code",
        "scope": scope,
        "state": state,
    }
    return f"{RIOT_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    _require_riot_settings()

    if not code:
        raise RiotOAuthError("MISSING_CODE", "Authorization code is required", 400)

    basic = base64.b64encode(
        f"{settings.RIOT_CLIENT_ID}:{settings.RIOT_CLIENT_SECRET}".encode("utf-8")
    ).decode("utf-8")

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.RIOT_REDIRECT_URI,
    }
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            RIOT_TOKEN_URL,
            data=payload,
            headers=headers,
            timeout=_oauth_timeout_seconds(),
        )
    except requests.Timeout as exc:
        raise RiotOAuthError(
            "RIOT_TIMEOUT",
            "Riot token exchange timed out",
            504,
        ) from exc
    except requests.RequestException as exc:
        raise RiotOAuthError(
            "RIOT_NETWORK_ERROR",
            "Unable to reach Riot token endpoint",
            502,
        ) from exc

    if response.status_code >= 400:
        details = _safe_json(response)
        error_name = details.get("error") if isinstance(details, dict) else None
        error_desc = details.get("error_description") if isinstance(details, dict) else None

        if response.status_code in {400, 401}:
            raise RiotOAuthError(
                "RIOT_INVALID_CODE",
                error_desc or "Invalid or expired authorization code",
                400,
                metadata={"riot_error": error_name} if error_name else None,
            )

        raise RiotOAuthError(
            "RIOT_TOKEN_EXCHANGE_FAILED",
            error_desc or "Riot token exchange failed",
            502,
            metadata={"riot_error": error_name} if error_name else None,
        )

    token_data = _safe_json(response)
    access_token = token_data.get("access_token") if isinstance(token_data, dict) else None
    if not access_token:
        raise RiotOAuthError(
            "RIOT_TOKEN_INVALID_RESPONSE",
            "Riot token response missing access_token",
            502,
        )

    return token_data


def fetch_userinfo(access_token: str) -> dict[str, Any]:
    """Fetch Riot OIDC userinfo payload (contains sub/puuid)."""
    if not access_token:
        raise RiotOAuthError("MISSING_ACCESS_TOKEN", "Access token is required", 400)

    try:
        response = requests.get(
            RIOT_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=_oauth_timeout_seconds(),
        )
    except requests.Timeout as exc:
        raise RiotOAuthError("RIOT_TIMEOUT", "Riot userinfo request timed out", 504) from exc
    except requests.RequestException as exc:
        raise RiotOAuthError(
            "RIOT_NETWORK_ERROR",
            "Unable to reach Riot userinfo endpoint",
            502,
        ) from exc

    if response.status_code >= 400:
        raise RiotOAuthError(
            "RIOT_USERINFO_FAILED",
            "Failed to fetch Riot user information",
            502,
            metadata={"status_code": response.status_code},
        )

    payload = _safe_json(response)
    puuid = payload.get("sub") if isinstance(payload, dict) else None
    if not puuid:
        raise RiotOAuthError(
            "RIOT_USERINFO_INVALID",
            "Riot userinfo missing subject identifier",
            502,
        )

    return payload


def resolve_riot_identity(userinfo: dict[str, Any], access_token: str) -> RiotIdentity:
    """
    Resolve Riot identity fields required for GameProfile and OAuth linkage.

    Priority:
    1. userinfo claims (if game_name/tag_line are present)
    2. Riot Account API by puuid across configured regional clusters
    """
    puuid = str(userinfo.get("sub", "")).strip()
    if not puuid:
        raise RiotOAuthError("RIOT_USERINFO_INVALID", "Riot userinfo missing sub", 502)

    game_name, tag_line = _extract_riot_id_from_userinfo(userinfo)
    if game_name and tag_line:
        return RiotIdentity(puuid=puuid, game_name=game_name, tag_line=tag_line)

    last_error: RiotOAuthError | None = None
    for cluster in _account_clusters():
        try:
            account_data = fetch_account_by_puuid(cluster, puuid, access_token)
            game_name = str(account_data.get("gameName", "")).strip()
            tag_line = str(account_data.get("tagLine", "")).strip()
            if game_name and tag_line:
                return RiotIdentity(puuid=puuid, game_name=game_name, tag_line=tag_line)
        except RiotOAuthError as exc:
            last_error = exc
            continue

    raise RiotOAuthError(
        "RIOT_ACCOUNT_LOOKUP_FAILED",
        "Unable to resolve Riot gameName/tagLine from userinfo or account API",
        502,
        metadata=last_error.metadata if last_error else None,
    )


def fetch_account_by_puuid(cluster: str, puuid: str, access_token: str) -> dict[str, Any]:
    """Fetch Riot account profile by puuid from a regional cluster endpoint."""
    url = f"https://{cluster}.api.riotgames.com/riot/account/v1/accounts/by-puuid/{puuid}"

    headers = {"Authorization": f"Bearer {access_token}"}
    riot_api_key = getattr(settings, "RIOT_API_KEY", "")
    if riot_api_key:
        headers["X-Riot-Token"] = riot_api_key

    try:
        response = requests.get(url, headers=headers, timeout=_oauth_timeout_seconds())
    except requests.Timeout as exc:
        raise RiotOAuthError(
            "RIOT_TIMEOUT",
            f"Riot account lookup timed out on cluster {cluster}",
            504,
            metadata={"cluster": cluster},
        ) from exc
    except requests.RequestException as exc:
        raise RiotOAuthError(
            "RIOT_NETWORK_ERROR",
            f"Network error during Riot account lookup on cluster {cluster}",
            502,
            metadata={"cluster": cluster},
        ) from exc

    if response.status_code == 404:
        raise RiotOAuthError(
            "RIOT_ACCOUNT_NOT_FOUND",
            "Riot account not found for supplied puuid",
            404,
            metadata={"cluster": cluster},
        )

    if response.status_code >= 400:
        raise RiotOAuthError(
            "RIOT_ACCOUNT_LOOKUP_FAILED",
            f"Riot account API returned {response.status_code}",
            502,
            metadata={"cluster": cluster, "status_code": response.status_code},
        )

    data = _safe_json(response)
    if not isinstance(data, dict):
        raise RiotOAuthError(
            "RIOT_ACCOUNT_LOOKUP_FAILED",
            "Riot account API returned unexpected payload",
            502,
            metadata={"cluster": cluster},
        )

    return data


def upsert_riot_connection(
    *,
    user,
    identity: RiotIdentity,
    token_data: dict[str, Any],
) -> tuple[GameProfile, GameOAuthConnection, bool]:
    """Create/update Valorant GameProfile and linked OAuth connection."""
    game = (
        Game.objects.filter(slug__iexact="valorant").first()
        or Game.objects.filter(name__iexact="Valorant").first()
    )
    if game is None:
        raise RiotOAuthError(
            "VALORANT_GAME_NOT_CONFIGURED",
            "Valorant game record is missing in games_game",
            500,
        )

    riot_id = identity.riot_id
    discriminator = f"#{identity.tag_line}" if identity.tag_line else ""

    metadata_update = {
        "riot_puuid": identity.puuid,
        "riot_game_name": identity.game_name,
        "riot_tag_line": identity.tag_line,
        "oauth_provider": GameOAuthConnection.Provider.RIOT,
    }

    expires_at = None
    expires_in = token_data.get("expires_in")
    if expires_in is not None:
        try:
            expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            expires_at = None

    scope_value = token_data.get("scope", "")
    if isinstance(scope_value, (list, tuple)):
        scope_value = " ".join(str(s).strip() for s in scope_value if str(s).strip())

    with transaction.atomic():
        try:
            passport, created = GameProfile.objects.get_or_create(
                user=user,
                game=game,
                defaults={
                    "game_display_name": game.display_name,
                    "ign": identity.game_name,
                    "discriminator": discriminator,
                    "platform": "PC",
                    "in_game_name": riot_id,
                    "identity_key": riot_id,
                    "visibility": GameProfile.VISIBILITY_PUBLIC,
                    "metadata": metadata_update,
                },
            )
        except IntegrityError as exc:
            raise RiotOAuthError(
                "RIOT_PASSPORT_CONFLICT",
                "Could not create Valorant passport due to uniqueness conflict",
                409,
            ) from exc

        if not created:
            existing_metadata = passport.metadata.copy() if isinstance(passport.metadata, dict) else {}
            existing_metadata.update(metadata_update)

            passport.game_display_name = game.display_name
            passport.ign = identity.game_name
            passport.discriminator = discriminator
            passport.platform = passport.platform or "PC"
            passport.in_game_name = riot_id
            passport.identity_key = riot_id
            passport.metadata = existing_metadata
            try:
                passport.save(
                    update_fields=[
                        "game_display_name",
                        "ign",
                        "discriminator",
                        "platform",
                        "in_game_name",
                        "identity_key",
                        "metadata",
                        "updated_at",
                    ]
                )
            except IntegrityError as exc:
                raise RiotOAuthError(
                    "RIOT_IDENTITY_CONFLICT",
                    "This Riot ID is already linked to another account",
                    409,
                ) from exc

        linked_elsewhere = GameOAuthConnection.objects.filter(
            provider=GameOAuthConnection.Provider.RIOT,
            provider_account_id=identity.puuid,
        ).exclude(passport__user=user).first()
        if linked_elsewhere:
            raise RiotOAuthError(
                "RIOT_ACCOUNT_ALREADY_LINKED",
                "This Riot account is already linked to another profile",
                409,
            )

        try:
            oauth_connection, _ = GameOAuthConnection.objects.update_or_create(
                passport=passport,
                defaults={
                    "provider": GameOAuthConnection.Provider.RIOT,
                    "provider_account_id": identity.puuid,
                    "access_token": str(token_data.get("access_token", "")),
                    "refresh_token": str(token_data.get("refresh_token", "")),
                    "token_type": str(token_data.get("token_type", "Bearer")),
                    "scopes": str(scope_value or ""),
                    "expires_at": expires_at,
                    "last_synced_at": timezone.now(),
                    "game_shard": "",
                },
            )
        except IntegrityError as exc:
            raise RiotOAuthError(
                "RIOT_OAUTH_CONFLICT",
                "This Riot OAuth account is already linked elsewhere",
                409,
            ) from exc

    return passport, oauth_connection, created


def refresh_riot_access_token(conn: GameOAuthConnection) -> GameOAuthConnection:
    """Refresh an expired Riot access token using the stored refresh_token.

    Updates conn.access_token, conn.refresh_token (if rotated), conn.expires_at,
    and conn.last_synced_at, then saves with targeted update_fields.

    Raises:
        RiotOAuthError(status_code=401): refresh token invalid/expired — user must re-auth.
        RiotOAuthError(status_code=502/504): transient network/server failure.
    """
    _require_riot_settings()
    if not conn.refresh_token:
        raise RiotOAuthError(
            "RIOT_NO_REFRESH_TOKEN",
            "No refresh token stored — user must re-authenticate",
            401,
        )

    basic = base64.b64encode(
        f"{settings.RIOT_CLIENT_ID}:{settings.RIOT_CLIENT_SECRET}".encode("utf-8")
    ).decode("utf-8")

    try:
        response = requests.post(
            RIOT_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": conn.refresh_token},
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=_oauth_timeout_seconds(),
        )
    except requests.Timeout as exc:
        raise RiotOAuthError("RIOT_TIMEOUT", "Riot token refresh timed out", 504) from exc
    except requests.RequestException as exc:
        raise RiotOAuthError("RIOT_NETWORK_ERROR", "Unable to reach Riot token endpoint", 502) from exc

    details = _safe_json(response)

    if response.status_code in {400, 401}:
        raise RiotOAuthError(
            "RIOT_REFRESH_FAILED",
            details.get("error_description") or "Riot refresh token invalid or expired — user must re-authenticate",
            401,
            metadata={"riot_error": details.get("error")},
        )

    if response.status_code >= 400:
        raise RiotOAuthError(
            "RIOT_REFRESH_FAILED",
            details.get("error_description") or "Riot token refresh failed",
            502,
            metadata={"status_code": response.status_code, "riot_error": details.get("error")},
        )

    new_access = details.get("access_token")
    if not new_access:
        raise RiotOAuthError("RIOT_REFRESH_INVALID_RESPONSE", "Riot token refresh missing access_token", 502)

    conn.access_token = str(new_access)
    if details.get("refresh_token"):
        conn.refresh_token = str(details["refresh_token"])

    expires_in = details.get("expires_in")
    conn.expires_at = (
        timezone.now() + timezone.timedelta(seconds=int(expires_in))
        if expires_in is not None
        else None
    )
    conn.last_synced_at = timezone.now()
    conn.save(update_fields=["access_token", "refresh_token", "expires_at", "last_synced_at"])

    logger.info(
        "Riot access token refreshed for connection %s (passport_id=%s)",
        conn.pk,
        conn.passport_id,
    )
    return conn


def _account_clusters() -> list[str]:
    configured = getattr(settings, "RIOT_ACCOUNT_API_CLUSTERS", ["americas", "asia", "europe"])
    if isinstance(configured, str):
        clusters = [p.strip().lower() for p in configured.split(",") if p.strip()]
    elif isinstance(configured, (list, tuple)):
        clusters = [str(p).strip().lower() for p in configured if str(p).strip()]
    else:
        clusters = []

    return clusters or ["americas", "asia", "europe"]


def _extract_riot_id_from_userinfo(userinfo: dict[str, Any]) -> tuple[str, str]:
    # Common claim candidates observed in OIDC payloads / Riot docs examples.
    acct = userinfo.get("acct") if isinstance(userinfo.get("acct"), dict) else {}

    game_name = (
        acct.get("game_name")
        or userinfo.get("game_name")
        or userinfo.get("gameName")
        or ""
    )
    tag_line = (
        acct.get("tag_line")
        or acct.get("tagLine")
        or userinfo.get("tag_line")
        or userinfo.get("tagLine")
        or userinfo.get("riot_tagline")
        or ""
    )

    return str(game_name).strip(), str(tag_line).strip().lstrip("#")


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError:
        return {}

    return data if isinstance(data, dict) else {}
