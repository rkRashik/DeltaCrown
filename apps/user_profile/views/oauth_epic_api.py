"""Epic Games OAuth API views for Rocket League linking."""

from __future__ import annotations

import json
import logging
import secrets

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from apps.common.api_responses import error_response, success_response, validation_error_response
from apps.user_profile.services.oauth_epic_service import (
    EpicOAuthError,
    build_epic_authorization_url,
    exchange_code_for_tokens,
    upsert_epic_connection,
)

logger = logging.getLogger(__name__)

STATE_CACHE_PREFIX = "epic_oauth_state:"
STATE_TTL_SECONDS = 600


@method_decorator(login_required, name="dispatch")
class EpicLoginRedirectView(View):
    def get(self, request: HttpRequest) -> JsonResponse:
        state = secrets.token_urlsafe(32)
        cache.set(f"{STATE_CACHE_PREFIX}{state}", request.user.id, timeout=STATE_TTL_SECONDS)
        redirect_uri = request.build_absolute_uri(reverse("user_profile:epic_oauth_callback"))

        try:
            authorization_url = build_epic_authorization_url(state=state, redirect_uri=redirect_uri)
        except EpicOAuthError as exc:
            return error_response(exc.error_code, exc.message, status=exc.status_code, metadata=exc.metadata)

        return success_response(
            {
                "authorization_url": authorization_url,
                "state": state,
                "expires_in_seconds": STATE_TTL_SECONDS,
            }
        )


@method_decorator(login_required, name="dispatch")
class EpicCallbackView(View):
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
            return validation_error_response({"code": "Authorization code is required"}, "Authorization code is required")
        if not state:
            return validation_error_response({"state": "state is required"}, "Missing OAuth state")

        cache_key = f"{STATE_CACHE_PREFIX}{state}"
        expected_user_id = cache.get(cache_key)
        cache.delete(cache_key)
        if not expected_user_id or expected_user_id != request.user.id:
            return error_response("INVALID_OAUTH_STATE", "OAuth state is invalid or has expired", status=400)

        redirect_uri = request.build_absolute_uri(reverse("user_profile:epic_oauth_callback"))
        try:
            token_data = exchange_code_for_tokens(code=code, redirect_uri=redirect_uri)
            passport, oauth_connection, passport_created = upsert_epic_connection(
                user=request.user,
                token_data=token_data,
            )
        except EpicOAuthError as exc:
            return error_response(exc.error_code, exc.message, status=exc.status_code, metadata=exc.metadata)
        except Exception as exc:
            logger.exception("Unexpected Epic OAuth callback failure: %s", exc)
            return error_response("SERVER_ERROR", "Unexpected error while processing Epic callback", status=500)

        return success_response(
            {
                "message": "Epic account connected successfully",
                "provider": oauth_connection.provider,
                "provider_account_id": oauth_connection.provider_account_id,
                "passport": {
                    "id": passport.id,
                    "game_slug": passport.game.slug,
                    "ign": passport.ign,
                    "identity_key": passport.identity_key,
                    "created": passport_created,
                },
            }
        )