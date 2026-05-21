"""Mobile profile and game passport endpoints."""
from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated

from apps.games.models import Game
from apps.user_profile.models import GameProfile, UserProfile
from apps.user_profile.services.game_passport_service import GamePassportService

from ..base import MobileApiView
from ..responses import error_response, success_response
from .serializers import (
    MobileGamePassportSerializer,
    MobileProfilePatchSerializer,
    PROFILE_FIELDS,
    apply_profile_updates,
    serialize_game,
    serialize_passport,
    serialize_profile,
)


def _client_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",", 1)[0].strip()
    return request.META.get("REMOTE_ADDR")


def _field_error_response(details, message="Validation failed."):
    return error_response(
        "validation_error",
        message,
        details=details if isinstance(details, dict) else {"detail": details},
        status=http_status.HTTP_400_BAD_REQUEST,
    )


class MobileProfileView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfile.objects.filter(user=request.user).first()
        return success_response(serialize_profile(profile))

    def patch(self, request):
        unsafe_fields = sorted(set(request.data.keys()) - PROFILE_FIELDS)
        if unsafe_fields:
            return _field_error_response(
                {"fields": unsafe_fields},
                "One or more fields cannot be updated from mobile.",
            )

        serializer = MobileProfilePatchSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _field_error_response(serializer.errors)

        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={"display_name": request.user.username},
        )
        try:
            apply_profile_updates(profile, serializer.validated_data)
        except Exception as exc:
            details = getattr(exc, "detail", None) or getattr(exc, "message_dict", None) or str(exc)
            return _field_error_response(details)

        return success_response(serialize_profile(profile))


class MobileGamesView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        games = (
            Game.objects.filter(is_active=True, is_passport_supported=True)
            .prefetch_related("identity_configs")
            .select_related("roster_config")
            .order_by("name")
        )
        return success_response({"games": [serialize_game(game) for game in games]})


class MobileGamePassportListCreateView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        passports = (
            GameProfile.objects.filter(user=request.user)
            .select_related("game")
            .order_by("-is_pinned", "-pinned_order", "sort_order", "-updated_at")
        )
        return success_response({"game_passports": [serialize_passport(passport) for passport in passports]})

    def post(self, request):
        serializer = MobileGamePassportSerializer(data=request.data)
        if not serializer.is_valid():
            return _field_error_response(serializer.errors)

        data = serializer.validated_data
        game = data["game"]
        if GameProfile.objects.filter(user=request.user, game=game).exists():
            return error_response(
                "duplicate_passport",
                "You already have a passport for this game.",
                status=http_status.HTTP_409_CONFLICT,
            )

        try:
            with transaction.atomic():
                passport = GamePassportService.create_passport(
                    user=request.user,
                    game=game.slug,
                    ign=data.get("ign") or _derive_mobile_ign(data.get("identity_data") or {}),
                    discriminator=data.get("discriminator") or None,
                    platform=data.get("platform") or None,
                    region=data.get("region") or "",
                    metadata=data.get("identity_data") or {},
                    visibility=data.get("visibility") or GameProfile.VISIBILITY_PUBLIC,
                    actor_user_id=request.user.id,
                    request_ip=_client_ip(request),
                )
                _apply_non_identity_fields(passport, data)
        except DjangoValidationError as exc:
            return _field_error_response(getattr(exc, "message_dict", None) or {"detail": exc.messages})
        except IntegrityError:
            return error_response(
                "duplicate_identity",
                "This game identity is already linked to another account.",
                status=http_status.HTTP_409_CONFLICT,
            )

        return success_response(serialize_passport(passport), status=http_status.HTTP_201_CREATED)


class MobileGamePassportDetailView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, passport_id: int):
        passport = self._get_owned_passport(request, passport_id)
        if passport is None:
            return error_response("not_found", "Game passport not found.", status=http_status.HTTP_404_NOT_FOUND)

        payload = dict(request.data)
        payload["game_id"] = passport.game_id
        serializer = MobileGamePassportSerializer(data=payload, partial=True)
        if not serializer.is_valid():
            return _field_error_response(serializer.errors)

        data = serializer.validated_data
        identity_changed = any(field in request.data for field in ("ign", "discriminator", "platform", "region"))

        try:
            with transaction.atomic():
                if identity_changed:
                    passport = GamePassportService.update_passport_identity(
                        user=request.user,
                        game=passport.game.slug,
                        ign=data.get("ign", passport.ign),
                        discriminator=data.get("discriminator", passport.discriminator),
                        platform=data.get("platform", passport.platform),
                        region=data.get("region", passport.region),
                        reason="mobile_profile_update",
                        actor_user_id=request.user.id,
                        request_ip=_client_ip(request),
                    )
                _apply_non_identity_fields(passport, data)
        except PermissionDenied as exc:
            return error_response("permission_denied", str(exc), status=http_status.HTTP_403_FORBIDDEN)
        except DjangoValidationError as exc:
            return _field_error_response(getattr(exc, "message_dict", None) or {"detail": exc.messages})
        except IntegrityError:
            return error_response(
                "duplicate_identity",
                "This game identity is already linked to another account.",
                status=http_status.HTTP_409_CONFLICT,
            )

        passport.refresh_from_db()
        return success_response(serialize_passport(passport))

    def delete(self, request, passport_id: int):
        passport = self._get_owned_passport(request, passport_id)
        if passport is None:
            return error_response("not_found", "Game passport not found.", status=http_status.HTTP_404_NOT_FOUND)

        return error_response(
            "otp_required",
            "Game passport deletion requires the existing OTP confirmation flow.",
            details={"required_flow": "profile_game_passport_delete_otp"},
            status=http_status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def _get_owned_passport(request, passport_id: int):
        try:
            return GameProfile.objects.select_related("game").get(id=passport_id, user=request.user)
        except GameProfile.DoesNotExist:
            return None


def _apply_non_identity_fields(passport: GameProfile, data: dict) -> None:
    update_fields = []
    for field in ("rank_name", "rank_points", "rank_tier", "peak_rank", "visibility", "is_lft"):
        if field in data:
            setattr(passport, field, data[field])
            update_fields.append(field)
    if update_fields:
        passport.save(update_fields=[*update_fields, "updated_at"])


def _derive_mobile_ign(identity_data: dict) -> str | None:
    for key in (
        "riot_id",
        "ign",
        "username",
        "in_game_name",
        "player_id",
        "uid",
        "game_id",
        "steam_id",
        "steam_id64",
        "user_id",
        "ea_id",
        "epic_id",
        "codm_uid",
        "pubg_id",
        "konami_id",
    ):
        value = identity_data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return None
