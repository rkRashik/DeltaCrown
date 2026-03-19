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
    field_schema = serializers.SerializerMethodField()

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
            "provider_data",
            "preferences",
            "passport_data",
            "locked_until",
            "is_locked",
            "days_locked",
            "verification_status",
            "is_verified",
            "cooldown",
            "api_synced",
            "live_performance",
            "field_schema",
        ]
        read_only_fields = fields

    # ── Field class constants (consumed by the frontend renderer) ────────────
    _FC_VERIFIED_IDENTITY = "VERIFIED_IDENTITY"   # Set by OAuth; never user-editable
    _FC_API_SYNCED        = "API_SYNCED"           # Refreshed by sync jobs; display-only
    _FC_PREFERENCE        = "PREFERENCE"           # User-controlled dropdown
    _FC_USER_EDITABLE     = "USER_EDITABLE"        # Free-text user input

    # Provider-owned keys that map directly into provider_data namespaces.
    # Any field whose DB name appears here is treated as VERIFIED_IDENTITY.
    _PROVIDER_IDENTITY_KEYS = {
        "steam": {"steam_id", "persona_name", "avatar", "avatar_medium", "avatar_full", "profile_url"},
        "riot":  {"puuid", "game_name", "tag_line", "summoner_id", "account_id", "region_shard"},
        "epic":  {"account_id", "display_name", "epic_id"},
    }

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

    def get_field_schema(self, obj):
        """
        Phase 1 Dynamic Schema — data-driven field classification.

        Returns a list of field descriptors so the frontend renderer never
        needs to hard-code which fields are locked vs. editable.  Driven by
        ``GamePlayerIdentityConfig`` rows for the passport's game plus the
        presence of data in ``provider_data`` namespaces.

        Field classes:
          VERIFIED_IDENTITY  — set by OAuth; padlock badge, never editable
          API_SYNCED         — refreshed by sync jobs; cloud-sync badge
          PREFERENCE         — user-controlled dropdown
          USER_EDITABLE      — free-text user input
        """
        from apps.games.models import GamePlayerIdentityConfig

        game_slug = (getattr(obj.game, "slug", "") or "").strip().lower()
        provider_data = obj.provider_data if isinstance(obj.provider_data, dict) else {}
        preferences = obj.preferences if isinstance(obj.preferences, dict) else {}

        # Collect all provider-owned field names that have live data
        verified_field_names: set[str] = set()
        for provider_key, owned_keys in self._PROVIDER_IDENTITY_KEYS.items():
            if provider_data.get(provider_key):
                verified_field_names.update(owned_keys)

        schema_fields = []

        try:
            identity_configs = list(
                GamePlayerIdentityConfig.objects.filter(game=obj.game).order_by("order")
            )
        except Exception:  # noqa: BLE001 — tolerate missing table during migration
            identity_configs = []

        for config in identity_configs:
            fname = config.field_name
            is_immutable = config.is_immutable
            is_required = config.is_required

            # Determine field class
            if fname in verified_field_names or is_immutable:
                field_class = self._FC_VERIFIED_IDENTITY
                locked = True
            elif fname in preferences:
                field_class = self._FC_PREFERENCE
                locked = False
            else:
                field_class = self._FC_USER_EDITABLE
                locked = False

            # Determine which zone holds the current value
            value_path = None
            for provider_key, owned_keys in self._PROVIDER_IDENTITY_KEYS.items():
                if fname in owned_keys and provider_data.get(provider_key):
                    value_path = f"provider_data.{provider_key}.{fname}"
                    break
            if value_path is None:
                if fname in preferences:
                    value_path = f"preferences.{fname}"
                else:
                    value_path = f"metadata.{fname}"

            entry: dict = {
                "field_name": fname,
                "display_name": config.display_name,
                "field_class": field_class,
                "locked": locked,
                "required": is_required,
                "value_path": value_path,
                "help_text": config.help_text or "",
            }

            # Attach choices for PREFERENCE / USER_EDITABLE selects
            if hasattr(config, "choices") and config.choices:
                entry["choices"] = config.choices

            schema_fields.append(entry)

        # If no schema rows exist yet, emit a minimal entry for each known
        # provider_data key so the frontend still knows what to lock.
        if not schema_fields:
            for provider_key, provider_ns in provider_data.items():
                if not isinstance(provider_ns, dict):
                    continue
                for key in provider_ns:
                    if key == "synced_at":
                        continue
                    schema_fields.append({
                        "field_name": key,
                        "display_name": key.replace("_", " ").title(),
                        "field_class": self._FC_VERIFIED_IDENTITY,
                        "locked": True,
                        "required": False,
                        "value_path": f"provider_data.{provider_key}.{key}",
                        "help_text": f"Verified by {provider_key.title()}.",
                    })

        return schema_fields

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
