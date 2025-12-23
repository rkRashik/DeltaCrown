"""
Audit Service (UP-M5)

Centralized audit logging for user profile changes.
Enforces immutability, privacy-safety, and idempotency.

Design Principles:
1. Single write path: All audit events go through record_event()
2. Immutable: Records cannot be updated or deleted
3. Privacy-safe: Never store PII (emails, passwords, tokens, etc.)
4. Minimal: Only log material changes (projection updates, admin actions)

Usage:
    from apps.user_profile.services.audit import AuditService
    from apps.user_profile.models.audit import UserAuditEvent
    
    # Record a public ID assignment
    AuditService.record_event(
        subject_user_id=user.id,
        event_type=UserAuditEvent.EventType.PUBLIC_ID_ASSIGNED,
        source_app='user_profile',
        object_type='UserProfile',
        object_id=profile.id,
        after_snapshot={'public_id': profile.public_id},
        metadata={'reason': 'auto-assignment'}
    )
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from typing import Optional, Dict, Any
import logging

from apps.user_profile.models.audit import UserAuditEvent

User = get_user_model()
logger = logging.getLogger(__name__)


class AuditService:
    """
    Centralized audit service for user profile changes.
    
    All audit events MUST go through record_event() to enforce:
    - Immutability (append-only)
    - Privacy-safety (PII redaction)
    - Standardized logging
    """
    
    # Fields that must NEVER be stored in snapshots (privacy/security)
    FORBIDDEN_FIELDS = {
        'password', 'password_hash', 'oauth_token', 'access_token', 'refresh_token',
        'api_key', 'secret', 'email', 'phone', 'ssn', 'kyc_document'
    }
    
    @classmethod
    @transaction.atomic
    def record_event(
        cls,
        *,
        subject_user_id: int,
        event_type: str,
        source_app: str,
        object_type: str,
        object_id: int,
        actor_user_id: Optional[int] = None,
        before_snapshot: Optional[Dict[str, Any]] = None,
        after_snapshot: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserAuditEvent:
        """
        Record an audit event (immutable, append-only).
        
        Args:
            subject_user_id: User whose data was affected
            event_type: Type of event (from UserAuditEvent.EventType)
            source_app: Source app (user_profile, economy, tournaments, etc.)
            object_type: Type of object changed (UserProfile, UserProfileStats, etc.)
            object_id: ID of object changed
            actor_user_id: User who performed action (None for system)
            before_snapshot: State before change (privacy-safe fields only)
            after_snapshot: State after change (privacy-safe fields only)
            metadata: Additional context
            request_id: Request ID for correlation
            idempotency_key: Idempotency key for deduplication
            ip_address: IP address of requester
            user_agent: User agent string
            
        Returns:
            UserAuditEvent: Created audit event
            
        Raises:
            ValueError: If forbidden fields detected in snapshots
        """
        # Redact forbidden fields from snapshots
        if before_snapshot:
            before_snapshot = cls._redact_snapshot(before_snapshot)
        
        if after_snapshot:
            after_snapshot = cls._redact_snapshot(after_snapshot)
        
        # Create immutable audit record
        event = UserAuditEvent.objects.create(
            actor_user_id=actor_user_id,
            subject_user_id=subject_user_id,
            event_type=event_type,
            source_app=source_app,
            object_type=object_type,
            object_id=object_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
            ip_address=ip_address,
            user_agent=user_agent,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            metadata=metadata or {}
        )
        
        logger.info(
            f"Audit event recorded: {event_type} for user_id={subject_user_id} "
            f"(actor={actor_user_id or 'SYSTEM'}, object={object_type}:{object_id})"
        )
        
        return event
    
    @classmethod
    def _redact_snapshot(cls, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove forbidden fields from snapshot (privacy/security).
        
        Args:
            snapshot: Snapshot dict
            
        Returns:
            Dict: Redacted snapshot
            
        Raises:
            ValueError: If forbidden fields detected
        """
        if not isinstance(snapshot, dict):
            return snapshot
        
        # Check for forbidden fields
        forbidden_found = set(snapshot.keys()) & cls.FORBIDDEN_FIELDS
        if forbidden_found:
            raise ValueError(
                f"Forbidden fields in snapshot: {forbidden_found}. "
                f"Never store PII/secrets in audit logs."
            )
        
        # Recursively redact nested dicts
        redacted = {}
        for key, value in snapshot.items():
            if isinstance(value, dict):
                redacted[key] = cls._redact_snapshot(value)
            else:
                redacted[key] = value
        
        return redacted
    
    @classmethod
    def compute_diff(cls, before: Optional[Dict], after: Optional[Dict]) -> Dict[str, Any]:
        """
        Compute diff between before/after snapshots.
        
        Args:
            before: Before state
            after: After state
            
        Returns:
            Dict: {
                'added': dict of new fields,
                'removed': dict of removed fields,
                'changed': dict of changed fields with (old, new) tuples
            }
        """
        if not before and not after:
            return {'added': {}, 'removed': {}, 'changed': {}}
        
        if not before:
            return {'added': after or {}, 'removed': {}, 'changed': {}}
        
        if not after:
            return {'added': {}, 'removed': before or {}, 'changed': {}}
        
        before_keys = set(before.keys())
        after_keys = set(after.keys())
        
        added = {k: after[k] for k in after_keys - before_keys}
        removed = {k: before[k] for k in before_keys - after_keys}
        changed = {}
        
        for k in before_keys & after_keys:
            if before[k] != after[k]:
                changed[k] = (before[k], after[k])
        
        return {
            'added': added,
            'removed': removed,
            'changed': changed
        }
