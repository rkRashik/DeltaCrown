"""Serializers for mobile profile and game passport endpoints."""
from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GameProfile, UserProfile

from ..serializers import _completion_percentage


PROFILE_FIELDS = {
    "display_name",
    "real_full_name",
    "country",
    "region",
    "city",
    "date_of_birth",
    "preferred_contact_method",
}


def _safe_image_url(field) -> str | None:
    try:
        return getattr(field, "url", None) if field else None
    except Exception:
        return None


def _country_code(profile) -> str | None:
    country = getattr(profile, "country", None)
    if not country:
        return None
    return getattr(country, "code", None) or str(country)


def serialize_profile(profile) -> dict:
    pct = _completion_percentage(profile)
    if profile is None:
        return {
            "display_name": None,
            "real_full_name": None,
            "public_id": None,
            "country": None,
            "region": None,
            "city": None,
            "date_of_birth": None,
            "preferred_contact_method": None,
            "avatar_url": None,
            "profile_picture_url": None,
            "completion_percentage": 0,
            "profile_completed": False,
        }

    avatar_url = _safe_image_url(getattr(profile, "avatar", None))
    return {
        "display_name": profile.display_name or None,
        "real_full_name": getattr(profile, "real_full_name", "") or None,
        "public_id": getattr(profile, "public_id", None) or None,
        "country": _country_code(profile),
        "region": getattr(profile, "region", "") or None,
        "city": getattr(profile, "city", "") or None,
        "date_of_birth": profile.date_of_birth.isoformat() if getattr(profile, "date_of_birth", None) else None,
        "preferred_contact_method": getattr(profile, "preferred_contact_method", "") or None,
        "avatar_url": avatar_url,
        "profile_picture_url": avatar_url,
        "completion_percentage": pct,
        "profile_completed": pct >= 100,
    }


class MobileProfilePatchSerializer(serializers.Serializer):
    display_name = serializers.CharField(max_length=80, required=False, allow_blank=False)
    real_full_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    country = serializers.CharField(required=False, allow_blank=True)
    region = serializers.CharField(max_length=2, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    preferred_contact_method = serializers.ChoiceField(
        choices=[choice[0] for choice in UserProfile._meta.get_field("preferred_contact_method").choices],
        required=False,
        allow_blank=True,
    )


def serialize_identity_config(config: GamePlayerIdentityConfig) -> dict:
    return {
        "field_name": config.field_name,
        "display_name": config.display_name,
        "field_type": config.field_type,
        "required": config.is_required,
        "immutable": config.is_immutable,
        "placeholder": config.placeholder or "",
        "help_text": config.help_text or "",
        "min_length": config.min_length,
        "max_length": config.max_length,
        "validation_regex": config.validation_regex or "",
    }


def serialize_game(game: Game) -> dict:
    roster = getattr(game, "roster_config", None)
    roster_data = None
    if roster is not None:
        roster_data = {
            "min_team_size": roster.min_team_size,
            "max_team_size": roster.max_team_size,
            "min_roster_size": roster.min_roster_size,
            "max_roster_size": roster.max_roster_size,
        }

    return {
        "id": game.id,
        "name": game.display_name or game.name,
        "slug": game.slug,
        "short_code": game.short_code,
        "category": game.category,
        "platforms": game.platforms or [],
        "roster": roster_data,
        "identity_fields": [
            serialize_identity_config(config)
            for config in sorted(game.identity_configs.all(), key=lambda item: item.order)
        ],
    }


def serialize_game_summary(game: Game) -> dict:
    return {
        "id": game.id,
        "name": game.display_name or game.name,
        "slug": game.slug,
        "short_code": game.short_code,
        "category": game.category,
    }


def serialize_passport(passport: GameProfile) -> dict:
    return {
        "id": passport.id,
        "game": serialize_game_summary(passport.game),
        "ign": passport.ign,
        "discriminator": passport.discriminator,
        "tag": passport.discriminator,
        "platform": passport.platform,
        "region": passport.region,
        "rank_name": passport.rank_name,
        "rank_points": passport.rank_points,
        "rank_tier": passport.rank_tier,
        "peak_rank": passport.peak_rank,
        "identity_key": passport.identity_key,
        "visibility": passport.visibility,
        "is_lft": passport.is_lft,
        "verification_status": passport.verification_status,
        "is_verified": passport.is_verified,
    }


class MobileGamePassportSerializer(serializers.Serializer):
    game_id = serializers.IntegerField(required=True)
    ign = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    discriminator = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    platform = serializers.CharField(max_length=32, required=False, allow_blank=True, allow_null=True)
    region = serializers.CharField(max_length=10, required=False, allow_blank=True)
    rank_name = serializers.CharField(max_length=50, required=False, allow_blank=True)
    rank_points = serializers.IntegerField(required=False, allow_null=True)
    rank_tier = serializers.IntegerField(required=False)
    peak_rank = serializers.CharField(max_length=50, required=False, allow_blank=True)
    visibility = serializers.ChoiceField(
        choices=[choice[0] for choice in GameProfile.VISIBILITY_CHOICES],
        required=False,
    )
    is_lft = serializers.BooleanField(required=False)
    identity_fields = serializers.DictField(required=False)
    metadata = serializers.DictField(required=False)

    def validate(self, attrs):
        try:
            game = Game.objects.get(id=attrs["game_id"], is_active=True, is_passport_supported=True)
        except Game.DoesNotExist as exc:
            raise serializers.ValidationError({"game_id": "Active passport-supported game not found."}) from exc

        attrs["game"] = game
        identity_data = {}
        identity_data.update(attrs.get("metadata") or {})
        identity_data.update(attrs.get("identity_fields") or {})
        for field in ("ign", "discriminator", "platform", "region"):
            if field in attrs and attrs[field] not in (None, ""):
                identity_data[field] = attrs[field]

        field_errors = {}
        for config in GamePlayerIdentityConfig.objects.filter(game=game).order_by("order", "id"):
            value = identity_data.get(config.field_name)
            is_valid, message = config.validate_value(value)
            if not is_valid:
                field_errors[config.field_name] = message

        if field_errors:
            raise serializers.ValidationError(field_errors)

        attrs["identity_data"] = identity_data
        return attrs


def apply_profile_updates(profile: UserProfile, validated_data: dict) -> None:
    for field, value in validated_data.items():
        setattr(profile, field, value)
    try:
        profile.full_clean(exclude=["user", "uuid", "public_id", "slug"])
    except DjangoValidationError as exc:
        raise serializers.ValidationError(getattr(exc, "message_dict", None) or {"detail": exc.messages}) from exc
    profile.save(update_fields=[*validated_data.keys(), "updated_at"])
