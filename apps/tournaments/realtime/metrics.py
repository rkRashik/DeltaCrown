"""
WebSocket Realtime Monitoring - Metrics Module

Prometheus-style metrics instrumentation for WebSocket connections and message handling.
IDs-only discipline - no display names, usernames, emails, or IP addresses in metrics.

Phase 2: Real-Time Features & Security
Module 2.6: Monitoring & Logging Enhancement

Metrics Tracked:
- ws_connections_total: Connection lifecycle events (counter)
- ws_messages_total: Message handling events (counter)
- ws_ratelimit_events_total: Rate limit rejections (counter)
- ws_auth_failures_total: Authentication failures (counter)
- ws_message_latency_seconds: Message processing latency (histogram)
- ws_active_connections_gauge: Current active connections (gauge)

Label Structure:
- role: WebSocket role (SPECTATOR, PLAYER, ORGANIZER, ADMIN)
- scope_type: Room type (tournament, match, bracket)
- status: Event status (connected, disconnected, error)
- type: Message type (join, leave, score_update, dispute_update, heartbeat)
- reason: Reason code (MSG_RATE, CONN_LIMIT, ROOM_FULL, PAYLOAD_TOO_BIG, JWT_EXPIRED, JWT_INVALID, ROLE_NOT_ALLOWED)

PII Discipline:
- IDs only in logs/metrics: user_id, tournament_id, match_id
- No display names, usernames, emails
- No IP addresses (even for rate limiting events)
- Reason codes instead of free-form text

Usage Examples:
    from apps.tournaments.realtime.metrics import record_connection, record_message
    
    # Connection lifecycle
    record_connection(user_id, role='SPECTATOR', scope_type='tournament', status='connected')
    record_connection(user_id, role='SPECTATOR', scope_type='tournament', status='disconnected')
    
    # Message handling
    with record_message_latency(user_id, type='score_update'):
        await process_message(data)
    record_message(user_id, type='score_update', status='success')
    
    # Rate limit events
    record_ratelimit_event(user_id, reason='MSG_RATE', retry_after_ms=1000)
    
    # Auth failures
    record_auth_failure(reason='JWT_EXPIRED')
"""

import logging
from contextlib import contextmanager
from typing import Optional
from collections import defaultdict
from datetime import datetime
import threading

logger = logging.getLogger(__name__)

# =============================================================================
# In-Memory Metrics Storage (Simple Prometheus-Style)
# =============================================================================

# Thread-safe metrics storage
_metrics_lock = threading.Lock()

# Connection counters: {(role, scope_type, status): count}
_connection_counters = defaultdict(int)

# Message counters: {(type, status): count}
_message_counters = defaultdict(int)

# Rate limit counters: {(reason,): count}
_ratelimit_counters = defaultdict(int)

# Auth failure counters: {(reason,): count}
_auth_failure_counters = defaultdict(int)

# Message latency histogram: {(type,): [duration_ms, ...]}
_message_latency_histogram = defaultdict(list)

# Active connections gauge: {(role, scope_type): count}
_active_connections_gauge = defaultdict(int)


# =============================================================================
# Constants: Reason Codes (Avoid Stringly-Typed)
# =============================================================================

class ReasonCode:
    """Reason codes for rate limiting and auth failures (IDs-only discipline)."""
    
    # Rate limit reasons
    MSG_RATE = 'MSG_RATE'
    CONN_LIMIT = 'CONN_LIMIT'
    ROOM_FULL = 'ROOM_FULL'
    PAYLOAD_TOO_BIG = 'PAYLOAD_TOO_BIG'
    
    # Auth failure reasons
    JWT_EXPIRED = 'JWT_EXPIRED'
    JWT_INVALID = 'JWT_INVALID'
    ROLE_NOT_ALLOWED = 'ROLE_NOT_ALLOWED'


class MessageType:
    """Message types for WebSocket events."""
    
    JOIN = 'join'
    LEAVE = 'leave'
    SCORE_UPDATE = 'score_update'
    DISPUTE_UPDATE = 'dispute_update'
    HEARTBEAT = 'heartbeat'
    BRACKET_UPDATE = 'bracket_update'
    MATCH_STARTED = 'match_started'
    MATCH_COMPLETED = 'match_completed'


class ConnectionStatus:
    """Connection lifecycle statuses."""
    
    CONNECTED = 'connected'
    DISCONNECTED = 'disconnected'
    ERROR = 'error'


# =============================================================================
# Metrics Recording Functions
# =============================================================================

def record_connection(user_id: int, role: str, scope_type: str, status: str) -> None:
    """
    Record connection lifecycle event (counter + gauge).
    
    Args:
        user_id: User ID (IDs-only, no username/email)
        role: WebSocket role (SPECTATOR, PLAYER, ORGANIZER, ADMIN)
        scope_type: Room type (tournament, match, bracket)
        status: Event status (connected, disconnected, error)
        
    IDs-Only: user_id only, no display names or IP addresses
    """
    with _metrics_lock:
        # Increment counter
        _connection_counters[(role, scope_type, status)] += 1
        
        # Update gauge (active connections)
        if status == ConnectionStatus.CONNECTED:
            _active_connections_gauge[(role, scope_type)] += 1
        elif status == ConnectionStatus.DISCONNECTED:
            _active_connections_gauge[(role, scope_type)] = max(
                0, _active_connections_gauge[(role, scope_type)] - 1
            )
    
    logger.info(
        f"WebSocket connection event",
        extra={
            'user_id': user_id,
            'role': role,
            'scope_type': scope_type,
            'status': status,
            'metric': 'ws_connections_total',
        }
    )


def record_message(user_id: int, type: str, status: str = 'success') -> None:
    """
    Record message handling event (counter).
    
    Args:
        user_id: User ID (IDs-only)
        type: Message type (join, leave, score_update, etc.)
        status: Processing status (success, error)
        
    IDs-Only: user_id only
    """
    with _metrics_lock:
        _message_counters[(type, status)] += 1
    
    logger.info(
        f"WebSocket message handled",
        extra={
            'user_id': user_id,
            'type': type,
            'status': status,
            'metric': 'ws_messages_total',
        }
    )


def record_ratelimit_event(user_id: int, reason: str, retry_after_ms: int) -> None:
    """
    Record rate limit rejection event (counter).
    
    Args:
        user_id: User ID (IDs-only)
        reason: Reason code (MSG_RATE, CONN_LIMIT, ROOM_FULL, PAYLOAD_TOO_BIG)
        retry_after_ms: Retry-after duration in milliseconds
        
    IDs-Only: user_id only, no IP addresses logged
    """
    with _metrics_lock:
        _ratelimit_counters[(reason,)] += 1
    
    logger.warning(
        f"WebSocket rate limit exceeded",
        extra={
            'user_id': user_id,
            'reason': reason,
            'retry_after_ms': retry_after_ms,
            'metric': 'ws_ratelimit_events_total',
        }
    )


def record_auth_failure(reason: str, user_id: Optional[int] = None) -> None:
    """
    Record authentication failure event (counter).
    
    Args:
        reason: Reason code (JWT_EXPIRED, JWT_INVALID, ROLE_NOT_ALLOWED)
        user_id: User ID if available (IDs-only)
        
    IDs-Only: user_id only (if known), no usernames or emails
    """
    with _metrics_lock:
        _auth_failure_counters[(reason,)] += 1
    
    logger.warning(
        f"WebSocket authentication failure",
        extra={
            'user_id': user_id if user_id else 'unknown',
            'reason': reason,
            'metric': 'ws_auth_failures_total',
        }
    )


@contextmanager
def record_message_latency(user_id: int, type: str):
    """
    Record message processing latency (histogram).
    
    Args:
        user_id: User ID (IDs-only)
        type: Message type (join, leave, score_update, etc.)
        
    Usage:
        with record_message_latency(user_id, MessageType.SCORE_UPDATE):
            await process_score_update(data)
            
    IDs-Only: user_id only
    """
    start_time = datetime.now()
    try:
        yield
    finally:
        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        with _metrics_lock:
            _message_latency_histogram[(type,)].append(duration_ms)
        
        logger.info(
            f"WebSocket message latency",
            extra={
                'user_id': user_id,
                'type': type,
                'duration_ms': duration_ms,
                'metric': 'ws_message_latency_seconds',
            }
        )


# =============================================================================
# Metrics Snapshot API
# =============================================================================

def get_metrics_snapshot() -> dict:
    """
    Get current metrics snapshot (for monitoring/debugging).
    
    Returns:
        Dictionary with all metrics values:
        {
            'connections_total': {(role, scope_type, status): count},
            'messages_total': {(type, status): count},
            'ratelimit_events_total': {(reason,): count},
            'auth_failures_total': {(reason,): count},
            'message_latency_p50': {(type,): ms},
            'message_latency_p95': {(type,): ms},
            'message_latency_p99': {(type,): ms},
            'active_connections': {(role, scope_type): count},
        }
        
    PII Discipline: No user-specific data, only aggregated counts/percentiles
    """
    with _metrics_lock:
        snapshot = {
            'connections_total': dict(_connection_counters),
            'messages_total': dict(_message_counters),
            'ratelimit_events_total': dict(_ratelimit_counters),
            'auth_failures_total': dict(_auth_failure_counters),
            'active_connections': dict(_active_connections_gauge),
        }
        
        # Compute latency percentiles
        latency_p50 = {}
        latency_p95 = {}
        latency_p99 = {}
        
        for key, durations in _message_latency_histogram.items():
            if durations:
                sorted_durations = sorted(durations)
                n = len(sorted_durations)
                latency_p50[key] = sorted_durations[int(n * 0.50)] if n > 0 else 0.0
                latency_p95[key] = sorted_durations[int(n * 0.95)] if n > 0 else 0.0
                latency_p99[key] = sorted_durations[int(n * 0.99)] if n > 0 else 0.0
        
        snapshot['message_latency_p50'] = latency_p50
        snapshot['message_latency_p95'] = latency_p95
        snapshot['message_latency_p99'] = latency_p99
    
    return snapshot


def reset_metrics() -> None:
    """
    Reset all metrics (for testing only).
    
    WARNING: Do not call in production. This clears all counters and histograms.
    """
    with _metrics_lock:
        _connection_counters.clear()
        _message_counters.clear()
        _ratelimit_counters.clear()
        _auth_failure_counters.clear()
        _message_latency_histogram.clear()
        _active_connections_gauge.clear()
    
    logger.warning("WebSocket metrics reset (testing only)")


# =============================================================================
# Prometheus Export (Future)
# =============================================================================

def export_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus text format.
    
    Returns:
        Prometheus-formatted metrics string
        
    Future Enhancement: Integrate with django-prometheus or prometheus_client
    when deploying to production environment with Prometheus scraping.
    
    Example Output:
        # HELP ws_connections_total Total WebSocket connections
        # TYPE ws_connections_total counter
        ws_connections_total{role="SPECTATOR",scope_type="tournament",status="connected"} 1250
        ws_connections_total{role="SPECTATOR",scope_type="tournament",status="disconnected"} 1200
        
        # HELP ws_messages_total Total WebSocket messages
        # TYPE ws_messages_total counter
        ws_messages_total{type="score_update",status="success"} 4567
        ...
    """
    # TODO: Implement Prometheus text format exporter
    # For now, return empty string (placeholder)
    return ""
