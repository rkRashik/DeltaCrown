# apps/teams/realtime/consumers.py
"""
Team WebSocket Consumer (Module 3.3)

Handles real-time team events via Django Channels.
Follows Module 2.2/Module 3.2 WebSocket patterns.

Planning Reference: Documents/ExecutionPlan/Modules/MODULE_3.3_IMPLEMENTATION_PLAN.md

Traceability:
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md#team-channels
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md#adr-007
"""
import logging
from typing import Dict, Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.exceptions import ObjectDoesNotExist

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
    """
    
    async def connect(self):
        """
        Handle WebSocket connection.
        
        Subscribes user to team channel: team_{team_id}
        """
        self.team_id = self.scope['url_route']['kwargs']['team_id']
        self.team_group_name = f'team_{self.team_id}'
        self.user = self.scope.get('user')
        
        # Log connection attempt
        username = self.user.username if self.user and self.user.is_authenticated else 'anonymous'
        logger.info(f"[WS] Team connection attempt: team_id={self.team_id}, user={username}")
        
        # Join team group
        await self.channel_layer.group_add(
            self.team_group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"[WS] Team connection accepted: team_id={self.team_id}, user={username}")
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Unsubscribes from team channel.
        """
        username = self.user.username if self.user and self.user.is_authenticated else 'anonymous'
        logger.info(f"[WS] Team disconnection: team_id={self.team_id}, user={username}, code={close_code}")
        
        # Leave team group
        await self.channel_layer.group_discard(
            self.team_group_name,
            self.channel_name
        )
    
    async def receive_json(self, content: Dict[str, Any]):
        """
        Handle incoming WebSocket messages.
        
        Currently not processing client messages - broadcast-only.
        Following Module 3.2 pattern (no client-initiated events).
        """
        username = self.user.username if self.user and self.user.is_authenticated else 'anonymous'
        logger.warning(
            f"[WS] Received unexpected message from client: team_id={self.team_id}, "
            f"user={username}, content={content}"
        )
        
        await self.send_json({
            "error": "Client messages not supported. Team events are broadcast-only."
        })
    
    # ════════════════════════════════════════════════════════════════
    # Team Event Handlers (5 events)
    # ════════════════════════════════════════════════════════════════
    
    async def team_created(self, event: Dict[str, Any]):
        """
        Handle team.created event from channel layer.
        
        Triggered by: TeamService.create_team() via API
        
        Payload:
        {
            "team_id": 42,
            "team_name": "Phoenix Squad",
            "captain_username": "player1",
            "game": "valorant",
            "created_at": "2025-11-08T15:00:00Z"
        }
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-creation
        """
        payload = event.get('payload', {})
        
        logger.info(
            f"[WS] Broadcasting team.created: team_id={payload.get('team_id')}, "
            f"team_name={payload.get('team_name')}"
        )
        
        # Send to WebSocket
        await self.send_json({
            "type": "team.created",
            "team_id": payload.get('team_id'),
            "team_name": payload.get('team_name'),
            "captain_username": payload.get('captain_username'),
            "game": payload.get('game'),
            "created_at": payload.get('created_at')
        })
    
    async def team_member_joined(self, event: Dict[str, Any]):
        """
        Handle team.member_joined event from channel layer.
        
        Triggered by: TeamService.accept_invite() via API
        
        Payload:
        {
            "team_id": 42,
            "team_name": "Phoenix Squad",
            "username": "player2",
            "role": "player",
            "timestamp": "2025-11-08T15:30:00Z"
        }
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#invitations
        """
        payload = event.get('payload', {})
        
        logger.info(
            f"[WS] Broadcasting team.member_joined: team_id={payload.get('team_id')}, "
            f"username={payload.get('username')}, role={payload.get('role')}"
        )
        
        # Send to WebSocket
        await self.send_json({
            "type": "team.member_joined",
            "team_id": payload.get('team_id'),
            "team_name": payload.get('team_name'),
            "username": payload.get('username'),
            "role": payload.get('role'),
            "timestamp": payload.get('timestamp')
        })
    
    async def team_member_removed(self, event: Dict[str, Any]):
        """
        Handle team.member_removed event from channel layer.
        
        Triggered by: TeamService.remove_member() via API
        
        Payload:
        {
            "team_id": 42,
            "team_name": "Phoenix Squad",
            "removed_user": "player2",
            "removed_by": "player1",
            "timestamp": "2025-11-08T16:00:00Z"
        }
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
        """
        payload = event.get('payload', {})
        
        logger.info(
            f"[WS] Broadcasting team.member_removed: team_id={payload.get('team_id')}, "
            f"removed_user={payload.get('removed_user')}, removed_by={payload.get('removed_by')}"
        )
        
        # Send to WebSocket
        await self.send_json({
            "type": "team.member_removed",
            "team_id": payload.get('team_id'),
            "team_name": payload.get('team_name'),
            "removed_user": payload.get('removed_user'),
            "removed_by": payload.get('removed_by'),
            "timestamp": payload.get('timestamp')
        })
    
    async def team_captain_transferred(self, event: Dict[str, Any]):
        """
        Handle team.captain_transferred event from channel layer.
        
        Triggered by: TeamService.transfer_captain() via API
        
        Payload:
        {
            "team_id": 42,
            "team_name": "Phoenix Squad",
            "old_captain": "player1",
            "new_captain": "player2",
            "timestamp": "2025-11-08T16:30:00Z"
        }
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#captain-transfer
        """
        payload = event.get('payload', {})
        
        logger.info(
            f"[WS] Broadcasting team.captain_transferred: team_id={payload.get('team_id')}, "
            f"old_captain={payload.get('old_captain')}, new_captain={payload.get('new_captain')}"
        )
        
        # Send to WebSocket
        await self.send_json({
            "type": "team.captain_transferred",
            "team_id": payload.get('team_id'),
            "team_name": payload.get('team_name'),
            "old_captain": payload.get('old_captain'),
            "new_captain": payload.get('new_captain'),
            "timestamp": payload.get('timestamp')
        })
    
    async def team_disbanded(self, event: Dict[str, Any]):
        """
        Handle team.disbanded event from channel layer.
        
        Triggered by: TeamService.disband_team() via API
        
        Payload:
        {
            "team_id": 42,
            "team_name": "Phoenix Squad",
            "disbanded_by": "player1",
            "timestamp": "2025-11-08T17:00:00Z"
        }
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#team-dissolution
        """
        payload = event.get('payload', {})
        
        logger.info(
            f"[WS] Broadcasting team.disbanded: team_id={payload.get('team_id')}, "
            f"team_name={payload.get('team_name')}, disbanded_by={payload.get('disbanded_by')}"
        )
        
        # Send to WebSocket
        await self.send_json({
            "type": "team.disbanded",
            "team_id": payload.get('team_id'),
            "team_name": payload.get('team_name'),
            "disbanded_by": payload.get('disbanded_by'),
            "timestamp": payload.get('timestamp')
        })
    
    async def team_member_left(self, event: Dict[str, Any]):
        """
        Handle team.member_left event from channel layer.
        
        Triggered by: TeamService.leave_team() via API
        
        Payload:
        {
            "team_id": 42,
            "team_name": "Phoenix Squad",
            "username": "player2",
            "timestamp": "2025-11-08T16:15:00Z"
        }
        
        Traceability:
        - Documents/Planning/PART_4.5_TEAM_MANAGEMENT_FLOW.md#roster-management
        """
        payload = event.get('payload', {})
        
        logger.info(
            f"[WS] Broadcasting team.member_left: team_id={payload.get('team_id')}, "
            f"username={payload.get('username')}"
        )
        
        # Send to WebSocket
        await self.send_json({
            "type": "team.member_left",
            "team_id": payload.get('team_id'),
            "team_name": payload.get('team_name'),
            "username": payload.get('username'),
            "timestamp": payload.get('timestamp')
        })
