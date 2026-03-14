"""Steam OpenID API views for CS2 and Dota 2 passport linking."""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from apps.common.api_responses import error_response, success_response, validation_error_response
from apps.user_profile.services.oauth_steam_service import (
    SteamOpenIDError,
    build_steam_openid_redirect_url,
    fetch_player_summary,
    upsert_steam_connection,
    validate_game_slug,
    verify_steam_callback,
)

logger = logging.getLogger(__name__)

STATE_CACHE_PREFIX = "steam_openid_state:"
STATE_TTL_SECONDS = 600


@method_decorator(login_required, name="dispatch")
class SteamLoginRedirectView(View):
    """Return the Steam OpenID redirect URL for frontend redirect."""

    def get(self, request: HttpRequest) -> JsonResponse:
        game_slug = request.GET.get("game")
        try:
            game_slug = validate_game_slug(game_slug)
        except SteamOpenIDError as exc:
            return error_response(exc.error_code, exc.message, status=exc.status_code, metadata=exc.metadata)

        state = secrets.token_urlsafe(32)
        cache.set(
            f"{STATE_CACHE_PREFIX}{state}",
            {"user_id": request.user.id, "game_slug": game_slug},
            timeout=STATE_TTL_SECONDS,
        )

        callback_url = request.build_absolute_uri(reverse("user_profile:steam_openid_callback"))
        return_to = f"{callback_url}?{urlencode({'state': state, 'game': game_slug})}"
        realm = f"{request.scheme}://{request.get_host()}"
        authorization_url = build_steam_openid_redirect_url(return_to=return_to, realm=realm)

        return success_response(
            {
                "authorization_url": authorization_url,
                "state": state,
                "game": game_slug,
                "expires_in_seconds": STATE_TTL_SECONDS,
            }
        )


@method_decorator(login_required, name="dispatch")
class SteamCallbackView(View):
    """Verify Steam OpenID callback and connect a Steam game passport."""

    def get(self, request: HttpRequest) -> JsonResponse:
        state = str(request.GET.get("state", "")).strip()
        game_slug = request.GET.get("game")

        if not state:
            return validation_error_response(
                field_errors={"state": "state is required"},
                message="Missing OpenID state",
            )

        try:
            game_slug = validate_game_slug(game_slug)
        except SteamOpenIDError as exc:
            return error_response(exc.error_code, exc.message, status=exc.status_code, metadata=exc.metadata)

        cache_key = f"{STATE_CACHE_PREFIX}{state}"
        cached = cache.get(cache_key)
        cache.delete(cache_key)

        if not cached or cached.get("user_id") != request.user.id or cached.get("game_slug") != game_slug:
            return error_response(
                error_code="INVALID_OPENID_STATE",
                message="Steam OpenID state is invalid or has expired",
                status=400,
            )

        try:
            steam_id = verify_steam_callback(request.GET.dict())
            summary = fetch_player_summary(steam_id)
            passport, oauth_connection, passport_created = upsert_steam_connection(
                user=request.user,
                game_slug=game_slug,
                summary=summary,
            )
        except SteamOpenIDError as exc:
            return error_response(
                error_code=exc.error_code,
                message=exc.message,
                status=exc.status_code,
                metadata=exc.metadata,
            )
        except Exception as exc:
            logger.exception("Unexpected Steam OpenID callback failure: %s", exc)
            return error_response(
                error_code="SERVER_ERROR",
                message="Unexpected error while processing Steam callback",
                status=500,
            )

        return success_response(
            {
                "message": "Steam account connected successfully",
                "provider": oauth_connection.provider,
                "provider_account_id": oauth_connection.provider_account_id,
                "passport": {
                    "id": passport.id,
                    "game_slug": passport.game.slug,
                    "ign": passport.ign,
                    "identity_key": passport.identity_key,
                    "created": passport_created,
                },
                "steam_profile": {
                    "steam_id": summary.steam_id,
                    "personaname": summary.personaname,
                    "avatar": summary.avatar_full or summary.avatar_medium or summary.avatar,
                    "profile_url": summary.profile_url,
                },
            }
        )
