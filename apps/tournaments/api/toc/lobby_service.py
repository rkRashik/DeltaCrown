"""
TOC Lobby / Server Management Service — Sprint 28.

Server pool management, lobby lifecycle, anti-cheat status,
region preferences, spectator slots, and match room chat.
"""

import logging
import secrets
from django.utils import timezone

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.match import Match

logger = logging.getLogger("toc.lobby")


class TOCLobbyService:
    """All read/write operations for the Lobby / Server Management tab."""

    @staticmethod
    def get_lobby_dashboard(tournament: Tournament) -> dict:
        """Full lobby management dashboard."""
        config = tournament.config or {}
        lobby_config = config.get("lobby", {})
        servers = lobby_config.get("servers", [])

        # Get matches needing lobbies
        active_matches = Match.objects.filter(
            tournament=tournament,
            state__in=["scheduled", "check_in", "ready", "live"],
        ).order_by("scheduled_time")

        match_lobbies = []
        for m in active_matches:
            lobby_info_raw = m.lobby_info or {}
            match_lobbies.append({
                "match_id": m.id,
                "match_number": m.match_number,
                "round": m.round_number,
                "state": m.state,
                "p1": m.participant1_name or "TBD",
                "p2": m.participant2_name or "TBD",
                "participant1_name": m.participant1_name or "TBD",
                "participant2_name": m.participant2_name or "TBD",
                "scheduled_time": m.scheduled_time.isoformat() if m.scheduled_time else None,
                "lobby_code": lobby_info_raw.get("code", ""),
                "server_id": lobby_info_raw.get("server_id", ""),
                "region": lobby_info_raw.get("region", ""),
                "lobby_status": lobby_info_raw.get("status", "not_created"),
                "spectator_slots": lobby_info_raw.get("spectator_slots", 0),
                "chat": lobby_info_raw.get("chat", []),
                # Nested lobby_info for JS compatibility
                "lobby_info": {
                    "lobby_code": lobby_info_raw.get("code", ""),
                    "server_id": lobby_info_raw.get("server_id", ""),
                    "region": lobby_info_raw.get("region", ""),
                    "status": lobby_info_raw.get("status", "not_created"),
                },
            })

        # Server pool summary
        active_servers = [
            s for s in servers
            if str(s.get("status", "")).lower() in {"online", "ready", "available", "in_use", "busy", "active"}
        ]
        idle_servers = [
            s for s in servers
            if str(s.get("status", "")).lower() in {"idle", "available", "ready"}
        ]

        # ── Game-aware match-flow settings (single source of truth) ────────
        # Merge values from `tournament.config['lobby']` (lobby section) and
        # `tournament.config['lobby_policy']` (already used by registration).
        # Returns a flat config dict the FE renders directly.
        lobby_policy = config.get("lobby_policy", {}) if isinstance(config.get("lobby_policy"), dict) else {}

        # Per-game capabilities to know what controls are even applicable.
        try:
            from apps.tournaments.api.toc.settings_service import TOCSettingsService
            capabilities = TOCSettingsService._lobby_capabilities_for_tournament(tournament)
        except Exception:
            capabilities = {}

        # Veto timer defaults — pulled from VetoConfiguration if available, else fall back.
        veto_seconds_default = 30
        veto_auto_pick_default = True
        try:
            game = getattr(tournament, "game", None)
            if game is not None:
                from apps.games.models.rules import VetoConfiguration
                veto_cfg = (
                    VetoConfiguration.objects
                    .filter(game=game, is_active=True)
                    .order_by("-priority")
                    .first()
                )
                if veto_cfg:
                    veto_seconds_default = int(veto_cfg.time_per_action_seconds or 30)
                    veto_auto_pick_default = bool(veto_cfg.auto_random_on_timeout)
        except Exception:
            pass

        coin_toss_actor = str(lobby_config.get("coin_toss_actor", "host")).lower()
        if coin_toss_actor not in ("host", "either", "staff"):
            coin_toss_actor = "host"

        credentials_owner = str(
            lobby_policy.get("credential_policy")
            or lobby_config.get("credentials_owner")
            or "host"
        ).lower()
        if credentials_owner not in ("host", "organizer", "staff"):
            credentials_owner = "host"

        result_submission_policy = str(lobby_config.get("result_submission_policy", "any_participant")).lower()
        if result_submission_policy not in ("any_participant", "host_first", "winner_only"):
            result_submission_policy = "any_participant"

        return {
            "servers": servers,
            "matches": match_lobbies,
            "config": {
                # Existing knobs (preserved for backward-compat)
                "auto_create": lobby_config.get("auto_create", False),
                "default_region": lobby_config.get("default_region", ""),
                "spectator_slots_default": lobby_config.get("spectator_slots_default", 2),
                "anticheat_required": lobby_config.get("anticheat_required", False),
                "chat_enabled": lobby_config.get("chat_enabled", True),
                "auto_close_minutes": lobby_config.get("auto_close_minutes", 0),
                # ── Coin toss ────────────────────────────────────────────
                "require_coin_toss": bool(lobby_policy.get("require_coin_toss", capabilities.get("default_require_coin_toss", True))),
                "coin_toss_actor": coin_toss_actor,
                # ── Map veto ─────────────────────────────────────────────
                "require_map_veto": bool(lobby_policy.get("require_map_veto", capabilities.get("default_require_map_veto", True))),
                "map_veto_seconds": int(lobby_config.get("map_veto_seconds", veto_seconds_default)),
                "map_veto_auto_pick": bool(lobby_config.get("map_veto_auto_pick", veto_auto_pick_default)),
                # ── Credentials ──────────────────────────────────────────
                "credentials_owner": credentials_owner,
                # ── Result submission ────────────────────────────────────
                "require_match_evidence": bool(lobby_policy.get("require_match_evidence", False)),
                "result_submission_policy": result_submission_policy,
                # ── Lobby window ─────────────────────────────────────────
                "lobby_open_minutes_before": int(lobby_config.get("lobby_open_minutes_before", 30)),
                "lobby_close_minutes_after": int(lobby_config.get("lobby_close_minutes_after", 10)),
            },
            "capabilities": {
                "supports_coin_toss": bool(capabilities.get("supports_coin_toss", True)),
                "supports_map_veto": bool(capabilities.get("supports_map_veto", True)),
                "phase_mode": str(capabilities.get("phase_mode", "veto")),
            },
            "summary": {
                "total_servers": len(servers),
                "online_servers": len(active_servers),
                "idle_servers": len(idle_servers),
                "matches_needing_lobby": len([m for m in match_lobbies if m["lobby_status"] == "not_created"]),
                "pending": len([m for m in match_lobbies if m["lobby_status"] == "not_created"]),
                "active_lobbies": len([m for m in match_lobbies if m["lobby_status"] == "active"]),
                "completed": len([m for m in match_lobbies if m["lobby_status"] == "completed"]),
            },
        }

    @staticmethod
    def add_server(tournament: Tournament, data: dict) -> dict:
        """Add a server to the pool."""
        config = tournament.config or {}
        lobby = config.get("lobby", {})
        servers = lobby.get("servers", [])

        server = {
            "id": f"srv-{secrets.token_hex(4)}",
            "name": data.get("name", f"Server {len(servers) + 1}"),
            "region": data.get("region", ""),
            "ip": data.get("ip", ""),
            "port": data.get("port", ""),
            "capacity": data.get("capacity", 10),
            "status": "idle",
            "game_type": data.get("game_type", ""),
            "created_at": timezone.now().isoformat(),
        }
        servers.append(server)
        lobby["servers"] = servers
        config["lobby"] = lobby
        tournament.config = config
        tournament.save(update_fields=["config"])
        return server

    @staticmethod
    def update_server(tournament: Tournament, server_id: str, data: dict) -> dict:
        """Update a server in the pool."""
        config = tournament.config or {}
        lobby = config.get("lobby", {})
        servers = lobby.get("servers", [])

        for s in servers:
            if s["id"] == server_id:
                for key in ["name", "region", "ip", "port", "capacity", "status", "game_type"]:
                    if key in data:
                        s[key] = data[key]
                lobby["servers"] = servers
                config["lobby"] = lobby
                tournament.config = config
                tournament.save(update_fields=["config"])
                return s
        return {"error": "Server not found"}

    @staticmethod
    def delete_server(tournament: Tournament, server_id: str) -> dict:
        """Remove a server from the pool."""
        config = tournament.config or {}
        lobby = config.get("lobby", {})
        servers = lobby.get("servers", [])
        servers = [s for s in servers if s["id"] != server_id]
        lobby["servers"] = servers
        config["lobby"] = lobby
        tournament.config = config
        tournament.save(update_fields=["config"])
        return {"deleted": True}

    @staticmethod
    def create_lobby(tournament: Tournament, match_id: int, data: dict = None) -> dict:
        """Create a lobby for a match."""
        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            return {"error": "Match not found"}

        data = data or {}
        lobby_info = match.lobby_info or {}
        lobby_info.update({
            "code": data.get("code") or secrets.token_urlsafe(8).upper()[:8],
            "server_id": data.get("server_id", ""),
            "region": data.get("region", ""),
            "status": "active",
            "spectator_slots": data.get("spectator_slots", 2),
            "created_at": timezone.now().isoformat(),
            "chat": lobby_info.get("chat", []),
        })
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info"])
        logger.info(f"Lobby created for match {match_id}: {lobby_info['code']}")
        return lobby_info

    @staticmethod
    def close_lobby(tournament: Tournament, match_id: int) -> dict:
        """Close a match lobby."""
        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            return {"error": "Match not found"}

        lobby_info = match.lobby_info or {}
        lobby_info["status"] = "closed"
        lobby_info["closed_at"] = timezone.now().isoformat()
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info"])
        return {"status": "closed"}

    @staticmethod
    def add_chat_message(tournament: Tournament, match_id: int, user, message: str) -> dict:
        """Add a message to match room chat."""
        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            return {"error": "Match not found"}

        lobby_info = match.lobby_info or {}
        chat = lobby_info.get("chat", [])
        msg = {
            "id": len(chat) + 1,
            "user": user.username if user else "System",
            "message": message[:500],
            "timestamp": timezone.now().isoformat(),
            "is_admin": user.is_staff if user else False,
        }
        chat.append(msg)
        lobby_info["chat"] = chat[-100:]  # Keep last 100 messages
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info"])
        return msg

    @staticmethod
    def get_match_chat(tournament: Tournament, match_id: int) -> list:
        """Get chat messages for a match."""
        try:
            match = Match.objects.get(id=match_id, tournament=tournament)
        except Match.DoesNotExist:
            return []
        return (match.lobby_info or {}).get("chat", [])

    @staticmethod
    def update_lobby_config(tournament: Tournament, data: dict) -> dict:
        """Update lobby configuration — game-aware, multi-section.

        Persists to both ``config['lobby']`` (lobby-tab-owned settings) and
        ``config['lobby_policy']`` (registration-tab-owned settings) so the
        two sections never drift out of sync.
        """
        config = tournament.config if isinstance(tournament.config, dict) else {}
        lobby = config.get("lobby", {}) if isinstance(config.get("lobby"), dict) else {}
        lobby_policy = config.get("lobby_policy", {}) if isinstance(config.get("lobby_policy"), dict) else {}

        def _coerce_bool(val):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.strip().lower() in {"1", "true", "yes", "on"}
            return bool(val)

        def _coerce_int(val, default=0):
            try:
                return max(0, int(val))
            except (TypeError, ValueError):
                return default

        # ── Existing lobby-section keys ────────────────────────────────────
        for key in ["auto_create", "anticheat_required", "chat_enabled"]:
            if key in data:
                lobby[key] = _coerce_bool(data[key])
        if "default_region" in data:
            lobby["default_region"] = str(data["default_region"] or "").strip()
        for key in ["spectator_slots_default", "auto_close_minutes",
                    "lobby_open_minutes_before", "lobby_close_minutes_after",
                    "map_veto_seconds"]:
            if key in data:
                lobby[key] = _coerce_int(data[key], lobby.get(key, 0))

        # ── Coin toss ──────────────────────────────────────────────────────
        if "require_coin_toss" in data:
            lobby_policy["require_coin_toss"] = _coerce_bool(data["require_coin_toss"])
        if "coin_toss_actor" in data:
            actor = str(data["coin_toss_actor"] or "host").strip().lower()
            if actor not in ("host", "either", "staff"):
                actor = "host"
            lobby["coin_toss_actor"] = actor

        # ── Map veto ───────────────────────────────────────────────────────
        if "require_map_veto" in data:
            lobby_policy["require_map_veto"] = _coerce_bool(data["require_map_veto"])
        if "map_veto_auto_pick" in data:
            lobby["map_veto_auto_pick"] = _coerce_bool(data["map_veto_auto_pick"])

        # ── Credentials ────────────────────────────────────────────────────
        # Mirror the same key both ways: lobby.credentials_owner ↔ lobby_policy.credential_policy.
        # The match-room renderer reads from lobby_policy.credential_policy so we keep that
        # as the source of truth, with lobby.credentials_owner as a convenience mirror.
        if "credentials_owner" in data:
            owner = str(data["credentials_owner"] or "host").strip().lower()
            if owner not in ("host", "organizer", "staff"):
                owner = "host"
            lobby["credentials_owner"] = owner
            lobby_policy["credential_policy"] = owner

        # ── Result submission ──────────────────────────────────────────────
        if "require_match_evidence" in data:
            lobby_policy["require_match_evidence"] = _coerce_bool(data["require_match_evidence"])
        if "result_submission_policy" in data:
            policy = str(data["result_submission_policy"] or "any_participant").strip().lower()
            if policy not in ("any_participant", "host_first", "winner_only"):
                policy = "any_participant"
            lobby["result_submission_policy"] = policy

        config["lobby"] = lobby
        config["lobby_policy"] = lobby_policy
        tournament.config = config
        tournament.save(update_fields=["config", "updated_at"])

        # Invalidate any related caches so the FE sees fresh values on next refresh.
        try:
            from django.core.cache import cache
            cache.delete(f"toc:stamp:lobby:{tournament.id}")
        except Exception:
            pass

        return lobby
