"""DRF serializers for user profile domain models."""

from django.utils import timezone
from rest_framework import serializers

from apps.user_profile.models import GameProfile


def _safe_image_url(field):
    try:
        return getattr(field, "url", None) if field else None
    except Exception:
        return None


class GameProfileSerializer(serializers.ModelSerializer):
    game_id = serializers.IntegerField(source="game.id", read_only=True)
    game = serializers.SerializerMethodField()
    rank = serializers.CharField(source="rank_name", read_only=True)
    pinned = serializers.BooleanField(source="is_pinned", read_only=True)
    passport_data = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    days_locked = serializers.SerializerMethodField()
    cooldown = serializers.SerializerMethodField()

    class Meta:
        model = GameProfile
        fields = [
            "id",
            "game_id",
            "game",
            "ign",
            "discriminator",
            "platform",
            "region",
            "rank_name",
            "rank",
            "is_pinned",
            "pinned",
            "visibility",
            "metadata",
            "passport_data",
            "locked_until",
            "is_locked",
            "days_locked",
            "verification_status",
            "is_verified",
            "cooldown",
        ]
        read_only_fields = fields

    def get_game(self, obj):
        return {
            "id": obj.game.id,
            "name": obj.game.name,
            "slug": obj.game.slug,
            "icon": _safe_image_url(obj.game.icon),
        }

    def get_passport_data(self, obj):
        return obj.metadata or {}

    def get_is_locked(self, obj):
        return bool(obj.locked_until and obj.locked_until > timezone.now())

    def get_days_locked(self, obj):
        if not obj.locked_until or obj.locked_until <= timezone.now():
            return 0
        return (obj.locked_until - timezone.now()).days + 1

    def get_cooldown(self, obj):
        cooldown_map = self.context.get("cooldown_map", {})
        return cooldown_map.get(obj.id)
