"""Riot OAuth API views for Valorant passport sign-on."""

from __future__ import annotations

import json
import logging
import secrets

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View

from apps.common.api_responses import error_response, success_response, validation_error_response
from apps.user_profile.services.oauth_riot_service import (
    RiotOAuthError,
    build_riot_authorization_url,
    exchange_code_for_tokens,
    fetch_userinfo,
    resolve_riot_identity,
    upsert_riot_connection,
)

logger = logging.getLogger(__name__)

STATE_CACHE_PREFIX = "riot_oauth_state:"
STATE_TTL_SECONDS = 600


@method_decorator(login_required, name="dispatch")
class RiotLoginRedirectView(View):
    """Return the Riot authorization URL for frontend redirect."""

    def get(self, request: HttpRequest) -> JsonResponse:
        state = secrets.token_urlsafe(32)
        cache.set(f"{STATE_CACHE_PREFIX}{state}", request.user.id, timeout=STATE_TTL_SECONDS)

        try:
            authorization_url = build_riot_authorization_url(state=state)
        except RiotOAuthError as exc:
            return error_response(
                error_code=exc.error_code,
                message=exc.message,
                status=exc.status_code,
                metadata=exc.metadata,
            )

        return success_response(
            {
                "authorization_url": authorization_url,
                "state": state,
                "expires_in_seconds": STATE_TTL_SECONDS,
            }
        )


@method_decorator(login_required, name="dispatch")
class RiotCallbackView(View):
    """Handle Riot OAuth callback and connect the account to Valorant passport."""

    def get(self, request: HttpRequest) -> JsonResponse:
        return self._handle_callback(request, request.GET)

    def post(self, request: HttpRequest) -> JsonResponse:
        payload = {}
        if request.body:
            try:
                payload = json.loads(request.body)
            except json.JSONDecodeError:
                payload = {}

        if not payload:
            payload = request.POST

        return self._handle_callback(request, payload)

    def _handle_callback(self, request: HttpRequest, payload) -> JsonResponse:
        code = str(payload.get("code", "")).strip()
        state = str(payload.get("state", "")).strip()

        if not code:
            return validation_error_response(
                field_errors={"code": "Authorization code is required"},
                message="Authorization code is required",
            )

        if not state:
            return validation_error_response(
                field_errors={"state": "state is required"},
                message="Missing OAuth state",
            )

        cache_key = f"{STATE_CACHE_PREFIX}{state}"
        expected_user_id = cache.get(cache_key)
        cache.delete(cache_key)

        if not expected_user_id or expected_user_id != request.user.id:
            return error_response(
                error_code="INVALID_OAUTH_STATE",
                message="OAuth state is invalid or has expired",
                status=400,
            )

        try:
            token_data = exchange_code_for_tokens(code)
            userinfo = fetch_userinfo(token_data["access_token"])
            identity = resolve_riot_identity(userinfo, token_data["access_token"])
            passport, oauth_connection, passport_created = upsert_riot_connection(
                user=request.user,
                identity=identity,
                token_data=token_data,
            )
        except RiotOAuthError as exc:
            return error_response(
                error_code=exc.error_code,
                message=exc.message,
                status=exc.status_code,
                metadata=exc.metadata,
            )
        except Exception as exc:
            logger.exception("Unexpected Riot OAuth callback failure: %s", exc)
            return error_response(
                error_code="SERVER_ERROR",
                message="Unexpected error while processing Riot callback",
                status=500,
            )

        return success_response(
            {
                "message": "Riot account connected successfully",
                "provider": oauth_connection.provider,
                "provider_account_id": oauth_connection.provider_account_id,
                "passport": {
                    "id": passport.id,
                    "game_slug": passport.game.slug,
                    "ign": passport.ign,
                    "discriminator": passport.discriminator,
                    "identity_key": passport.identity_key,
                    "created": passport_created,
                },
            }
        )
