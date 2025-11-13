"""
Rate Limiting Middleware for WebSocket Connections

Enforces connection and message rate limits to prevent abuse while allowing
legitimate traffic bursts. Applied transparently to TournamentConsumer.

Phase 2: Real-Time Features & Security
Module 2.5: Rate Limiting & Abuse Protection
Module 2.6: Realtime Monitoring & Logging Enhancement

Limits Enforced:
- Per-user concurrent connections (default: 3)
- Per-IP concurrent connections (default: 10)
- Per-user message rate (default: 10 msg/sec, burst 20)
- Per-IP message rate (default: 20 msg/sec, burst 40)
- Per-room membership cap (default: 2000)

On Limit Exceeded:
- Send error payload: {"type": "error", "code": "rate_limited", "retry_after_ms": <ms>}
- Close connection with policy code 4008 (Policy Violation)

Server→Client Messages: Never throttled (only client→server)
"""

import logging
import json
from typing import Optional

from channels.middleware import BaseMiddleware
from channels.exceptions import DenyConnection
from django.conf import settings

from .ratelimit import (
    check_and_consume,
    check_and_consume_ip,
    room_try_join,
    room_leave,
    increment_user_connections,
    decrement_user_connections,
    increment_ip_connections,
    decrement_ip_connections,
    get_user_connections,
    get_ip_connections,
)

# Module 2.6: Realtime Monitoring & Logging Enhancement
from . import logging as ws_logging
from . import metrics

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration (from settings.py with defaults)
# =============================================================================

def get_rate_config():
    """Get rate limit configuration from settings with fallbacks."""
    return {
        # Message rate limits
        'msg_rps': getattr(settings, 'WS_RATE_MSG_RPS', 10.0),
        'msg_burst': getattr(settings, 'WS_RATE_MSG_BURST', 20),
        'msg_rps_ip': getattr(settings, 'WS_RATE_MSG_RPS_IP', 20.0),
        'msg_burst_ip': getattr(settings, 'WS_RATE_MSG_BURST_IP', 40),
        
        # Connection limits
        'conn_per_user': getattr(settings, 'WS_RATE_CONN_PER_USER', 3),
        'conn_per_ip': getattr(settings, 'WS_RATE_CONN_PER_IP', 10),
        
        # Room limits
        'room_max_members': getattr(settings, 'WS_RATE_ROOM_MAX_MEMBERS', 2000),
        
        # Payload limits
        'max_payload_bytes': getattr(settings, 'WS_MAX_PAYLOAD_BYTES', 16 * 1024),  # 16 KB
    }


# =============================================================================
# Rate Limit Middleware
# =============================================================================

class RateLimitMiddleware(BaseMiddleware):
    """
    WebSocket rate limiting middleware.
    
    Wraps consumer to enforce connection and message rate limits.
    Should be applied in ASGI routing after JWTAuthMiddleware.
    
    Usage in asgi.py:
        application = ProtocolTypeRouter({
            "websocket": JWTAuthMiddleware(
                RateLimitMiddleware(
                    URLRouter(websocket_urlpatterns)
                )
            ),
        })
    """
    
    async def __call__(self, scope, receive, send):
        """
        Intercept WebSocket lifecycle to enforce rate limits.
        
        **STRICT BYPASS**: If WS_RATE_ENABLED=False, skip all rate limiting logic.
        This ensures tests and environments without Redis work without errors.
        
        Connection Phase:
        - Check per-user connection limit
        - Check per-IP connection limit
        - Check room capacity limit
        
        Message Phase:
        - Check per-user message rate
        - Check per-IP message rate
        - Validate payload size
        """
        # STRICT BYPASS: Skip all rate limiting if disabled
        # This ensures test environments work without Redis
        from django.conf import settings
        if not getattr(settings, "WS_RATE_ENABLED", False):
            logger.debug("Rate limiting disabled (WS_RATE_ENABLED=False), bypassing middleware")
            return await self.inner(scope, receive, send)
        
        # Get user and IP from scope
        user = scope.get('user')
        client_ip = self._get_client_ip(scope)
        
        # Get configuration
        config = get_rate_config()
        
        # Track connection attempt
        user_id = user.id if user and user.is_authenticated else None
        tournament_id = None  # Initialize for finally block
        
        # =================================================================
        # CONNECTION RATE LIMITING
        # =================================================================
        
        try:
            # Check per-user connection limit
            if user_id:
                current_conns = get_user_connections(user_id)
                if current_conns >= config['conn_per_user']:
                    logger.warning(
                        f"User {user_id} exceeded connection limit: "
                        f"{current_conns}/{config['conn_per_user']}"
                    )
                    
                    # Module 2.6: Log rate limit rejection
                    ws_logging.log_ratelimit_reject(
                        user_id=user_id,
                        tournament_id=tournament_id,
                        reason_code=ws_logging.ReasonCode.CONN_LIMIT,
                        retry_after_ms=5000
                    )
                    
                    # Module 2.6: Record rate limit event in metrics
                    metrics.record_ratelimit_event(
                        user_id=user_id,
                        reason=metrics.ReasonCode.CONN_LIMIT,
                        retry_after_ms=5000
                    )
                    
                    await self._send_rate_limit_error(
                        send,
                        code="connection_limit_exceeded",
                        message=f"Maximum {config['conn_per_user']} concurrent connections allowed",
                        retry_after_ms=5000
                    )
                    raise DenyConnection()
                
                # Increment connection count
                increment_user_connections(user_id)
            
            # Check per-IP connection limit
            if client_ip:
                current_ip_conns = get_ip_connections(client_ip)
                if current_ip_conns >= config['conn_per_ip']:
                    logger.warning(
                        f"IP {client_ip} exceeded connection limit: "
                        f"{current_ip_conns}/{config['conn_per_ip']}"
                    )
                    
                    # Decrement user connections if we incremented
                    if user_id:
                        decrement_user_connections(user_id)
                    
                    # Module 2.6: Log rate limit rejection (no IP in logs per IDs-only discipline)
                    ws_logging.log_ratelimit_reject(
                        user_id=user_id,
                        tournament_id=tournament_id,
                        reason_code=ws_logging.ReasonCode.CONN_LIMIT,
                        retry_after_ms=10000
                    )
                    
                    # Module 2.6: Record rate limit event in metrics
                    metrics.record_ratelimit_event(
                        user_id=user_id,
                        reason=metrics.ReasonCode.CONN_LIMIT,
                        retry_after_ms=10000
                    )
                    
                    await self._send_rate_limit_error(
                        send,
                        code="ip_connection_limit_exceeded",
                        message=f"Too many connections from this IP address",
                        retry_after_ms=10000
                    )
                    raise DenyConnection()
                
                # Increment IP connection count
                increment_ip_connections(client_ip)
            
            # Check room capacity (extract tournament_id from path)
            tournament_id = self._extract_tournament_id(scope)
            if tournament_id:
                room = f"tournament_{tournament_id}"
                allowed, room_size = room_try_join(
                    room=room,
                    user_id=user_id or 0,  # Use 0 for anonymous
                    max_members=config['room_max_members']
                )
                
                if not allowed:
                    logger.warning(
                        f"Tournament {tournament_id} room full: "
                        f"{room_size}/{config['room_max_members']}"
                    )
                    
                    # Decrement connection counts
                    if user_id:
                        decrement_user_connections(user_id)
                    if client_ip:
                        decrement_ip_connections(client_ip)
                    
                    # Module 2.6: Log rate limit rejection
                    ws_logging.log_ratelimit_reject(
                        user_id=user_id,
                        tournament_id=tournament_id,
                        reason_code=ws_logging.ReasonCode.ROOM_FULL,
                        retry_after_ms=30000
                    )
                    
                    # Module 2.6: Record rate limit event in metrics
                    metrics.record_ratelimit_event(
                        user_id=user_id,
                        reason=metrics.ReasonCode.ROOM_FULL,
                        retry_after_ms=30000
                    )
                    
                    await self._send_rate_limit_error(
                        send,
                        code="room_full",
                        message=f"Tournament room at capacity ({room_size} members)",
                        retry_after_ms=30000
                    )
                    raise DenyConnection()
                
                # Store room for cleanup on disconnect
                scope['tournament_room'] = room
            
            # =================================================================
            # MESSAGE RATE LIMITING (wrap receive)
            # =================================================================
            
            async def rate_limited_receive():
                """Wrap receive to enforce message rate limits."""
                message = await receive()
                
                # Only rate limit client→server messages
                if message.get('type') == 'websocket.receive':
                    # Check payload size
                    text = message.get('text', '')
                    payload_size = len(text.encode('utf-8'))
                    
                    if payload_size > config['max_payload_bytes']:
                        logger.warning(
                            f"User {user_id} sent oversized payload: "
                            f"{payload_size}/{config['max_payload_bytes']} bytes"
                        )
                        
                        # Module 2.6: Log rate limit rejection
                        ws_logging.log_ratelimit_reject(
                            user_id=user_id,
                            tournament_id=tournament_id,
                            reason_code=ws_logging.ReasonCode.PAYLOAD_TOO_BIG,
                            retry_after_ms=0
                        )
                        
                        # Module 2.6: Record rate limit event in metrics
                        metrics.record_ratelimit_event(
                            user_id=user_id,
                            reason=metrics.ReasonCode.PAYLOAD_TOO_BIG,
                            retry_after_ms=0
                        )
                        
                        # Send error and close connection
                        await self._send_rate_limit_error(
                            send,
                            code="payload_too_large",
                            message=f"Payload exceeds {config['max_payload_bytes']} bytes",
                            close=True
                        )
                        return {'type': 'websocket.disconnect', 'code': 4009}  # Message Too Big
                    
                    # Check per-user message rate
                    if user_id:
                        allowed, info = check_and_consume(
                            user_id=user_id,
                            key_suffix='msg',
                            rate_per_sec=config['msg_rps'],
                            burst=config['msg_burst']
                        )
                        
                        if not allowed:
                            retry_after_ms = info
                            logger.warning(
                                f"User {user_id} rate limited (message): "
                                f"retry after {retry_after_ms}ms"
                            )
                            
                            # Module 2.6: Log rate limit rejection
                            ws_logging.log_ratelimit_reject(
                                user_id=user_id,
                                tournament_id=tournament_id,
                                reason_code=ws_logging.ReasonCode.MSG_RATE,
                                retry_after_ms=retry_after_ms
                            )
                            
                            # Module 2.6: Record rate limit event in metrics
                            metrics.record_ratelimit_event(
                                user_id=user_id,
                                reason=metrics.ReasonCode.MSG_RATE,
                                retry_after_ms=retry_after_ms
                            )
                            
                            await self._send_rate_limit_error(
                                send,
                                code="message_rate_limit_exceeded",
                                message=f"Sending messages too fast",
                                retry_after_ms=retry_after_ms
                            )
                            
                            # Return empty receive (drop message but keep connection)
                            # Consumer won't process this message
                            return {'type': 'websocket.receive', 'text': ''}
                    
                    # Check per-IP message rate
                    if client_ip:
                        allowed, info = check_and_consume_ip(
                            ip_address=client_ip,
                            key_suffix='msg',
                            rate_per_sec=config['msg_rps_ip'],
                            burst=config['msg_burst_ip']
                        )
                        
                        if not allowed:
                            retry_after_ms = info
                            logger.warning(
                                f"IP {client_ip} rate limited (message): "
                                f"retry after {retry_after_ms}ms"
                            )
                            
                            # Module 2.6: Log rate limit rejection (no IP in logs per IDs-only discipline)
                            ws_logging.log_ratelimit_reject(
                                user_id=user_id,
                                tournament_id=tournament_id,
                                reason_code=ws_logging.ReasonCode.MSG_RATE,
                                retry_after_ms=retry_after_ms
                            )
                            
                            # Module 2.6: Record rate limit event in metrics
                            metrics.record_ratelimit_event(
                                user_id=user_id,
                                reason=metrics.ReasonCode.MSG_RATE,
                                retry_after_ms=retry_after_ms
                            )
                            
                            await self._send_rate_limit_error(
                                send,
                                code="ip_rate_limit_exceeded",
                                message=f"Too many messages from this IP",
                                retry_after_ms=retry_after_ms
                            )
                            
                            return {'type': 'websocket.receive', 'text': ''}
                
                return message
            
            # Call next middleware/consumer with rate-limited receive
            return await super().__call__(scope, rate_limited_receive, send)
        
        finally:
            # =================================================================
            # CLEANUP ON DISCONNECT
            # =================================================================
            
            # Decrement connection counts
            if user_id:
                decrement_user_connections(user_id)
            if client_ip:
                decrement_ip_connections(client_ip)
            
            # Remove from room
            if tournament_id and user_id:
                room = f"tournament_{tournament_id}"
                room_leave(room, user_id)
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    @staticmethod
    def _get_client_ip(scope) -> Optional[str]:
        """Extract client IP from scope headers."""
        # Check X-Forwarded-For header (if behind proxy)
        headers = dict(scope.get('headers', []))
        
        x_forwarded_for = headers.get(b'x-forwarded-for')
        if x_forwarded_for:
            # Get first IP (client)
            return x_forwarded_for.decode('utf-8').split(',')[0].strip()
        
        # Fallback to client in scope
        client = scope.get('client')
        if client:
            return client[0]  # (host, port) tuple
        
        return None
    
    @staticmethod
    def _extract_tournament_id(scope) -> Optional[int]:
        """Extract tournament_id from WebSocket path."""
        # Path format: /ws/tournament/<tournament_id>/
        path = scope.get('path', '')
        parts = path.strip('/').split('/')
        
        if len(parts) >= 3 and parts[0] == 'ws' and parts[1] == 'tournament':
            try:
                return int(parts[2])
            except (ValueError, IndexError):
                pass
        
        return None
    
    @staticmethod
    async def _send_rate_limit_error(
        send,
        code: str,
        message: str,
        retry_after_ms: int = 0,
        close: bool = False
    ):
        """
        Send rate limit error to client.
        
        Args:
            send: ASGI send callable
            code: Error code (e.g., "rate_limited", "room_full")
            message: Human-readable error message
            retry_after_ms: Milliseconds until client should retry
            close: Whether to close connection after error
        """
        error_payload = {
            'type': 'error',
            'code': code,
            'message': message,
        }
        
        if retry_after_ms > 0:
            error_payload['retry_after_ms'] = retry_after_ms
        
        try:
            # Send error message
            await send({
                'type': 'websocket.send',
                'text': json.dumps(error_payload)
            })
            
            # Close connection if requested
            if close:
                await send({
                    'type': 'websocket.close',
                    'code': 4008  # Policy Violation
                })
        except Exception as e:
            logger.error(f"Failed to send rate limit error: {e}", exc_info=True)


# =============================================================================
# Decorator for Consumer Methods (Optional)
# =============================================================================

def enforce_message_schema(required_fields=None):
    """
    Decorator to enforce message schema validation.
    
    Usage in consumer:
        @enforce_message_schema(required_fields=['action'])
        async def receive_json(self, content):
            # content guaranteed to have 'action' field
            ...
    """
    if required_fields is None:
        required_fields = []
    
    def decorator(func):
        async def wrapper(self, content, **kwargs):
            # Validate required fields
            missing_fields = [f for f in required_fields if f not in content]
            
            if missing_fields:
                logger.warning(f"Invalid message schema: missing {missing_fields}")
                
                # Send schema error
                await self.send_json({
                    'type': 'error',
                    'code': 'invalid_schema',
                    'message': f'Missing required fields: {", ".join(missing_fields)}',
                    'required_fields': required_fields
                })
                return
            
            # Call original method
            return await func(self, content, **kwargs)
        
        return wrapper
    return decorator
