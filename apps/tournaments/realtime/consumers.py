"""
WebSocket Consumers for Real-Time Tournament Updates

Handles WebSocket connections for tournament rooms, broadcasting live updates
for matches, scores, and bracket progressions.

Phase 2: Real-Time Features & Security
Module 2.2: WebSocket Real-Time Updates
Module 2.4: Security Hardening (role-based access control)
Module 2.5: Rate Limiting & Abuse Protection (hardened)

Connection URL:
    ws://domain/ws/tournament/<tournament_id>/?token=<jwt_access_token>

Event Flow:
    1. Client connects with JWT token
    2. Server validates token via JWTAuthMiddleware
    3. RateLimitMiddleware enforces connection/message limits
    4. Consumer validates origin and role permissions
    5. Consumer joins tournament room group
    6. Service layer broadcasts events (match_started, score_updated, etc.)
    7. Consumer receives events and sends to client
    8. Client disconnects, consumer leaves group

Security Features (Module 2.4):
    - Role-based access control (SPECTATOR, PLAYER, ORGANIZER, ADMIN)
    - Action-level permissions for privileged operations
    - Organizer/admin-only actions protected

Security Features (Module 2.5):
    - Origin validation (configurable allowlist)
    - Max payload size enforcement (16 KB default)
    - Schema validation for client messages
    - Room isolation (no cross-tournament broadcasts)
"""

import logging
import json
from typing import Dict, Any, List, Optional
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from apps.tournaments.security import (
    TournamentRole,
    get_user_tournament_role,
    check_tournament_role,
    check_websocket_action_permission,
)

logger = logging.getLogger(__name__)


class TournamentConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time tournament updates.
    
    Handles connections to tournament-specific rooms and broadcasts events
    to all connected clients. Requires JWT authentication via middleware.
    
    Attributes:
        tournament_id (int): Tournament ID from URL path
        room_group_name (str): Channel layer group name (tournament_{id})
        user: Authenticated user from JWT token (injected by middleware)
        
    Event Handlers:
        - match_started: New match begins
        - score_updated: Match score changes
        - match_completed: Match finishes with confirmed result
        - bracket_updated: Bracket progression after match completion
        
    Authentication:
        - Requires valid JWT token in query parameter: ?token=<jwt>
        - User injected into scope by JWTAuthMiddleware
        - Anonymous users are rejected on connect
        
    Security (Module 2.5):
        - Origin validation against WS_ALLOWED_ORIGINS
        - Max payload size (16 KB default)
        - Schema validation for client messages
        - Room isolation (no cross-tournament access)
        
    Example Client Usage:
        ```javascript
        const token = localStorage.getItem('access_token');
        const ws = new WebSocket(
            `ws://localhost:8000/ws/tournament/1/?token=${token}`
        );
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            if (data.type === 'match_completed') {
                updateBracketUI(data);
            }
        };
        ```
    """
    
    # =========================================================================
    # Configuration
    # =========================================================================
    
    @staticmethod
    def get_allowed_origins() -> Optional[List[str]]:
        """Get allowed origins from settings."""
        origins = getattr(settings, 'WS_ALLOWED_ORIGINS', None)
        if origins:
            # Parse comma-separated string
            return [o.strip() for o in origins.split(',') if o.strip()]
        return None
    
    @staticmethod
    def get_max_payload_bytes() -> int:
        """Get max payload size from settings."""
        return getattr(settings, 'WS_MAX_PAYLOAD_BYTES', 16 * 1024)  # 16 KB default
    
    async def connect(self):
        """
        Handle WebSocket connection.
        
        Process:
            1. Extract tournament_id from URL route
            2. Verify user is authenticated (JWT validated by middleware)
            3. Validate user role (minimum: SPECTATOR)
            4. Validate origin (if WS_ALLOWED_ORIGINS configured)
            5. Join tournament room group
            6. Accept WebSocket connection
            7. Send welcome message with connection confirmation
            
        Rejection Cases:
            - User is AnonymousUser (invalid/missing JWT token)
            - Tournament ID missing from route
            - Origin not in allowlist (production only)
            
        Side Effects:
            - Adds connection to channel layer group
            - Logs connection attempts and failures
            - Stores user role in consumer instance
        """
        # Extract tournament ID from URL route
        self.tournament_id = self.scope['url_route']['kwargs'].get('tournament_id')
        
        if not self.tournament_id:
            logger.warning("WebSocket connection attempted without tournament_id")
            await self.close(code=4000)
            return
        
        # Check authentication (user injected by JWTAuthMiddleware)
        self.user = self.scope.get('user', AnonymousUser())
        
        if isinstance(self.user, AnonymousUser) or not self.user.is_authenticated:
            logger.warning(
                f"Unauthenticated WebSocket connection attempt to tournament {self.tournament_id}"
            )
            await self.close(code=4001)  # 4001: Authentication required
            return
        
        # =====================================================================
        # MODULE 2.4: Role-Based Access Control
        # =====================================================================
        
        # Determine user's tournament role
        self.user_role = get_user_tournament_role(self.user)
        
        # All authenticated users can connect (minimum: SPECTATOR)
        # Specific actions will be validated in receive_json
        logger.info(
            f"WebSocket role assigned: user={self.user.username}, "
            f"role={self.user_role.value}, tournament={self.tournament_id}"
        )
        
        # =====================================================================
        # MODULE 2.5: Origin Validation
        # =====================================================================
        
        allowed_origins = self.get_allowed_origins()
        if allowed_origins:
            origin = self._get_origin()
            
            if origin and origin not in allowed_origins:
                logger.warning(
                    f"WebSocket connection rejected: invalid origin {origin}. "
                    f"Allowed: {allowed_origins}"
                )
                await self.send_json({
                    'type': 'error',
                    'code': 'invalid_origin',
                    'message': 'Connection rejected: invalid origin'
                })
                await self.close(code=4003)  # 4003: Forbidden
                return
        
        # Generate room group name
        self.room_group_name = f'tournament_{self.tournament_id}'
        
        # Join tournament room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept WebSocket connection
        await self.accept()
        
        logger.info(
            f"WebSocket connected: user={self.user.username} (ID: {self.user.id}), "
            f"role={self.user_role.value}, tournament={self.tournament_id}, "
            f"channel={self.channel_name}"
        )
        
        # Send welcome message to client
        await self.send_json({
            'type': 'connection_established',
            'data': {
                'tournament_id': self.tournament_id,
                'user_id': self.user.id,
                'username': self.user.username,
                'role': self.user_role.value,  # Inform client of their role
                'message': f'Connected to tournament {self.tournament_id} updates',
            }
        })
    
    async def disconnect(self, close_code):
        """
        Handle WebSocket disconnection.
        
        Args:
            close_code: WebSocket close code
            
        Process:
            1. Leave tournament room group
            2. Log disconnection
            
        Side Effects:
            - Removes connection from channel layer group
            - Logs disconnection with close code
        """
        if hasattr(self, 'room_group_name'):
            # Leave tournament room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
            
            logger.info(
                f"WebSocket disconnected: user={getattr(self, 'user', 'unknown')}, "
                f"tournament={getattr(self, 'tournament_id', 'unknown')}, "
                f"close_code={close_code}"
            )
    
    # -------------------------------------------------------------------------
    # Event Handlers (called by channel layer group_send)
    # -------------------------------------------------------------------------
    
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
            f"Sent match_started event to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}"
        )
    
    async def score_updated(self, event: Dict[str, Any]):
        """
        Handle score_updated event from channel layer.
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'match_id': int,
                    'tournament_id': int,
                    'participant1_score': int,
                    'participant2_score': int,
                    'updated_at': str (ISO 8601),
                    'updated_by': int (user_id),
                }
                
        Broadcasts to client:
            JSON message with type='score_updated' and event data
        """
        await self.send_json({
            'type': 'score_updated',
            'data': event['data']
        })
        
        logger.debug(
            f"Sent score_updated event to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}"
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
            f"Sent match_completed event to user {self.user.username}: "
            f"match_id={event['data'].get('match_id')}, "
            f"winner_id={event['data'].get('winner_id')}"
        )
    
    async def bracket_updated(self, event: Dict[str, Any]):
        """
        Handle bracket_updated event from channel layer.
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'bracket_id': int,
                    'tournament_id': int,
                    'updated_nodes': List[int],  # BracketNode IDs that changed
                    'next_matches': List[Dict],  # Newly created matches
                    'bracket_status': str,  # 'active', 'completed', etc.
                    'updated_at': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='bracket_updated' and event data
        """
        await self.send_json({
            'type': 'bracket_updated',
            'data': event['data']
        })
        
        logger.info(
            f"Sent bracket_updated event to user {self.user.username}: "
            f"bracket_id={event['data'].get('bracket_id')}, "
            f"nodes_updated={len(event['data'].get('updated_nodes', []))}"
        )
    
    async def bracket_generated(self, event: Dict[str, Any]):
        """
        Handle bracket_generated event from channel layer.
        
        Module 4.1: Bracket Generation API
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'bracket_id': int,
                    'tournament_id': int,
                    'tournament_name': str,
                    'format': str,  # 'single-elimination', 'round-robin', etc.
                    'seeding_method': str,  # 'random', 'slot-order', 'ranked', etc.
                    'total_rounds': int,
                    'total_matches': int,
                    'generated_at': str (ISO 8601),
                    'generated_by': int (user_id),
                    'is_regeneration': bool (optional),
                }
                
        Broadcasts to client:
            JSON message with type='bracket_generated' and event data
        """
        await self.send_json({
            'type': 'bracket_generated',
            'data': event['data']
        })
        
        logger.info(
            f"Sent bracket_generated event to user {self.user.username}: "
            f"bracket_id={event['data'].get('bracket_id')}, "
            f"format={event['data'].get('format')}, "
            f"total_matches={event['data'].get('total_matches')}"
        )
    
    async def registration_created(self, event: Dict[str, Any]):
        """
        Handle registration.created event from channel layer.
        
        Module 3.1: Real-time registration updates
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'registration_id': int,
                    'tournament_id': int,
                    'user_id': int,
                    'user_name': str,
                    'team_id': int | None,
                    'team_name': str | None,
                    'status': str,  # 'pending', 'payment_submitted', 'confirmed'
                    'timestamp': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='registration_created' and event data
        """
        await self.send_json({
            'type': 'registration_created',
            'data': event['data']
        })
        
        logger.info(
            f"Sent registration_created event to user {self.user.username}: "
            f"registration_id={event['data'].get('registration_id')}, "
            f"tournament_id={event['data'].get('tournament_id')}"
        )
    
    async def registration_cancelled(self, event: Dict[str, Any]):
        """
        Handle registration.cancelled event from channel layer.
        
        Module 3.1: Real-time cancellation updates
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'registration_id': int,
                    'tournament_id': int,
                    'user_id': int,
                    'user_name': str,
                    'reason': str | None,
                    'timestamp': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='registration_cancelled' and event data
        """
        await self.send_json({
            'type': 'registration_cancelled',
            'data': event['data']
        })
        
        logger.info(
            f"Sent registration_cancelled event to user {self.user.username}: "
            f"registration_id={event['data'].get('registration_id')}, "
            f"tournament_id={event['data'].get('tournament_id')}"
        )
    
    # -------------------------------------------------------------------------
    # Payment Event Handlers (Module 3.2)
    # -------------------------------------------------------------------------
    
    async def payment_proof_submitted(self, event: Dict[str, Any]):
        """
        Handle payment.proof_submitted event from channel layer.
        
        Module 3.2: Real-time payment proof submission updates
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'payment_id': int,
                    'registration_id': int,
                    'tournament_id': int,
                    'status': str,  # 'submitted'
                    'timestamp': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='payment_proof_submitted' and event data
            
        Security:
            - Room isolation validated (tournament_id must match)
            - No sensitive data exposed (file URLs, reference numbers excluded)
        """
        # Validate room isolation
        if not self._validate_room_isolation(event.get('tournament_id')):
            return
        
        await self.send_json({
            'type': 'payment_proof_submitted',
            'data': {
                'payment_id': event.get('payment_id'),
                'registration_id': event.get('registration_id'),
                'tournament_id': event.get('tournament_id'),
                'status': event.get('status'),
                'timestamp': event.get('timestamp'),
            }
        })
        
        logger.info(
            f"Sent payment_proof_submitted event to user {self.user.username}: "
            f"payment_id={event.get('payment_id')}, "
            f"tournament_id={event.get('tournament_id')}"
        )
    
    async def payment_verified(self, event: Dict[str, Any]):
        """
        Handle payment.verified event from channel layer.
        
        Module 3.2: Real-time payment verification updates
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'payment_id': int,
                    'registration_id': int,
                    'tournament_id': int,
                    'verified_by': str (username),
                    'timestamp': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='payment_verified' and event data
            
        Security:
            - Room isolation validated
            - Verified_by username exposed for transparency
        """
        # Validate room isolation
        if not self._validate_room_isolation(event.get('tournament_id')):
            return
        
        await self.send_json({
            'type': 'payment_verified',
            'data': {
                'payment_id': event.get('payment_id'),
                'registration_id': event.get('registration_id'),
                'tournament_id': event.get('tournament_id'),
                'verified_by': event.get('verified_by'),
                'timestamp': event.get('timestamp'),
            }
        })
        
        logger.info(
            f"Sent payment_verified event to user {self.user.username}: "
            f"payment_id={event.get('payment_id')}, "
            f"verified_by={event.get('verified_by')}"
        )
    
    async def payment_rejected(self, event: Dict[str, Any]):
        """
        Handle payment.rejected event from channel layer.
        
        Module 3.2: Real-time payment rejection updates
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'payment_id': int,
                    'registration_id': int,
                    'tournament_id': int,
                    'reason': str,
                    'timestamp': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='payment_rejected' and event data
            
        Security:
            - Room isolation validated
            - Reason exposed to guide resubmission
        """
        # Validate room isolation
        if not self._validate_room_isolation(event.get('tournament_id')):
            return
        
        await self.send_json({
            'type': 'payment_rejected',
            'data': {
                'payment_id': event.get('payment_id'),
                'registration_id': event.get('registration_id'),
                'tournament_id': event.get('tournament_id'),
                'reason': event.get('reason'),
                'timestamp': event.get('timestamp'),
            }
        })
        
        logger.info(
            f"Sent payment_rejected event to user {self.user.username}: "
            f"payment_id={event.get('payment_id')}, "
            f"reason={event.get('reason')[:50]}"  # Log first 50 chars
        )
    
    async def payment_refunded(self, event: Dict[str, Any]):
        """
        Handle payment.refunded event from channel layer.
        
        Module 3.2: Real-time payment refund updates
        
        Args:
            event: Event dict with 'type' and 'data' keys
                data: {
                    'payment_id': int,
                    'registration_id': int,
                    'tournament_id': int,
                    'reason': str,
                    'timestamp': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='payment_refunded' and event data
            
        Security:
            - Room isolation validated
            - Reason exposed for transparency
        """
        # Validate room isolation
        if not self._validate_room_isolation(event.get('tournament_id')):
            return
        
        await self.send_json({
            'type': 'payment_refunded',
            'data': {
                'payment_id': event.get('payment_id'),
                'registration_id': event.get('registration_id'),
                'tournament_id': event.get('tournament_id'),
                'reason': event.get('reason'),
                'timestamp': event.get('timestamp'),
            }
        })
        
        logger.info(
            f"Sent payment_refunded event to user {self.user.username}: "
            f"payment_id={event.get('payment_id')}, "
            f"reason={event.get('reason')[:50]}"
        )
    
    # -------------------------------------------------------------------------
    # Check-in Event Handlers (Module 3.4)
    # -------------------------------------------------------------------------
    
    async def registration_checked_in(self, event: Dict[str, Any]):
        """
        Handle registration_checked_in event from channel layer.
        
        Module 3.4: Real-time check-in updates
        
        Args:
            event: Event dict with 'type' and payload keys
                {
                    'type': 'registration_checked_in',
                    'tournament_id': int,
                    'registration_id': int,
                    'checked_in': bool (True),
                    'checked_in_at': str (ISO 8601),
                }
                
        Broadcasts to client:
            JSON message with type='registration_checked_in' and event data
            
        Security:
            - Room isolation validated
        """
        # Validate room isolation
        if not self._validate_room_isolation(event.get('tournament_id')):
            return
        
        await self.send_json({
            'type': 'registration_checked_in',
            'data': {
                'tournament_id': event.get('tournament_id'),
                'registration_id': event.get('registration_id'),
                'checked_in': event.get('checked_in'),
                'checked_in_at': event.get('checked_in_at'),
                # Note: checked_in_by field not yet in Registration model
            }
        })
        
        logger.info(
            f"Sent registration_checked_in event to user {self.user.username}: "
            f"registration_id={event.get('registration_id')}, "
            f"tournament_id={event.get('tournament_id')}"
        )
    
    async def registration_checkin_reverted(self, event: Dict[str, Any]):
        """
        Handle registration_checkin_reverted event from channel layer.
        
        Module 3.4: Real-time check-in undo updates
        
        Args:
            event: Event dict with 'type' and payload keys
                {
                    'type': 'registration_checkin_reverted',
                    'tournament_id': int,
                    'registration_id': int,
                    'checked_in': bool (False),
                    'checked_in_at': None,
                }
                
        Broadcasts to client:
            JSON message with type='registration_checkin_reverted' and event data
            
        Security:
            - Room isolation validated
        """
        # Validate room isolation
        if not self._validate_room_isolation(event.get('tournament_id')):
            return
        
        await self.send_json({
            'type': 'registration_checkin_reverted',
            'data': {
                'tournament_id': event.get('tournament_id'),
                'registration_id': event.get('registration_id'),
                'checked_in': event.get('checked_in'),
                'checked_in_at': event.get('checked_in_at'),
                # Note: checked_in_by field not yet in Registration model
            }
        })
        
        logger.info(
            f"Sent registration_checkin_reverted event to user {self.user.username}: "
            f"registration_id={event.get('registration_id')}, "
            f"tournament_id={event.get('tournament_id')}"
        )
    
    # -------------------------------------------------------------------------
    # Client Message Handling (Module 2.5: Schema Validation)
    # -------------------------------------------------------------------------
    
    async def receive_json(self, content: Dict[str, Any], **kwargs):
        """
        Handle JSON messages received from WebSocket client.
        
        Module 2.4: Validates user permissions for privileged actions.
        Module 2.5: Validates message schema and payload size.
        
        Currently broadcast-only - client messages logged but not processed.
        Future enhancement: Allow clients to request specific data or subscribe
        to specific match updates.
        
        Args:
            content: Parsed JSON message from client
            **kwargs: Additional keyword arguments
            
        Validation:
            - Requires 'type' field
            - Payload size checked by middleware (max 16 KB)
            - Action permissions checked against user role
        """
        # =====================================================================
        # MODULE 2.5: Schema Validation
        # =====================================================================
        
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
            f"Received message from user {self.user.username} (role={self.user_role.value}): "
            f"type={message_type}"
        )
        
        # =====================================================================
        # MODULE 2.4: Action Permission Validation
        # =====================================================================
        
        # Check if user has permission for this action
        if not await check_websocket_action_permission(self.user, message_type):
            logger.warning(
                f"Permission denied: user={self.user.username}, "
                f"role={self.user_role.value}, action={message_type}"
            )
            await self.send_json({
                'type': 'error',
                'code': 'insufficient_permissions',
                'message': f'Action "{message_type}" requires higher privileges. '
                          f'Your role: {self.user_role.value}',
            })
            return
        
        # =====================================================================
        # Message Type Handlers
        # =====================================================================
        
        if message_type == 'ping':
            # Heartbeat keepalive (allowed for all roles)
            await self.send_json({
                'type': 'pong',
                'timestamp': content.get('timestamp'),
            })
        
        elif message_type == 'subscribe':
            # Subscribe to tournament updates (allowed for all roles)
            await self.send_json({
                'type': 'subscribed',
                'data': {
                    'tournament_id': self.tournament_id,
                    'message': 'Successfully subscribed to tournament updates',
                }
            })
        
        # ---------------------------------------------------------------------
        # Player Actions (requires PLAYER role or higher)
        # ---------------------------------------------------------------------
        
        elif message_type == 'ready_up':
            # Player indicates readiness for match
            logger.info(
                f"Player ready: user={self.user.username}, tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'ready_acknowledged',
                'message': 'Ready status recorded',
            })
        
        elif message_type == 'report_score':
            # Player reports match score
            logger.info(
                f"Score report: user={self.user.username}, tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'score_report_received',
                'message': 'Score report submitted for verification',
            })
        
        elif message_type == 'submit_proof':
            # Player submits match proof
            logger.info(
                f"Proof submission: user={self.user.username}, tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'proof_received',
                'message': 'Proof submitted for review',
            })
        
        # ---------------------------------------------------------------------
        # Organizer Actions (requires ORGANIZER role or higher)
        # ---------------------------------------------------------------------
        
        elif message_type == 'update_score':
            # Organizer updates match score
            logger.info(
                f"Organizer score update: user={self.user.username}, "
                f"tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'score_updated_confirmed',
                'message': 'Score update processed',
            })
        
        elif message_type == 'verify_payment':
            # Organizer verifies payment
            logger.info(
                f"Payment verification: user={self.user.username}, "
                f"tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'payment_verified',
                'message': 'Payment verified',
            })
        
        elif message_type == 'start_match':
            # Organizer starts match
            logger.info(
                f"Match start: user={self.user.username}, tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'match_started_confirmed',
                'message': 'Match started',
            })
        
        # ---------------------------------------------------------------------
        # Admin Actions (requires ADMIN role)
        # ---------------------------------------------------------------------
        
        elif message_type == 'regenerate_bracket':
            # Admin regenerates bracket
            logger.info(
                f"Bracket regeneration: user={self.user.username}, "
                f"tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'bracket_regeneration_started',
                'message': 'Bracket regeneration initiated',
            })
        
        elif message_type == 'force_refund':
            # Admin forces refund
            logger.info(
                f"Force refund: user={self.user.username}, tournament={self.tournament_id}"
            )
            await self.send_json({
                'type': 'refund_processed',
                'message': 'Refund processed',
            })
        
        # ---------------------------------------------------------------------
        # Unknown Action
        # ---------------------------------------------------------------------
        
        else:
            # Unknown message type
            await self.send_json({
                'type': 'error',
                'code': 'unsupported_message_type',
                'message': f'Message type "{message_type}" not supported',
            })
    
    # =========================================================================
    # Helper Methods (Module 2.5)
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
    
    def _validate_room_isolation(self, event_tournament_id: int) -> bool:
        """
        Validate that event belongs to this consumer's tournament.
        
        Prevents cross-tournament event leakage.
        
        Args:
            event_tournament_id: Tournament ID from event data
        
        Returns:
            True if event belongs to this room, False otherwise
        """
        if event_tournament_id != self.tournament_id:
            logger.error(
                f"Room isolation violation: event for tournament {event_tournament_id} "
                f"received in room for tournament {self.tournament_id}"
            )
            return False
        
        return True

