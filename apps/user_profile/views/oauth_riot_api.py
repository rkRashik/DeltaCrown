"""Riot OAuth API views for Valorant passport sign-on."""

from __future__ import annotations

import json
import logging
import secrets
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from apps.common.api_responses import error_response, success_response, validation_error_response
from apps.user_profile.services.oauth_riot_service import (
    RiotOAuthError,
    build_riot_authorization_url,
    exchange_code_for_tokens,
    fetch_userinfo,
    resolve_riot_identity,
    upsert_riot_passports,
)

logger = logging.getLogger(__name__)

STATE_CACHE_PREFIX = "riot_oauth_state:"
STATE_TTL_SECONDS = 600

VALID_RESPONSE_MODES = {"json", "redirect", "auto"}
VALID_CALLBACK_MODES = {"json", "redirect"}


def _wants_json_response(request: HttpRequest, explicit_mode: str = "auto") -> bool:
    mode = (explicit_mode or "auto").strip().lower()
    if mode == "json":
        return True
    if mode == "redirect":
        return False
    accept = (request.headers.get("Accept") or "").lower()
    return "application/json" in accept and "text/html" not in accept


def _build_settings_return_url(*, status: str, message: str = "", error_code: str = "") -> str:
    base_path = reverse("user_profile:settings")
    query = {
        "tab": "passports",
        "oauth_provider": "riot",
        "oauth_status": status,
        "oauth_game": "valorant",
    }
    if message:
        query["oauth_message"] = message
    if error_code:
        query["oauth_error"] = error_code
    return f"{base_path}?{urlencode(query)}"


@method_decorator(login_required, name="dispatch")
class RiotLoginRedirectView(View):
    """Return the Riot authorization URL for frontend redirect."""

    def get(self, request: HttpRequest) -> HttpResponse:
        response_mode = str(request.GET.get("response_mode", "auto") or "auto").strip().lower()
        raw_callback_mode = str(request.GET.get("callback_mode", "") or "").strip().lower()

        if response_mode not in VALID_RESPONSE_MODES:
            response_mode = "auto"

        wants_json = _wants_json_response(request, explicit_mode=response_mode)
        callback_mode = raw_callback_mode if raw_callback_mode in VALID_CALLBACK_MODES else ("json" if wants_json else "redirect")

        state = secrets.token_urlsafe(32)

        try:
            authorization_url = build_riot_authorization_url(state=state)
        except RiotOAuthError as exc:
            # Map status 500 → 503 for "not configured" so Django doesn't
            # treat it as a server crash (503 = service unavailable).
            http_status = exc.status_code if exc.status_code != 500 else 503
            return error_response(
                error_code=exc.error_code,
                message=exc.message,
                status=http_status,
                metadata=exc.metadata,
            )
        except Exception:
            logger.exception("[Riot OAuth] Unexpected error building authorization URL")
            return error_response(
                error_code="SERVER_ERROR",
                message="An unexpected error occurred. Please try again.",
                status=500,
            )

        # Settings are valid — only persist OAuth state after successful validation.
        cache.set(
            f"{STATE_CACHE_PREFIX}{state}",
            {
                "user_id": request.user.id,
                "callback_mode": callback_mode,
            },
            timeout=STATE_TTL_SECONDS,
        )

        if not wants_json:
            return HttpResponseRedirect(authorization_url)

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

    def get(self, request: HttpRequest) -> HttpResponse:
        return self._handle_callback(request, request.GET)

    def post(self, request: HttpRequest) -> HttpResponse:
        payload = {}
        if request.body:
            try:
                payload = json.loads(request.body)
            except json.JSONDecodeError:
                payload = {}

        if not payload:
            payload = request.POST

        return self._handle_callback(request, payload)

    def _resolve_callback_mode(self, explicit_mode: str, cached_state) -> str:
        mode = str(explicit_mode or "").strip().lower()
        if mode in VALID_CALLBACK_MODES:
            return mode
        if isinstance(cached_state, dict):
            cached_mode = str(cached_state.get("callback_mode", "")).strip().lower()
            if cached_mode in VALID_CALLBACK_MODES:
                return cached_mode
        return "json"

    def _error_response_or_redirect(
        self,
        *,
        explicit_callback_mode: str,
        cached_state,
        error_code: str,
        message: str,
        status_code: int,
        metadata=None,
    ) -> HttpResponse:
        resolved_mode = self._resolve_callback_mode(explicit_callback_mode, cached_state)
        if resolved_mode == "redirect":
            return HttpResponseRedirect(
                _build_settings_return_url(
                    status="failed",
                    message=message,
                    error_code=error_code,
                )
            )
        return error_response(error_code, message, status=status_code, metadata=metadata)

    def _handle_callback(self, request: HttpRequest, payload) -> HttpResponse:
        code = str(payload.get("code", "")).strip()
        state = str(payload.get("state", "")).strip()
        callback_mode = str(payload.get("callback_mode", "") or "").strip().lower()

        if not code:
            return self._error_response_or_redirect(
                explicit_callback_mode=callback_mode,
                cached_state=None,
                error_code="VALIDATION_ERROR",
                message="Authorization code is required",
                status_code=400,
                metadata={"field_errors": {"code": "Authorization code is required"}},
            )

        if not state:
            return self._error_response_or_redirect(
                explicit_callback_mode=callback_mode,
                cached_state=None,
                error_code="VALIDATION_ERROR",
                message="Missing OAuth state",
                status_code=400,
                metadata={"field_errors": {"state": "state is required"}},
            )

        logger.info(
            "[Riot OAuth] Callback received: user=%s code_present=%s state_present=%s callback_mode=%s",
            request.user.id if request.user.is_authenticated else "anon",
            bool(code),
            bool(state),
            callback_mode or "(none)",
        )

        cache_key = f"{STATE_CACHE_PREFIX}{state}"
        cached_state = cache.get(cache_key)
        cache.delete(cache_key)

        # Support both old format (plain user_id) and new format (dict)
        if isinstance(cached_state, dict):
            expected_user_id = cached_state.get("user_id")
        else:
            expected_user_id = cached_state
            cached_state = {"user_id": expected_user_id}

        if not expected_user_id or expected_user_id != request.user.id:
            return self._error_response_or_redirect(
                explicit_callback_mode=callback_mode,
                cached_state=cached_state,
                error_code="INVALID_OAUTH_STATE",
                message="OAuth state is invalid or has expired",
                status_code=400,
            )

        logger.info("[Riot OAuth] State validated for user=%s, exchanging code", request.user.id)
        try:
            token_data = exchange_code_for_tokens(code)
            logger.info("[Riot OAuth] Token exchange successful")
            userinfo = fetch_userinfo(token_data["access_token"])
            logger.info("[Riot OAuth] Userinfo fetched: sub=%s", userinfo.get("sub", "(missing)"))
            identity = resolve_riot_identity(userinfo, token_data["access_token"])
            logger.info("[Riot OAuth] Identity resolved: puuid=%s riot_id=%s", identity.puuid, identity.riot_id)
            results = upsert_riot_passports(
                user=request.user,
                identity=identity,
                token_data=token_data,
            )
            passport, oauth_connection, passport_created = results[0]
            logger.info(
                "[Riot OAuth] Connection saved: passport_id=%s provider_account_pk=%s created=%s",
                passport.id, oauth_connection.provider_account_id, passport_created,
            )
        except RiotOAuthError as exc:
            logger.warning("[Riot OAuth] RiotOAuthError: %s — %s (status=%s)", exc.error_code, exc.message, exc.status_code)
            return self._error_response_or_redirect(
                explicit_callback_mode=callback_mode,
                cached_state=cached_state,
                error_code=exc.error_code,
                message=exc.message,
                status_code=exc.status_code,
                metadata=exc.metadata,
            )
        except Exception as exc:
            logger.exception("Unexpected Riot OAuth callback failure: %s", exc)
            return self._error_response_or_redirect(
                explicit_callback_mode=callback_mode,
                cached_state=cached_state,
                error_code="SERVER_ERROR",
                message="Unexpected error while processing Riot callback",
                status_code=500,
            )

        resolved_mode = self._resolve_callback_mode(callback_mode, cached_state)
        if resolved_mode == "redirect":
            return HttpResponseRedirect(
                _build_settings_return_url(
                    status="connected",
                    message="Riot account connected successfully",
                )
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
