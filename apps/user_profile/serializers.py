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

    # Normalised slug (dashes stripped) → OAuth provider namespace.
    # ALL identity fields for these games are ALWAYS locked — data comes from
    # the OAuth provider; users never type them manually.
    _OAUTH_GAME_SLUGS: dict = {
        "cs2": "steam",
        "counterstrike2": "steam",
        "dota2": "steam",
        "valorant": "riot",
        "rocketleague": "epic",
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
        slug_norm = (getattr(obj.game, "slug", "") or "").strip().lower().replace("-", "")
        return {
            "id": obj.game.id,
            "name": obj.game.name,
            "slug": obj.game.slug,
            "icon": _safe_image_url(obj.game.icon),
            "api_synced": slug_norm in self._OAUTH_GAME_SLUGS,
        }

    def get_field_schema(self, obj):
        """
        Truth-table field classification.

        OAuth games (CS2 / Valorant / Dota2 / RL): ALL identity fields are
        ALWAYS locked — data arrives via the OAuth provider; users never type.
        Manual games (EA FC 26 / Free Fire / eFootball / etc.): ALL identity
        fields are USER_EDITABLE — the user enters their own game ID freely.
        Preference fields (role / region / etc.): always USER_EDITABLE.
        """
        from apps.games.models import GamePlayerIdentityConfig
        from apps.user_profile.models.game_passport_schema import GameChoiceConfig

        game_slug_norm = (getattr(obj.game, "slug", "") or "").strip().lower().replace("-", "")
        is_oauth_game = game_slug_norm in self._OAUTH_GAME_SLUGS
        oauth_provider = self._OAUTH_GAME_SLUGS.get(game_slug_norm)
        provider_data = obj.provider_data if isinstance(obj.provider_data, dict) else {}
        preferences = obj.preferences if isinstance(obj.preferences, dict) else {}

        # Use prefetch cache populated by prefetch_related('game__identity_configs',
        # 'game__passport_schema') in the view — avoids N+1 per-passport DB queries.
        choice_config = None
        try:
            choice_config = obj.game.passport_schema
        except Exception:  # noqa: BLE001
            pass

        schema_fields = []

        try:
            # .all() uses the prefetch cache; sort in Python to avoid cache bypass.
            identity_configs = sorted(
                obj.game.identity_configs.all(),
                key=lambda c: c.order,
            )
        except Exception:  # noqa: BLE001 — tolerate missing table during migration
            identity_configs = []

        for config in identity_configs:
            fname = config.field_name
            is_required = config.is_required

            # ── Truth Table ────────────────────────────────────────────────
            # is_oauth_game=True  → VERIFIED_IDENTITY, locked=True  (always)
            # is_oauth_game=False → USER_EDITABLE,     locked=False (always)
            # preference field    → PREFERENCE,        locked=False (always)
            if is_oauth_game:
                field_class = self._FC_VERIFIED_IDENTITY
                locked = True
            elif fname in preferences:
                field_class = self._FC_PREFERENCE
                locked = False
            else:
                field_class = self._FC_USER_EDITABLE
                locked = False

            # ── Value path ─────────────────────────────────────────────────
            if is_oauth_game and oauth_provider:
                value_path = f"provider_data.{oauth_provider}.{fname}"
            elif fname in preferences:
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
                "placeholder": config.placeholder or "",
                "type": (config.field_type or "text").lower(),
                "min_length": config.min_length,
                "max_length": config.max_length,
                "validation_regex": config.validation_regex or "",
            }

            # ── Dropdown choices from GameChoiceConfig ─────────────────────
            if choice_config and config.field_type and config.field_type.lower() == "select":
                fn_lower = fname.lower()
                if "region" in fn_lower:
                    entry["choices"] = choice_config.region_choices or []
                elif "rank" in fn_lower and "peak" not in fn_lower:
                    entry["choices"] = choice_config.rank_choices or []
                elif "role" in fn_lower:
                    entry["choices"] = choice_config.role_choices or []
                elif "platform" in fn_lower:
                    entry["choices"] = choice_config.platform_choices or []
                elif "server" in fn_lower:
                    entry["choices"] = choice_config.server_choices or []
                elif "mode" in fn_lower:
                    entry["choices"] = choice_config.mode_choices or []
                elif "premier" in fn_lower:
                    entry["choices"] = choice_config.premier_rating_choices or []
                elif "division" in fn_lower:
                    entry["choices"] = choice_config.division_choices or []

            schema_fields.append(entry)

        # Fallback: only for OAuth games — if no identity_configs exist yet but we have
        # provider_data, surface those fields as locked entries so the UI can display them.
        # Manual games (non-OAuth) must never be locked through this path.
        if not schema_fields and is_oauth_game:
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
                        "type": "text",
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
