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
    api_synced = serializers.SerializerMethodField()
    live_performance = serializers.SerializerMethodField()

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
            "matches_played",
            "win_rate",
            "kd_ratio",
            "main_role",
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
            "api_synced",
            "live_performance",
        ]
        read_only_fields = fields

    @staticmethod
    def _coerce_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _get_live_stats_snapshot(self, obj):
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        live_stats = metadata.get("live_stats")
        if not isinstance(live_stats, dict):
            return {}

        slug = (getattr(obj.game, "slug", "") or "").strip().lower()
        aliases = []
        if slug:
            aliases.extend(
                [
                    slug,
                    slug.replace("-", ""),
                    slug.replace("-", "_"),
                ]
            )

        for alias in aliases:
            snapshot = live_stats.get(alias)
            if isinstance(snapshot, dict):
                return snapshot

        # Fall back to first structured snapshot if slug aliases are not present.
        for value in live_stats.values():
            if isinstance(value, dict):
                return value

        return {}

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

    def get_api_synced(self, obj):
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        return bool(metadata.get("api_synced"))

    def get_live_performance(self, obj):
        metadata = obj.metadata if isinstance(obj.metadata, dict) else {}
        snapshot = self._get_live_stats_snapshot(obj)

        kd_ratio = self._coerce_float(snapshot.get("recent_kd_ratio"))
        if kd_ratio is None and obj.kd_ratio is not None:
            kd_ratio = self._coerce_float(obj.kd_ratio)

        win_rate_pct = self._coerce_float(snapshot.get("recent_win_rate_pct"))
        if win_rate_pct is None and obj.win_rate is not None:
            win_rate_pct = self._coerce_float(obj.win_rate)

        matches_played = self._coerce_int(snapshot.get("sample_size"))
        if matches_played is None:
            matches_played = self._coerce_int(obj.matches_played) or 0

        main_role = str(snapshot.get("most_played_role") or obj.main_role or "").strip()

        synced_at = snapshot.get("synced_at") or metadata.get("riot_last_match_sync_at")
        if synced_at and hasattr(synced_at, "isoformat"):
            synced_at = synced_at.isoformat()

        has_stats = bool(
            kd_ratio is not None
            or win_rate_pct is not None
            or matches_played > 0
            or main_role
            or synced_at
        )

        return {
            "sync_state": "ready" if has_stats else ("syncing" if self.get_api_synced(obj) else "manual"),
            "has_stats": has_stats,
            "source": snapshot.get("provider") or metadata.get("oauth_provider") or "manual",
            "kd_ratio": round(kd_ratio, 3) if kd_ratio is not None else None,
            "win_rate_pct": round(win_rate_pct, 2) if win_rate_pct is not None else None,
            "matches_played": matches_played,
            "main_role": main_role,
            "wins": self._coerce_int(snapshot.get("wins")),
            "losses": self._coerce_int(snapshot.get("losses")),
            "kills": self._coerce_int(snapshot.get("kills")),
            "deaths": self._coerce_int(snapshot.get("deaths")),
            "assists": self._coerce_int(snapshot.get("assists")),
            "synced_at": synced_at,
        }
