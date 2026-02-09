# apps/organizations/realtime/consumers.py
"""
Team WebSocket Consumer — migrated from apps.teams.realtime.consumers

Handles real-time team events via Django Channels.
"""
import logging
from typing import Dict, Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class TeamConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for team events.

    Channel: team_{team_id}

    Events:
    - team.created - New team created
    - team.member_joined - Player accepted invite
    - team.member_removed - Captain removed member
    - team.captain_transferred - Captain role transferred
    - team.disbanded - Team disbanded
    - team.member_left - Member left voluntarily
    """

    async def connect(self):
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.team_group_name = f'team_{self.team_id}'
        self.user = self.scope.get('user')

        username = self.user.username if self.user and self.user.is_authenticated else 'anonymous'
        logger.info("[WS] Team connection attempt: team_id=%s, user=%s", self.team_id, username)

        await self.channel_layer.group_add(self.team_group_name, self.channel_name)
        await self.accept()
        logger.info("[WS] Team connection accepted: team_id=%s, user=%s", self.team_id, username)

    async def disconnect(self, close_code):
        username = self.user.username if self.user and self.user.is_authenticated else 'anonymous'
        logger.info("[WS] Team disconnection: team_id=%s, user=%s, code=%s", self.team_id, username, close_code)
        await self.channel_layer.group_discard(self.team_group_name, self.channel_name)

    async def receive_json(self, content: Dict[str, Any]):
        await self.send_json({"error": "Client messages not supported. Team events are broadcast-only."})

    # ─── Event handlers ──────────────────────────────────────────
    async def team_created(self, event: Dict[str, Any]):
        payload = event.get('payload', {})
        await self.send_json({"type": "team.created", **{k: payload.get(k) for k in ('team_id', 'team_name', 'captain_username', 'game', 'created_at')}})

    async def team_member_joined(self, event: Dict[str, Any]):
        payload = event.get('payload', {})
        await self.send_json({"type": "team.member_joined", **{k: payload.get(k) for k in ('team_id', 'team_name', 'username', 'role', 'timestamp')}})

    async def team_member_removed(self, event: Dict[str, Any]):
        payload = event.get('payload', {})
        await self.send_json({"type": "team.member_removed", **{k: payload.get(k) for k in ('team_id', 'team_name', 'removed_user', 'removed_by', 'timestamp')}})

    async def team_captain_transferred(self, event: Dict[str, Any]):
        payload = event.get('payload', {})
        await self.send_json({"type": "team.captain_transferred", **{k: payload.get(k) for k in ('team_id', 'team_name', 'old_captain', 'new_captain', 'timestamp')}})

    async def team_disbanded(self, event: Dict[str, Any]):
        payload = event.get('payload', {})
        await self.send_json({"type": "team.disbanded", **{k: payload.get(k) for k in ('team_id', 'team_name', 'disbanded_by', 'timestamp')}})

    async def team_member_left(self, event: Dict[str, Any]):
        payload = event.get('payload', {})
        await self.send_json({"type": "team.member_left", **{k: payload.get(k) for k in ('team_id', 'team_name', 'username', 'timestamp')}})
