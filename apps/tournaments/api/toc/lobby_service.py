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

        return {
            "servers": servers,
            "matches": match_lobbies,
            "config": {
                "auto_create": lobby_config.get("auto_create", False),
                "default_region": lobby_config.get("default_region", ""),
                "spectator_slots_default": lobby_config.get("spectator_slots_default", 2),
                "anticheat_required": lobby_config.get("anticheat_required", False),
                "chat_enabled": lobby_config.get("chat_enabled", True),
                "auto_close_minutes": lobby_config.get("auto_close_minutes", 0),
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
        """Update lobby configuration."""
        config = tournament.config or {}
        lobby = config.get("lobby", {})
        for key in [
            "auto_create",
            "default_region",
            "spectator_slots_default",
            "anticheat_required",
            "chat_enabled",
            "auto_close_minutes",
        ]:
            if key in data:
                lobby[key] = data[key]
        config["lobby"] = lobby
        tournament.config = config
        tournament.save(update_fields=["config"])
        return lobby
