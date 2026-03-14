"""Epic Games OAuth helpers for Rocket League passport linking."""

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

EPIC_AUTHORIZE_URL = "https://www.epicgames.com/id/api/redirect"
EPIC_TOKEN_URL = "https://api.epicgames.dev/epic/oauth/v2/token"


@dataclass
class EpicOAuthError(Exception):
    error_code: str
    message: str
    status_code: int = 400
    metadata: dict[str, Any] | None = None


def _timeout_seconds() -> int:
    timeout = getattr(settings, "EPIC_OAUTH_TIMEOUT_SECONDS", 10)
    try:
        return max(3, int(timeout))
    except (TypeError, ValueError):
        return 10


def _require_epic_settings() -> None:
    missing = []
    if not getattr(settings, "EPIC_CLIENT_ID", ""):
        missing.append("EPIC_CLIENT_ID")
    if not getattr(settings, "EPIC_CLIENT_SECRET", ""):
        missing.append("EPIC_CLIENT_SECRET")
    if missing:
        raise EpicOAuthError(
            error_code="EPIC_CONFIG_MISSING",
            message="Missing Epic OAuth configuration.",
            status_code=500,
            metadata={"missing": missing},
        )


def build_epic_authorization_url(*, state: str, redirect_uri: str) -> str:
    _require_epic_settings()
    params = {
        "response_type": "code",
        "client_id": settings.EPIC_CLIENT_ID,
        "scope": "basic_profile",
        "redirect_uri": redirect_uri,
        "state": state,
    }
    return f"{EPIC_AUTHORIZE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(*, code: str, redirect_uri: str) -> dict[str, Any]:
    _require_epic_settings()
    if not code:
        raise EpicOAuthError("MISSING_CODE", "Authorization code is required", 400)

    basic = base64.b64encode(
        f"{settings.EPIC_CLIENT_ID}:{settings.EPIC_CLIENT_SECRET}".encode("utf-8")
    ).decode("utf-8")
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    try:
        response = requests.post(EPIC_TOKEN_URL, data=data, headers=headers, timeout=_timeout_seconds())
    except requests.Timeout as exc:
        raise EpicOAuthError("EPIC_TIMEOUT", "Epic token exchange timed out", 504) from exc
    except requests.RequestException as exc:
        raise EpicOAuthError("EPIC_NETWORK_ERROR", "Unable to reach Epic token endpoint", 502) from exc

    payload = _safe_json(response)
    if response.status_code >= 400:
        raise EpicOAuthError(
            "EPIC_TOKEN_EXCHANGE_FAILED",
            payload.get("error_description") or payload.get("errorMessage") or "Epic token exchange failed",
            400 if response.status_code in {400, 401} else 502,
            metadata={"status_code": response.status_code, "epic_error": payload.get("error")},
        )

    account_id = str(payload.get("account_id", "")).strip()
    if not account_id:
        raise EpicOAuthError(
            "EPIC_TOKEN_INVALID_RESPONSE",
            "Epic token response missing account_id",
            502,
        )

    return payload


def upsert_epic_connection(*, user, token_data: dict[str, Any]) -> tuple[GameProfile, GameOAuthConnection, bool]:
    game = Game.objects.filter(slug__iexact="rocketleague").first()
    if game is None:
        raise EpicOAuthError(
            "ROCKETLEAGUE_GAME_NOT_CONFIGURED",
            "Rocket League game record is missing in games_game",
            500,
        )

    account_id = str(token_data.get("account_id", "")).strip()
    display_name = str(token_data.get("displayName", "")).strip() or account_id

    expires_at = None
    expires_in = token_data.get("expires_in")
    if expires_in is not None:
        try:
            expires_at = timezone.now() + timezone.timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            expires_at = None

    metadata_update = {
        "epic_account_id": account_id,
        "epic_display_name": display_name,
        "oauth_provider": GameOAuthConnection.Provider.EPIC,
    }

    with transaction.atomic():
        linked_elsewhere = GameOAuthConnection.objects.filter(
            provider=GameOAuthConnection.Provider.EPIC,
            provider_account_id=account_id,
        ).exclude(passport__user=user).first()
        if linked_elsewhere:
            raise EpicOAuthError(
                "EPIC_ACCOUNT_ALREADY_LINKED",
                "This Epic account is already linked to another profile",
                409,
            )

        try:
            passport, created = GameProfile.objects.get_or_create(
                user=user,
                game=game,
                defaults={
                    "game_display_name": game.display_name,
                    "ign": display_name,
                    "platform": "PC",
                    "in_game_name": display_name,
                    "identity_key": account_id,
                    "visibility": GameProfile.VISIBILITY_PUBLIC,
                    "metadata": metadata_update,
                },
            )
        except IntegrityError as exc:
            raise EpicOAuthError(
                "EPIC_PASSPORT_CONFLICT",
                "Could not create Rocket League passport due to uniqueness conflict",
                409,
            ) from exc

        if not created:
            existing_metadata = passport.metadata.copy() if isinstance(passport.metadata, dict) else {}
            existing_metadata.update(metadata_update)
            passport.game_display_name = game.display_name
            passport.ign = display_name
            passport.platform = passport.platform or "PC"
            passport.in_game_name = display_name
            passport.identity_key = account_id
            passport.metadata = existing_metadata
            try:
                passport.save(
                    update_fields=[
                        "game_display_name",
                        "ign",
                        "platform",
                        "in_game_name",
                        "identity_key",
                        "metadata",
                        "updated_at",
                    ]
                )
            except IntegrityError as exc:
                raise EpicOAuthError(
                    "EPIC_IDENTITY_CONFLICT",
                    "This Epic account is already linked to another account",
                    409,
                ) from exc

        oauth_connection, _ = GameOAuthConnection.objects.update_or_create(
            passport=passport,
            defaults={
                "provider": GameOAuthConnection.Provider.EPIC,
                "provider_account_id": account_id,
                "access_token": str(token_data.get("access_token", "")),
                "refresh_token": str(token_data.get("refresh_token", "")),
                "token_type": str(token_data.get("token_type", "Bearer")),
                "scopes": str(token_data.get("scope", "basic_profile")),
                "expires_at": expires_at,
                "last_synced_at": timezone.now(),
                "game_shard": "",
            },
        )

    return passport, oauth_connection, created


def _safe_json(response: requests.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}