"""
Observability hooks for moderation enforcement.

Test-only event emitter interface. Disabled by default.
Allows tests to observe enforcement decisions without side effects.

Events emitted:
- sanction.gate_check: WebSocket or purchase gate decision
- sanction.created: New sanction created
- sanction.revoked: Existing sanction revoked
- report.triaged: Report triage completed

All payloads use IDs only - NO PII (no username/email/IP).
"""
from typing import Dict, Any, Optional, List
from django.conf import settings
import logging
import time

logger = logging.getLogger(__name__)


class ModerationEventEmitter:
    """
    Test-only event emitter for moderation operations.
    
    In production: disabled by default (MODERATION_OBSERVABILITY_ENABLED=False).
    In tests: enable via override_settings to observe enforcement decisions.
    
    Supports sampling via MODERATION_OBSERVABILITY_SAMPLE_RATE (0.0-1.0).
    """
    
    def __init__(self):
        self._events: List[Dict[str, Any]] = []
    
    def emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        """
        Emit an observability event (subject to sampling).
        
        Args:
            event_name: Event type (e.g. "sanction.gate_check")
            payload: Event data (must contain only IDs, no PII)
        """
        # Check flag dynamically (allows override_settings to work)
        if not getattr(settings, 'MODERATION_OBSERVABILITY_ENABLED', False):
            return
        
        # Apply sampling
        sample_rate = getattr(settings, 'MODERATION_OBSERVABILITY_SAMPLE_RATE', 0.0)
        if not self._should_sample(sample_rate):
            return
        
        # Validate: NO PII in payload
        self._validate_no_pii(payload)
        
        event = {
            'event': event_name,
            'timestamp': time.time(),
            'payload': payload
        }
        
        self._events.append(event)
        
        # Lightweight logging (IDs only)
        logger.info(
            f"Moderation event: {event_name}",
            extra={'event_data': payload}
        )
    
    def _validate_no_pii(self, payload: Dict[str, Any]) -> None:
        """Ensure payload contains NO username/email/IP."""
        payload_str = str(payload).lower()
        
        # Check for common PII field names
        pii_fields = ['username', 'email', 'ip', 'ip_address', 'user_email']
        for field in pii_fields:
            if field in payload_str:
                raise ValueError(f"PII leak: '{field}' found in observability payload")
    
    def get_events(self, event_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve emitted events (test utility)."""
        if event_name:
            return [e for e in self._events if e['event'] == event_name]
        return self._events.copy()
    
    def clear(self) -> None:
        """Clear event buffer (test utility)."""
        self._events.clear()
    
    def _should_sample(self, rate: float) -> bool:
        """
        Determine if event should be sampled based on rate.
        
        Args:
            rate: Sampling rate (0.0 = none, 1.0 = all)
        
        Returns:
            True if event should be emitted
        """
        import random
        
        if rate <= 0.0:
            return False
        if rate >= 1.0:
            return True
        
        return random.random() < rate


# Emitter protocol for extensibility (test sinks, future integrations)
class EmitterProtocol:
    """
    Protocol for observability event sinks.
    
    Implementations can send events to:
    - Test buffers (in-memory for assertions)
    - Logging systems (structured logs)
    - Metrics backends (StatsD, Prometheus)
    - External observability platforms (Datadog, Sentry)
    
    All implementations must enforce zero-PII guarantee.
    """
    
    def emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Emit an event to the sink."""
        raise NotImplementedError
    
    def clear(self) -> None:
        """Clear sink state (test utility)."""
        raise NotImplementedError


class TestSink(EmitterProtocol):
    """
    Test-only sink that buffers events in memory.
    
    Use this in tests to assert on emitted events without side effects.
    """
    
    def __init__(self):
        self._buffer: List[Dict[str, Any]] = []
    
    def emit(self, event_name: str, payload: Dict[str, Any]) -> None:
        """Buffer event in memory."""
        self._buffer.append({
            'event': event_name,
            'timestamp': time.time(),
            'payload': payload
        })
    
    def clear(self) -> None:
        """Clear buffer."""
        self._buffer.clear()
    
    def get_events(self, event_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve buffered events."""
        if event_name:
            return [e for e in self._buffer if e['event'] == event_name]
        return self._buffer.copy()


# Global singleton (test-only, disabled in production)
_emitter = ModerationEventEmitter()


def emit_gate_check(
    gate_type: str,
    user_id: int,
    allowed: bool,
    reason_code: Optional[str],
    sanction_id: Optional[int],
    duration_ms: float,
    scope: Optional[str] = None,
    scope_id: Optional[int] = None
) -> None:
    """
    Emit a gate check event.
    
    Args:
        gate_type: "websocket" or "purchase"
        user_id: User being checked
        allowed: Whether access was granted
        reason_code: Denial reason (if blocked)
        sanction_id: Active sanction ID (if blocked)
        duration_ms: Gate check latency
        scope: "global" or "tournament" (if applicable)
        scope_id: Tournament ID (if tournament-scoped)
    """
    _emitter.emit('sanction.gate_check', {
        'gate_type': gate_type,
        'user_id': user_id,
        'allowed': allowed,
        'reason_code': reason_code,
        'sanction_id': sanction_id,
        'duration_ms': round(duration_ms, 2),
        'scope': scope,
        'scope_id': scope_id
    })


def emit_sanction_created(
    sanction_id: int,
    subject_profile_id: int,
    type: str,
    scope: str,
    scope_id: Optional[int]
) -> None:
    """Emit sanction creation event."""
    _emitter.emit('sanction.created', {
        'sanction_id': sanction_id,
        'subject_profile_id': subject_profile_id,
        'type': type,
        'scope': scope,
        'scope_id': scope_id
    })


def emit_sanction_revoked(
    sanction_id: int,
    subject_profile_id: int,
    revoked_by_id: int
) -> None:
    """Emit sanction revocation event."""
    _emitter.emit('sanction.revoked', {
        'sanction_id': sanction_id,
        'subject_profile_id': subject_profile_id,
        'revoked_by_id': revoked_by_id
    })


def emit_report_triaged(
    report_id: int,
    reporter_id: int,
    subject_profile_id: int,
    action_taken: str
) -> None:
    """Emit report triage event."""
    _emitter.emit('report.triaged', {
        'report_id': report_id,
        'reporter_id': reporter_id,
        'subject_profile_id': subject_profile_id,
        'action_taken': action_taken
    })


def get_emitter() -> ModerationEventEmitter:
    """Get global emitter instance (test utility)."""
    return _emitter
