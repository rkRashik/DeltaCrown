"""
WebSocket Realtime Monitoring - Structured Logging Module

Structured logging helpers for WebSocket connections and message handling.
IDs-only discipline - no display names, usernames, emails, or IP addresses in logs.

Phase 2: Real-Time Features & Security
Module 2.6: Monitoring & Logging Enhancement

Log Event Types:
- WS_CONNECT: Connection established
- WS_DISCONNECT: Connection closed
- WS_MESSAGE: Message processed
- WS_RATELIMIT_REJECT: Rate limit exceeded
- WS_AUTH_FAIL: Authentication failure
- WS_ERROR: General error

Log Fields (IDs-Only):
- event: Event type constant
- user_id: User ID (IDs-only, no username/email)
- tournament_id: Tournament ID (when applicable)
- match_id: Match ID (when applicable)
- role: WebSocket role (SPECTATOR, PLAYER, ORGANIZER, ADMIN)
- reason_code: Reason code for errors (MSG_RATE, JWT_EXPIRED, etc.)
- duration_ms: Processing duration in milliseconds

PII Discipline:
- IDs only: user_id, tournament_id, match_id
- No display names, usernames, emails
- No IP addresses (even for rate limiting events)
- Reason codes instead of free-form text

Usage Examples:
    from apps.tournaments.realtime.logging import log_ws_event, EventType, ReasonCode
    
    # Connection lifecycle
    log_ws_event(EventType.WS_CONNECT, user_id, tournament_id, role='SPECTATOR')
    log_ws_event(EventType.WS_DISCONNECT, user_id, tournament_id, role='SPECTATOR', duration_ms=1250)
    
    # Message handling
    log_ws_event(EventType.WS_MESSAGE, user_id, tournament_id, message_type='score_update', duration_ms=12)
    
    # Rate limit events
    log_ws_event(EventType.WS_RATELIMIT_REJECT, user_id, tournament_id, reason_code=ReasonCode.MSG_RATE, retry_after_ms=1000)
    
    # Auth failures
    log_ws_event(EventType.WS_AUTH_FAIL, user_id=None, reason_code=ReasonCode.JWT_EXPIRED)
"""

import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Constants: Event Types (Avoid Stringly-Typed)
# =============================================================================

class EventType:
    """Event types for WebSocket structured logging."""
    
    WS_CONNECT = 'WS_CONNECT'
    WS_DISCONNECT = 'WS_DISCONNECT'
    WS_MESSAGE = 'WS_MESSAGE'
    WS_RATELIMIT_REJECT = 'WS_RATELIMIT_REJECT'
    WS_AUTH_FAIL = 'WS_AUTH_FAIL'
    WS_ERROR = 'WS_ERROR'


class ReasonCode:
    """Reason codes for errors and rejections (IDs-only discipline)."""
    
    # Rate limit reasons
    MSG_RATE = 'MSG_RATE'
    CONN_LIMIT = 'CONN_LIMIT'
    ROOM_FULL = 'ROOM_FULL'
    PAYLOAD_TOO_BIG = 'PAYLOAD_TOO_BIG'
    
    # Auth failure reasons
    JWT_EXPIRED = 'JWT_EXPIRED'
    JWT_INVALID = 'JWT_INVALID'
    ROLE_NOT_ALLOWED = 'ROLE_NOT_ALLOWED'
    
    # General errors
    CONSUMER_ERROR = 'CONSUMER_ERROR'
    INVALID_MESSAGE_FORMAT = 'INVALID_MESSAGE_FORMAT'


# =============================================================================
# Structured Logging Functions
# =============================================================================

def log_ws_event(
    event: str,
    user_id: Optional[int] = None,
    tournament_id: Optional[int] = None,
    match_id: Optional[int] = None,
    role: Optional[str] = None,
    message_type: Optional[str] = None,
    reason_code: Optional[str] = None,
    retry_after_ms: Optional[int] = None,
    duration_ms: Optional[float] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Log structured WebSocket event with IDs-only discipline.
    
    Args:
        event: Event type (WS_CONNECT, WS_DISCONNECT, WS_MESSAGE, etc.)
        user_id: User ID (IDs-only, no username/email)
        tournament_id: Tournament ID (when applicable)
        match_id: Match ID (when applicable)
        role: WebSocket role (SPECTATOR, PLAYER, ORGANIZER, ADMIN)
        message_type: Message type (join, leave, score_update, etc.)
        reason_code: Reason code for errors (MSG_RATE, JWT_EXPIRED, etc.)
        retry_after_ms: Retry-after duration in milliseconds (for rate limits)
        duration_ms: Processing duration in milliseconds
        error_message: Error message (if applicable)
        
    IDs-Only Discipline:
        - user_id, tournament_id, match_id only (no display names, usernames, emails)
        - No IP addresses (even for rate limiting events)
        - Reason codes instead of free-form text
        
    Examples:
        >>> log_ws_event(EventType.WS_CONNECT, user_id=123, tournament_id=456, role='SPECTATOR')
        >>> log_ws_event(EventType.WS_RATELIMIT_REJECT, user_id=123, reason_code=ReasonCode.MSG_RATE, retry_after_ms=1000)
        >>> log_ws_event(EventType.WS_AUTH_FAIL, reason_code=ReasonCode.JWT_EXPIRED)
    """
    log_data = {
        'event': event,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    }
    
    # Add optional fields (IDs-only)
    if user_id is not None:
        log_data['user_id'] = user_id
    if tournament_id is not None:
        log_data['tournament_id'] = tournament_id
    if match_id is not None:
        log_data['match_id'] = match_id
    if role is not None:
        log_data['role'] = role
    if message_type is not None:
        log_data['message_type'] = message_type
    if reason_code is not None:
        log_data['reason_code'] = reason_code
    if retry_after_ms is not None:
        log_data['retry_after_ms'] = retry_after_ms
    if duration_ms is not None:
        log_data['duration_ms'] = duration_ms
    if error_message is not None:
        log_data['error_message'] = error_message
    
    # Choose log level based on event type
    if event in (EventType.WS_RATELIMIT_REJECT, EventType.WS_AUTH_FAIL, EventType.WS_ERROR):
        logger.warning(f"WebSocket event: {event}", extra=log_data)
    else:
        logger.info(f"WebSocket event: {event}", extra=log_data)


# =============================================================================
# Convenience Functions (Wrappers for Common Events)
# =============================================================================

def log_connect(
    user_id: int,
    tournament_id: int,
    role: str,
) -> None:
    """
    Log WebSocket connection event.
    
    Args:
        user_id: User ID (IDs-only)
        tournament_id: Tournament ID
        role: WebSocket role (SPECTATOR, PLAYER, ORGANIZER, ADMIN)
        
    Example:
        >>> log_connect(user_id=123, tournament_id=456, role='SPECTATOR')
    """
    log_ws_event(
        event=EventType.WS_CONNECT,
        user_id=user_id,
        tournament_id=tournament_id,
        role=role,
    )


def log_disconnect(
    user_id: int,
    tournament_id: int,
    role: str,
    duration_ms: float,
) -> None:
    """
    Log WebSocket disconnection event.
    
    Args:
        user_id: User ID (IDs-only)
        tournament_id: Tournament ID
        role: WebSocket role
        duration_ms: Connection duration in milliseconds
        
    Example:
        >>> log_disconnect(user_id=123, tournament_id=456, role='SPECTATOR', duration_ms=1250)
    """
    log_ws_event(
        event=EventType.WS_DISCONNECT,
        user_id=user_id,
        tournament_id=tournament_id,
        role=role,
        duration_ms=duration_ms,
    )


def log_message(
    user_id: int,
    tournament_id: int,
    message_type: str,
    duration_ms: float,
) -> None:
    """
    Log WebSocket message handling event.
    
    Args:
        user_id: User ID (IDs-only)
        tournament_id: Tournament ID
        message_type: Message type (join, leave, score_update, etc.)
        duration_ms: Processing duration in milliseconds
        
    Example:
        >>> log_message(user_id=123, tournament_id=456, message_type='score_update', duration_ms=12)
    """
    log_ws_event(
        event=EventType.WS_MESSAGE,
        user_id=user_id,
        tournament_id=tournament_id,
        message_type=message_type,
        duration_ms=duration_ms,
    )


def log_ratelimit_reject(
    user_id: int,
    tournament_id: int,
    reason_code: str,
    retry_after_ms: int,
) -> None:
    """
    Log WebSocket rate limit rejection event.
    
    Args:
        user_id: User ID (IDs-only)
        tournament_id: Tournament ID
        reason_code: Reason code (MSG_RATE, CONN_LIMIT, ROOM_FULL, PAYLOAD_TOO_BIG)
        retry_after_ms: Retry-after duration in milliseconds
        
    IDs-Only: No IP addresses logged (even for rate limiting events)
        
    Example:
        >>> log_ratelimit_reject(user_id=123, tournament_id=456, reason_code=ReasonCode.MSG_RATE, retry_after_ms=1000)
    """
    log_ws_event(
        event=EventType.WS_RATELIMIT_REJECT,
        user_id=user_id,
        tournament_id=tournament_id,
        reason_code=reason_code,
        retry_after_ms=retry_after_ms,
    )


def log_auth_failure(
    reason_code: str,
    user_id: Optional[int] = None,
) -> None:
    """
    Log WebSocket authentication failure event.
    
    Args:
        reason_code: Reason code (JWT_EXPIRED, JWT_INVALID, ROLE_NOT_ALLOWED)
        user_id: User ID if available (IDs-only)
        
    IDs-Only: user_id only (if known), no usernames or emails
        
    Example:
        >>> log_auth_failure(reason_code=ReasonCode.JWT_EXPIRED, user_id=123)
        >>> log_auth_failure(reason_code=ReasonCode.JWT_INVALID)  # user_id unknown
    """
    log_ws_event(
        event=EventType.WS_AUTH_FAIL,
        user_id=user_id,
        reason_code=reason_code,
    )


def log_error(
    user_id: Optional[int],
    tournament_id: Optional[int],
    reason_code: str,
    error_message: str,
) -> None:
    """
    Log WebSocket general error event.
    
    Args:
        user_id: User ID if available (IDs-only)
        tournament_id: Tournament ID if available
        reason_code: Reason code (CONSUMER_ERROR, INVALID_MESSAGE_FORMAT, etc.)
        error_message: Error message (brief, no PII)
        
    IDs-Only: user_id, tournament_id only
        
    Example:
        >>> log_error(user_id=123, tournament_id=456, reason_code=ReasonCode.CONSUMER_ERROR, error_message="Unexpected consumer exception")
    """
    log_ws_event(
        event=EventType.WS_ERROR,
        user_id=user_id,
        tournament_id=tournament_id,
        reason_code=reason_code,
        error_message=error_message,
    )
