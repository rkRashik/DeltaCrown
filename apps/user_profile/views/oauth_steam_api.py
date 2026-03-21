"""Steam OpenID API views for CS2 and Dota 2 passport linking."""

from __future__ import annotations

import logging
import secrets
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from apps.common.api_responses import error_response, success_response
from apps.user_profile.services.oauth_steam_service import (
    SteamOpenIDError,
    build_steam_openid_redirect_url,
    fetch_player_summary,
    upsert_steam_passports,
    verify_steam_callback,
)

logger = logging.getLogger(__name__)

STATE_CACHE_PREFIX = "steam_openid_state:"
STATE_TTL_SECONDS = 600

VALID_RESPONSE_MODES = {"json", "redirect", "auto"}
VALID_CALLBACK_MODES = {"json", "redirect"}


def _wants_json_response(request: HttpRequest, explicit_mode: str = "auto") -> bool:
    mode = (explicit_mode or "auto").strip().lower()
    if mode == "json":
        return True
    if mode == "redirect":
        return False

    # Auto-mode: API callers usually send application/json while normal browser
    # navigation carries text/html in the Accept header.
    accept = (request.headers.get("Accept") or "").lower()
    return "application/json" in accept and "text/html" not in accept


def _build_settings_return_url(*, status: str, message: str = "", error_code: str = "") -> str:
    base_path = reverse("user_profile:settings")
    query = {
        "tab": "passports",
        "oauth_provider": "steam",
        "oauth_status": status,
    }
    if message:
        query["oauth_message"] = message
    if error_code:
        query["oauth_error"] = error_code
    return f"{base_path}?{urlencode(query)}"


@method_decorator(login_required, name="dispatch")
class SteamLoginRedirectView(View):
    """Return the Steam OpenID redirect URL for frontend redirect."""

    def get(self, request: HttpRequest) -> HttpResponse:
        response_mode = str(request.GET.get("response_mode", "json") or "json").strip().lower()
        raw_callback_mode = str(request.GET.get("callback_mode", "") or "").strip().lower()

        if response_mode not in VALID_RESPONSE_MODES:
            response_mode = "auto"

        wants_json = _wants_json_response(request, explicit_mode=response_mode)
        callback_mode = (
            raw_callback_mode if raw_callback_mode in VALID_CALLBACK_MODES
            else ("json" if wants_json else "redirect")
        )

        state = secrets.token_urlsafe(32)
        cache.set(
            f"{STATE_CACHE_PREFIX}{state}",
            {
                "user_id": request.user.id,
                "callback_mode": callback_mode,
            },
            timeout=STATE_TTL_SECONDS,
        )

        callback_url = request.build_absolute_uri(reverse("user_profile:steam_openid_callback"))
        return_to = f"{callback_url}?{urlencode({'state': state})}"
        realm = f"{request.scheme}://{request.get_host()}"
        authorization_url = build_steam_openid_redirect_url(return_to=return_to, realm=realm)

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
class SteamCallbackView(View):
    """Verify Steam OpenID callback and connect a Steam game passport."""

    def get(self, request: HttpRequest) -> HttpResponse:
        from django.conf import settings as django_settings

        state = str(request.GET.get("state", "")).strip()
        callback_mode = str(request.GET.get("callback_mode", "") or "").strip().lower()

        # ── PROBE 0: Log every incoming callback unconditionally ──────────
        logger.error(
            "[Steam OpenID] PROBE-0 callback hit: user=%s user_auth=%s "
            "state=%r has_claimed_id=%s has_openid_mode=%s url_path=%s",
            request.user.id if request.user.is_authenticated else "anon",
            request.user.is_authenticated,
            state[:8] + "…" if len(state) > 8 else state,
            bool(request.GET.get("openid.claimed_id")),
            request.GET.get("openid.mode"),
            request.path,
        )

        def _resolve_callback_mode(cached_data):
            if callback_mode in VALID_CALLBACK_MODES:
                return callback_mode
            if cached_data and cached_data.get("callback_mode") in VALID_CALLBACK_MODES:
                return cached_data.get("callback_mode")
            return "json"

        def _error_response_or_redirect(*, error_code: str, message: str, status: int = 400, metadata=None, cached_data=None):
            resolved_mode = _resolve_callback_mode(cached_data)
            logger.error(
                "[Steam OpenID] ERROR → code=%s message=%r resolved_mode=%s user=%s",
                error_code, message, resolved_mode,
                request.user.id if request.user.is_authenticated else "anon",
            )
            if resolved_mode == "redirect":
                return HttpResponseRedirect(
                    _build_settings_return_url(
                        status="failed",
                        message=message,
                        error_code=error_code,
                    )
                )
            return error_response(error_code=error_code, message=message, status=status, metadata=metadata)

        if not state:
            return _error_response_or_redirect(
                error_code="MISSING_OPENID_STATE",
                message="Missing OpenID state",
                status=400,
                metadata={"field_errors": {"state": "state is required"}},
            )

        cache_key = f"{STATE_CACHE_PREFIX}{state}"
        cached = cache.get(cache_key)
        cache.delete(cache_key)

        # ── PROBE 1: State cache lookup result ────────────────────────────
        logger.error(
            "[Steam OpenID] PROBE-1 state check: cache_hit=%s "
            "cached_user=%s request_user=%s",
            cached is not None,
            (cached or {}).get("user_id"),
            request.user.id if request.user.is_authenticated else "anon",
        )

        if not cached or cached.get("user_id") != request.user.id:
            return _error_response_or_redirect(
                error_code="INVALID_OPENID_STATE",
                message="Steam OpenID state is invalid or has expired",
                status=400,
                cached_data=cached,
            )

        # ── PROBE 2: API key presence check ──────────────────────────────
        steam_api_key = getattr(django_settings, "STEAM_API_KEY", "").strip()
        logger.error(
            "[Steam OpenID] PROBE-2 config: STEAM_API_KEY_present=%s user=%s",
            bool(steam_api_key),
            request.user.id,
        )

        logger.info(
            "[Steam OpenID] Callback received: user=%s state_present=%s openid_params=%s",
            request.user.id if request.user.is_authenticated else "anon",
            bool(state),
            bool(request.GET.get("openid.claimed_id")),
        )
        try:
            steam_id = verify_steam_callback(request.GET.dict())
            logger.error("[Steam OpenID] PROBE-3 signature verified: steam_id=%s", steam_id)
            summary = fetch_player_summary(steam_id)
            logger.error(
                "[Steam OpenID] PROBE-4 player summary OK: persona=%s steam_id=%s",
                summary.personaname, summary.steam_id,
            )
            results = upsert_steam_passports(user=request.user, summary=summary)
            logger.error(
                "[Steam OpenID] PROBE-5 upsert done: linked_games=%s",
                [p.game.slug for p, _, _ in results],
            )
        except SteamOpenIDError as exc:
            logger.error(
                "[Steam OpenID] SteamOpenIDError: code=%s message=%r status=%s metadata=%s",
                exc.error_code, exc.message, exc.status_code, exc.metadata,
            )
            return _error_response_or_redirect(
                error_code=exc.error_code,
                message=exc.message,
                status=exc.status_code,
                metadata=exc.metadata,
                cached_data=cached,
            )
        except Exception as exc:
            logger.exception("[Steam OpenID] UNEXPECTED exception in callback: %s", exc)
            return _error_response_or_redirect(
                error_code="SERVER_ERROR",
                message="Unexpected error while processing Steam callback",
                status=500,
                cached_data=cached,
            )

        # ── PROBE-6: Success path reached ────────────────────────────────
        logger.error("[Steam OpenID] PROBE-6 SUCCESS: linked=%s mode=%s", len(results), _resolve_callback_mode(cached))

        resolved_mode = _resolve_callback_mode(cached)
        if resolved_mode == "redirect":
            if not results:
                return HttpResponseRedirect(
                    _build_settings_return_url(
                        status="warning",
                        message="Steam connected successfully, but we did not find supported games (CS2/Dota 2) in your library.",
                    )
                )
                return HttpResponseRedirect(
                _build_settings_return_url(
                    status="connected",
                    message=(
                        f"Steam account connected — {len(results)} game(s) linked"
                        if len(results) != 1
                        else "Steam account connected successfully"
                    ),
                )
            )

        passports_data = [
            {
                "id": passport.id,
                "game_slug": passport.game.slug,
                "ign": passport.ign,
                "identity_key": passport.identity_key,
                "created": created,
            }
            for passport, _, created in results
        ]
        return success_response(
            {
                "message": f"Steam account linked — {len(results)} game passport(s) updated",
                "provider": "steam",
                "provider_account_id": summary.steam_id,
                "passports": passports_data,
                "steam_profile": {
                    "steam_id": summary.steam_id,
                    "personaname": summary.personaname,
                    "avatar": summary.avatar_full or summary.avatar_medium or summary.avatar,
                    "profile_url": summary.profile_url,
                },
            }
        )


        # ── PROBE 0: Log every incoming callback unconditionally ──────────
        logger.error(
            "[Steam OpenID] PROBE-0 callback hit: user=%s user_auth=%s "
            "state=%r game=%r has_claimed_id=%s has_openid_mode=%s url_path=%s",
            request.user.id if request.user.is_authenticated else "anon",
            request.user.is_authenticated,
            state[:8] + "…" if len(state) > 8 else state,
            game_slug,
            bool(request.GET.get("openid.claimed_id")),
            request.GET.get("openid.mode"),
            request.path,
        )

        def _resolve_callback_mode(cached_data):
            if callback_mode in VALID_CALLBACK_MODES:
                return callback_mode
            if cached_data and cached_data.get("callback_mode") in VALID_CALLBACK_MODES:
                return cached_data.get("callback_mode")
            return "json"

        def _error_response_or_redirect(*, error_code: str, message: str, status: int = 400, metadata=None, cached_data=None):
            resolved_mode = _resolve_callback_mode(cached_data)
            logger.error(
                "[Steam OpenID] ERROR → code=%s message=%r resolved_mode=%s user=%s game=%s",
                error_code, message, resolved_mode,
                request.user.id if request.user.is_authenticated else "anon",
                game_slug,
            )
            if resolved_mode == "redirect":
                target_slug = game_slug or (cached_data or {}).get("game_slug") or "cs2"
                return HttpResponseRedirect(
                    _build_settings_return_url(
                        game_slug=target_slug,
                        status="failed",
                        message=message,
                        error_code=error_code,
                    )
                )
            return error_response(error_code=error_code, message=message, status=status, metadata=metadata)

        if not state:
            return _error_response_or_redirect(
                error_code="MISSING_OPENID_STATE",
                message="Missing OpenID state",
                status=400,
                metadata={"field_errors": {"state": "state is required"}},
            )

        try:
            game_slug = validate_game_slug(game_slug)
        except SteamOpenIDError as exc:
            return _error_response_or_redirect(
                error_code=exc.error_code,
                message=exc.message,
                status=exc.status_code,
                metadata=exc.metadata,
            )

        cache_key = f"{STATE_CACHE_PREFIX}{state}"
        cached = cache.get(cache_key)
        cache.delete(cache_key)

        # ── PROBE 1: State cache lookup result ────────────────────────────
        logger.error(
            "[Steam OpenID] PROBE-1 state check: cache_hit=%s "
            "cached_user=%s request_user=%s cached_game=%s param_game=%s",
            cached is not None,
            (cached or {}).get("user_id"),
            request.user.id if request.user.is_authenticated else "anon",
            (cached or {}).get("game_slug"),
            game_slug,
        )

        if not cached or cached.get("user_id") != request.user.id or cached.get("game_slug") != game_slug:
            return _error_response_or_redirect(
                error_code="INVALID_OPENID_STATE",
                message="Steam OpenID state is invalid or has expired",
                status=400,
                cached_data=cached,
            )

        # ── PROBE 2: API key presence check ──────────────────────────────
        steam_api_key = getattr(django_settings, "STEAM_API_KEY", "").strip()
        logger.error(
            "[Steam OpenID] PROBE-2 config: STEAM_API_KEY_present=%s game=%s user=%s",
            bool(steam_api_key),
            game_slug,
            request.user.id,
        )

        logger.info(
            "[Steam OpenID] Callback received: user=%s game=%s state_present=%s openid_params=%s",
            request.user.id if request.user.is_authenticated else "anon",
            game_slug,
            bool(state),
            bool(request.GET.get("openid.claimed_id")),
        )
        try:
            steam_id = verify_steam_callback(request.GET.dict())
            logger.error("[Steam OpenID] PROBE-3 signature verified: steam_id=%s", steam_id)
            summary = fetch_player_summary(steam_id)
            logger.error(
                "[Steam OpenID] PROBE-4 player summary OK: persona=%s steam_id=%s",
                summary.personaname, summary.steam_id,
            )
            passport, oauth_connection, passport_created = upsert_steam_connection(
                user=request.user,
                game_slug=game_slug,
                summary=summary,
            )
            logger.error(
                "[Steam OpenID] PROBE-5 upsert done: passport_id=%s game=%s created=%s",
                passport.id, game_slug, passport_created,
            )
        except SteamOpenIDError as exc:
            logger.error(
                "[Steam OpenID] SteamOpenIDError: code=%s message=%r status=%s metadata=%s",
                exc.error_code, exc.message, exc.status_code, exc.metadata,
            )
            return _error_response_or_redirect(
                error_code=exc.error_code,
                message=exc.message,
                status=exc.status_code,
                metadata=exc.metadata,
                cached_data=cached,
            )
        except Exception as exc:
            logger.exception("[Steam OpenID] UNEXPECTED exception in callback: %s", exc)
            return _error_response_or_redirect(
                error_code="SERVER_ERROR",
                message="Unexpected error while processing Steam callback",
                status=500,
                cached_data=cached,
            )
        # ── PROBE-6: Success path reached ────────────────────────────────
        logger.error("[Steam OpenID] PROBE-6 SUCCESS: dispatching response mode=%s", _resolve_callback_mode(cached))

        resolved_mode = _resolve_callback_mode(cached)
        if resolved_mode == "redirect":
            return HttpResponseRedirect(
                _build_settings_return_url(
                    game_slug=game_slug,
                    status="connected",
                    message="Steam account connected successfully",
                )
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
