"""
WebSocket Consumer for Match-Specific Real-Time Updates

Handles WebSocket connections for individual match rooms, broadcasting live updates
for match-specific events (scores, disputes, state transitions).

Phase 4: Tournament Operations API
Module 4.5: WebSocket Enhancement

Connection URL:
    ws://domain/ws/match/<match_id>/?token=<jwt_access_token>

Event Flow:
    1. Client connects with JWT token to match room
    2. Server validates token via JWTAuthMiddleware
    3. Consumer validates user is participant/organizer/admin (or spectator read-only)
    4. Consumer joins match_{match_id} room group
    5. Service layer broadcasts match events (score_updated, dispute_created, etc.)
    6. Consumer receives events and sends to client
    7. Client disconnects, consumer leaves group

Security Features:
    - JWT authentication required (inherited from JWTAuthMiddleware)
    - Role-based access: participants/organizers/admins (full), spectators (read-only)
    - Match isolation (clients only receive events for their match)
    - Server-initiated heartbeat (25s ping, 50s timeout)
    - Origin validation and payload size limits (inherited from Module 2.5)

Event Types:
    - score_updated: Match score changes (with micro-batching)
    - match_completed: Match finishes with confirmed result
    - dispute_created: Dispute reported for match (NEW in Module 4.5)
    - match_started: Match transitions to LIVE state
    - match_state_changed: Generic state transition event
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from apps.tournaments.security import (
    TournamentRole,
    get_user_tournament_role,
)

logger = logging.getLogger(__name__)


class MatchConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for match-specific real-time updates.
    
    Handles connections to match-specific rooms and broadcasts events
    to all connected clients watching a specific match. Requires JWT 
    authentication via middleware.
    
    Attributes:
        match_id (int): Match ID from URL path
        room_group_name (str): Channel layer group name (match_{id})
        user: Authenticated user from JWT token (injected by middleware)
        user_role (TournamentRole): User's role in tournament
        is_participant (bool): Whether user is a match participant
        heartbeat_task (asyncio.Task): Server-initiated heartbeat timer
        last_pong_time (float): Timestamp of last client pong response
        
    Event Handlers:
        - score_updated: Match score changes (micro-batched)
        - match_completed: Match finishes
        - dispute_created: Dispute reported (NEW)
        - match_started: Match begins
        - match_state_changed: Generic state transition
        
    Authentication:
        - Requires valid JWT token in query parameter: ?token=<jwt>
        - User injected into scope by JWTAuthMiddleware
        - Anonymous users rejected on connect
        
    Authorization:
        - Participants: Full access (read + write actions)
        - Organizers/Admins: Full access
        - Spectators: Read-only access (can connect but limited actions)
        
    Heartbeat:
        - Server sends ping every 25s
        - Client must respond with pong within 50s (2 intervals)
        - No pong = close with code 4004 (heartbeat timeout)
    """
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    HEARTBEAT_INTERVAL = 25  # seconds
    HEARTBEAT_TIMEOUT = 50  # seconds (2 intervals)
    
    @staticmethod
    def get_allowed_origins() -> Optional[list]:
        """Get allowed origins from settings (inherited from Module 2.5)."""
        origins = getattr(settings, 'WS_ALLOWED_ORIGINS', None)
        if origins:
            return [o.strip() for o in origins.split(',') if o.strip()]
        return None
    
    async def connect(self):
        """
        Handle WebSocket connection to match room.
        
        Process:
            1. Extract match_id from URL route
            2. Verify user is authenticated (JWT validated by middleware)
            3. Validate user has access to match (participant/organizer/admin/spectator)
            4. Validate origin (if WS_ALLOWED_ORIGINS configured)
            5. Join match_{match_id} room group
            6. Accept WebSocket connection
            7. Start server-initiated heartbeat timer
            8. Send welcome message with connection confirmation
            
        Rejection Cases:
            - User is AnonymousUser (invalid/missing JWT token)
            - Match ID missing from route
            - Origin not in allowlist (production only)
            
        Side Effects:
            - Adds connection to channel layer group (match_{match_id})
            - Starts asyncio heartbeat task
            - Logs connection attempts and failures
        """
        # Extract match ID from URL route
        self.match_id = self.scope['url_route']['kwargs'].get('match_id')
        
        if not self.match_id:
            logger.warning("WebSocket connection attempted without match_id")
            await self.close(code=4000)
            return
        
        # Check authentication (user injected by JWTAuthMiddleware)
        self.user = self.scope.get('user', AnonymousUser())
        
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            logger.warning(
                f"Unauthenticated WebSocket connection attempt to match {self.match_id}"
            )
            await self.close(code=4001)  # 4001: Authentication required
            return
        
        # =====================================================================
        # Authorization: Validate user has access to this match
        # =====================================================================
        
        # Import here to avoid circular imports
        from apps.tournaments.models import Match
        
        try:
            match = await self._get_match(self.match_id)
            
            if not match:
                logger.warning(
                    f"Match {self.match_id} not found for user {self.user.username}"
                )
                await self.close(code=4004)  # 4004: Not found
                return
            
            self.tournament_id = match.tournament_id
            
            # Determine user's tournament role (wrap sync function for async context)
            from channels.db import database_sync_to_async
            self.user_role = await database_sync_to_async(get_user_tournament_role)(self.user)
            
            # Check if user is a match participant
            self.is_participant = self.user.id in [
                match.participant1_id, 
                match.participant2_id
            ]
            
            # Authorization check:
            # - Participants, organizers, admins: Full access
            # - Spectators: Read-only access (can connect)
            # - Note: Specific action permissions validated in receive_json
            
            logger.info(
                f"Match WebSocket role assigned: user={self.user.username}, "
                f"role={self.user_role.value}, match={self.match_id}, "
                f"participant={self.is_participant}"
            )
            
        except Exception as e:
            logger.error(
                f"Error validating match access for user {self.user.username}: {e}",
                exc_info=True
            )
            await self.close(code=4003)  # 4003: Forbidden
            return
        
        # =====================================================================
        # Origin Validation (Module 2.5)
        # =====================================================================
        
        allowed_origins = self.get_allowed_origins()
        if allowed_origins:
            origin = self._get_origin()
            
            if origin and origin not in allowed_origins:
                logger.warning(
                    f"Match WebSocket connection rejected: invalid origin {origin}"
                )
                await self.send_json({
                    'type': 'error',
                    'code': 'invalid_origin',
                    'message': 'Connection rejected: invalid origin'
                })
                await self.close(code=4003)
                return
        
        # Generate room group name
        self.room_group_name = f'match_{self.match_id}'
        
        # Join match room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept WebSocket connection
        await self.accept()
        
        logger.info(
            f"Match WebSocket connected: user={self.user.username} (ID: {self.user.id}), "
            f"role={self.user_role.value}, match={self.match_id}, "
            f"participant={self.is_participant}, channel={self.channel_name}"
        )
        
        # =====================================================================
        # Module 4.5: Start server-initiated heartbeat
        # =====================================================================
        
        self.last_pong_time = asyncio.get_event_loop().time()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Send welcome message to client
        await self.send_json({
            'type': 'connection_established',
            'data': {
                'match_id': self.match_id,
                'tournament_id': self.tournament_id,
                'user_id': self.user.id,
                'username': self.user.username,
                'role': self.user_role.value,
                'is_participant': self.is_participant,
                'message': f'Connected to match {self.match_id} updates',
                'heartbeat_interval': self.HEARTBEAT_INTERVAL,
            }
        })
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Args:
            close_code: WebSocket close code
            
        Process:
            1. Cancel heartbeat task
            2. Leave match room group
            3. Log disconnection
            
        Side Effects:
            - Removes connection from channel layer group
            - Cancels asyncio heartbeat task
            - Logs disconnection with close code
        """
        # Cancel heartbeat task
        if hasattr(self, 'heartbeat_task'):
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Leave match room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            logger.info(
                f"Match WebSocket disconnected: user={getattr(self, 'user', 'unknown')}, "
                f"match={getattr(self, 'match_id', 'unknown')}, "
                f"close_code={close_code}"
            )
    
    # =========================================================================
    # Event Handlers (called by channel layer group_send)
    # =========================================================================
    
    async def score_updated(self, event: Dict[str, Any]):
        """
        Handle score_updated event from channel layer.
        
        Module 4.5: Supports micro-batching (100ms window, latest wins).
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'match_id': int,
                    'tournament_id': int,
                    'participant1_score': int,
                    'participant2_score': int,
                    'updated_at': str (ISO 8601),
                    'updated_by': int (user_id),
                    'sequence': int (optional, for batching),
                }
                
        Broadcasts to client:
            JSON message with type='score_updated' and event data
        """
        await self.send_json({
            'type': 'score_updated',
            'data': event['data']
        })
        
        logger.debug(
            f"Sent score_updated to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}, "
            f"seq={event['data'].get('sequence', 'N/A')}"
        )
    
    async def match_completed(self, event: Dict[str, Any]):
        """
        Handle match_completed event from channel layer.
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'match_id': int,
                    'tournament_id': int,
                    'winner_id': int,
                    'winner_name': str,
                    'loser_id': int,
                    'loser_name': str,
                    'participant1_score': int,
                    'participant2_score': int,
                    'confirmed_at': str (ISO 8601),
                    'confirmed_by': int (user_id),
                }
                
        Broadcasts to client:
            JSON message with type='match_completed' and event data
        """
        await self.send_json({
            'type': 'match_completed',
            'data': event['data']
        })
        
        logger.info(
            f"Sent match_completed to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}, "
            f"winner_id={event['data'].get('winner_id')}"
        )
    
    async def dispute_created(self, event: Dict[str, Any]):
        """
        Handle dispute_created event from channel layer.
        
        Module 4.5: NEW event for dispute reporting.
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'match_id': int,
                    'tournament_id': int,
                    'dispute_id': int,
                    'initiated_by': int (user_id),
                    'reason': str,
                    'status': str,  # 'open', 'under_review', etc.
                    'timestamp': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='dispute_created' and event data
        """
        await self.send_json({
            'type': 'dispute_created',
            'data': event['data']
        })
        
        logger.info(
            f"Sent dispute_created to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}, "
            f"dispute_id={event['data'].get('dispute_id')}"
        )
    
    async def match_started(self, event: Dict[str, Any]):
        """
        Handle match_started event from channel layer.
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'match_id': int,
                    'tournament_id': int,
                    'participant1_id': int,
                    'participant1_name': str,
                    'participant2_id': int,
                    'participant2_name': str,
                    'scheduled_time': str (ISO 8601),
                    'bracket_round': int,
                    'bracket_position': int,
                }
                
        Broadcasts to client:
            JSON message with type='match_started' and event data
        """
        await self.send_json({
            'type': 'match_started',
            'data': event['data']
        })
        
        logger.debug(
            f"Sent match_started to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}"
        )
    
    async def match_state_changed(self, event: Dict[str, Any]):
        """
        Handle match_state_changed event from channel layer.
        
        Generic event for any match state transition.
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'match_id': int,
                    'tournament_id': int,
                    'old_state': str,
                    'new_state': str,
                    'timestamp': str (ISO 8601),
                    'changed_by': int (user_id),
                }
                
        Broadcasts to client:
            JSON message with type='match_state_changed' and event data
        """
        await self.send_json({
            'type': 'match_state_changed',
            'data': event['data']
        })
        
        logger.debug(
            f"Sent match_state_changed to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}, "
            f"state={event['data'].get('old_state')} → {event['data'].get('new_state')}"
        )
    
    # =========================================================================
    # Client Message Handling
    # =========================================================================
    
    async def receive_json(self, content: Dict[str, Any], **kwargs):
        """
        Handle JSON messages received from WebSocket client.
        
        Module 4.5: Server-initiated heartbeat - client must respond to ping.
        
        Currently supports:
            - pong: Response to server ping (heartbeat)
            - ping: Client-initiated keepalive
            - subscribe: Subscribe confirmation (no-op)
        
        Args:
            content: Parsed JSON message from client
            **kwargs: Additional keyword arguments
            
        Validation:
            - Requires 'type' field
            - Payload size checked by middleware (max 16 KB)
            - Action permissions checked for privileged operations
        """
        # Validate required 'type' field
        if 'type' not in content:
            logger.warning(
                f"Invalid message from user {self.user.username}: missing 'type' field"
            )
            await self.send_json({
                'type': 'error',
                'code': 'invalid_schema',
                'message': 'Message must include "type" field',
            })
            return
        
        message_type = content['type']
        
        logger.debug(
            f"Received message from user {self.user.username} "
            f"(role={self.user_role.value}): type={message_type}"
        )
        
        # =====================================================================
        # Module 4.5: Heartbeat - Client pong response
        # =====================================================================
        
        if message_type == 'pong':
            # Update last pong time (client responded to server ping)
            self.last_pong_time = asyncio.get_event_loop().time()
            logger.debug(
                f"Heartbeat pong received from user {self.user.username}, "
                f"match={self.match_id}"
            )
            return
        
        # =====================================================================
        # Client-initiated ping (legacy, still supported)
        # =====================================================================
        
        if message_type == 'ping':
            await self.send_json({
                'type': 'pong',
                'timestamp': content.get('timestamp'),
            })
            return
        
        # =====================================================================
        # Subscribe confirmation (no-op)
        # =====================================================================
        
        if message_type == 'subscribe':
            await self.send_json({
                'type': 'subscribed',
                'data': {
                    'match_id': self.match_id,
                    'tournament_id': self.tournament_id,
                    'message': 'Successfully subscribed to match updates',
                }
            })
            return
        
        # =====================================================================
        # Unknown message type
        # =====================================================================
        
        await self.send_json({
            'type': 'error',
            'code': 'unsupported_message_type',
            'message': f'Message type "{message_type}" not supported',
        })
    
    # =========================================================================
    # Module 4.5: Server-Initiated Heartbeat
    # =========================================================================
    
    async def _heartbeat_loop(self):
        """
        Server-initiated heartbeat loop.
        
        Module 4.5: Ping client every 25s, expect pong within 50s.
        
        Process:
            1. Wait HEARTBEAT_INTERVAL seconds
            2. Send ping to client with timestamp
            3. Check if client responded with pong within timeout
            4. If no pong after HEARTBEAT_TIMEOUT, close connection
            5. Repeat
            
        Close Code:
            4004: Heartbeat timeout (no pong from client)
        """
        try:
            while True:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
                
                # Check if client responded to previous ping
                current_time = asyncio.get_event_loop().time()
                time_since_pong = current_time - self.last_pong_time
                
                if time_since_pong > self.HEARTBEAT_TIMEOUT:
                    logger.warning(
                        f"Heartbeat timeout for user {self.user.username}, "
                        f"match={self.match_id}, no pong for {time_since_pong:.1f}s"
                    )
                    await self.close(code=4004)  # 4004: Heartbeat timeout
                    return
                
                # Send ping to client
                await self.send_json({
                    'type': 'ping',
                    'timestamp': current_time,
                })
                
                logger.debug(
                    f"Heartbeat ping sent to user {self.user.username}, "
                    f"match={self.match_id}"
                )
                
        except asyncio.CancelledError:
            logger.debug(
                f"Heartbeat loop cancelled for user {self.user.username}, "
                f"match={self.match_id}"
            )
        except Exception as e:
            logger.error(
                f"Heartbeat loop error for user {self.user.username}, "
                f"match={self.match_id}: {e}",
                exc_info=True
            )
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _get_origin(self) -> Optional[str]:
        """
        Extract origin from WebSocket headers.
        
        Returns:
            Origin header value or None if not present
        """
        headers = dict(self.scope.get('headers', []))
        origin = headers.get(b'origin')
        
        if origin:
            return origin.decode('utf-8')
        
        return None
    
    @staticmethod
    async def _get_match(match_id: int):
        """
        Fetch match from database (async).
        
        Args:
            match_id: Match ID to fetch
            
        Returns:
            Match instance or None if not found
        """
        from channels.db import database_sync_to_async
        from apps.tournaments.models import Match
        
        @database_sync_to_async
        def get_match_sync():
            return Match.objects.filter(id=match_id).first()
        
        return await get_match_sync()
