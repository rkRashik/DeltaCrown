"""
Sanctions Service

Provides idempotent, atomic operations for account sanctions.

API:
- create_sanction(): Issue a sanction with idempotency
- revoke_sanction(): Revoke a sanction atomically
- is_sanctioned(): Query if user is currently sanctioned
- effective_policies(): Get all active sanctions for a user
"""
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.db.models import Q

from apps.moderation.models import ModerationSanction, ModerationAudit


def create_sanction(
    subject_id,
    *,
    type,
    scope,
    scope_id=None,
    reason_code,
    starts_at=None,
    ends_at=None,
    idempotency_key=None,
    notes=None,
    issued_by=None,
):
    """
    Create a moderation sanction with idempotency.
    
    Args:
        subject_id: User profile ID being sanctioned
        type: 'ban', 'suspend', or 'mute'
        scope: 'global' or 'tournament'
        scope_id: Tournament ID (required if scope='tournament')
        reason_code: Short code for sanction reason
        starts_at: When sanction begins (default: now)
        ends_at: When sanction ends (None = permanent)
        idempotency_key: Unique key for replay protection
        notes: Dict of additional metadata
        issued_by: User profile ID of issuer (None = system)
    
    Returns:
        dict: {
            'sanction_id': int,
            'created': bool,  # False if replayed
            'subject_profile_id': int,
            'type': str,
            'scope': str,
            'starts_at': str (ISO),
            'ends_at': str (ISO) or None,
        }
    
    Raises:
        ValueError: Invalid parameters
        IntegrityError: Database constraint violation (re-raised for logging)
    """
    # Validate required fields
    if not subject_id:
        raise ValueError("subject_id is required")
    if type not in ['ban', 'suspend', 'mute']:
        raise ValueError(f"Invalid type: {type}")
    if scope not in ['global', 'tournament']:
        raise ValueError(f"Invalid scope: {scope}")
    if scope == 'tournament' and not scope_id:
        raise ValueError("scope_id required when scope='tournament'")
    if not reason_code:
        raise ValueError("reason_code is required")
    
    # Validate time window
    starts_at = starts_at or timezone.now()
    if ends_at and ends_at <= starts_at:
        raise ValueError("ends_at must be after starts_at")
    
    # Build sanction object
    sanction_data = {
        'subject_profile_id': subject_id,
        'type': type,
        'scope': scope,
        'scope_id': scope_id,
        'reason_code': reason_code,
        'notes': notes or {},
        'issued_by': issued_by,
        'starts_at': starts_at,
        'ends_at': ends_at,
        'idempotency_key': idempotency_key,
    }
    
    # Idempotency: check for existing sanction with same key
    if idempotency_key:
        existing = ModerationSanction.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return {
                'sanction_id': existing.id,
                'created': False,
                'subject_profile_id': existing.subject_profile_id,
                'type': existing.type,
                'scope': existing.scope,
                'starts_at': existing.starts_at.isoformat(),
                'ends_at': existing.ends_at.isoformat() if existing.ends_at else None,
            }
    
    # Create sanction atomically
    with transaction.atomic():
        sanction = ModerationSanction.objects.create(**sanction_data)
        
        # Write audit trail
        ModerationAudit.objects.create(
            event='sanction_created',
            actor_id=issued_by,
            subject_profile_id=subject_id,
            ref_type='sanction',
            ref_id=sanction.id,
            meta={
                'type': type,
                'scope': scope,
                'scope_id': scope_id,
                'reason_code': reason_code,
                'starts_at': starts_at.isoformat(),
                'ends_at': ends_at.isoformat() if ends_at else None,
            }
        )
    
    return {
        'sanction_id': sanction.id,
        'created': True,
        'subject_profile_id': sanction.subject_profile_id,
        'type': sanction.type,
        'scope': sanction.scope,
        'starts_at': sanction.starts_at.isoformat(),
        'ends_at': sanction.ends_at.isoformat() if sanction.ends_at else None,
    }


def revoke_sanction(
    sanction_id,
    *,
    idempotency_key=None,
    revoked_by=None,
    notes=None,
):
    """
    Revoke a sanction atomically.
    
    Args:
        sanction_id: ID of sanction to revoke
        idempotency_key: Unique key for replay protection
        revoked_by: User profile ID of revoker (None = system)
        notes: Dict of additional metadata
    
    Returns:
        dict: {
            'sanction_id': int,
            'revoked': bool,  # False if already revoked or replayed
            'revoked_at': str (ISO) or None,
        }
    
    Raises:
        ValueError: Sanction not found
    """
    with transaction.atomic():
        # Lock row for update
        try:
            sanction = ModerationSanction.objects.select_for_update().get(id=sanction_id)
        except ModerationSanction.DoesNotExist:
            raise ValueError(f"Sanction {sanction_id} not found")
        
        # Idempotency: check if already revoked
        if sanction.revoked_at:
            return {
                'sanction_id': sanction.id,
                'revoked': False,
                'revoked_at': sanction.revoked_at.isoformat(),
            }
        
        # Revoke sanction
        now = timezone.now()
        sanction.revoked_at = now
        sanction.save(update_fields=['revoked_at'])
        
        # Write audit trail
        ModerationAudit.objects.create(
            event='sanction_revoked',
            actor_id=revoked_by,
            subject_profile_id=sanction.subject_profile_id,
            ref_type='sanction',
            ref_id=sanction.id,
            meta={
                'revoked_at': now.isoformat(),
                'notes': notes or {},
            }
        )
    
    return {
        'sanction_id': sanction.id,
        'revoked': True,
        'revoked_at': now.isoformat(),
    }


def is_sanctioned(
    subject_id,
    *,
    type=None,
    scope=None,
    scope_id=None,
    at=None,
):
    """
    Check if a user is currently sanctioned.
    
    Args:
        subject_id: User profile ID to check
        type: Filter by sanction type ('ban', 'suspend', 'mute')
        scope: Filter by scope ('global', 'tournament')
        scope_id: Filter by tournament ID (requires scope='tournament')
        at: Check sanctions active at this time (default: now)
    
    Returns:
        bool: True if user has matching active sanction
    """
    at = at or timezone.now()
    
    # Build query
    q = Q(subject_profile_id=subject_id)
    q &= Q(revoked_at__isnull=True)
    q &= Q(starts_at__lte=at)
    q &= Q(ends_at__isnull=True) | Q(ends_at__gt=at)
    
    if type:
        q &= Q(type=type)
    if scope:
        q &= Q(scope=scope)
    if scope_id is not None:
        q &= Q(scope_id=scope_id)
    
    return ModerationSanction.objects.filter(q).exists()


def effective_policies(subject_id, *, at=None):
    """
    Get all active sanctions for a user.
    
    Args:
        subject_id: User profile ID to check
        at: Check sanctions active at this time (default: now)
    
    Returns:
        dict: {
            'subject_profile_id': int,
            'has_sanctions': bool,
            'sanctions': [
                {
                    'sanction_id': int,
                    'type': str,
                    'scope': str,
                    'scope_id': int or None,
                    'reason_code': str,
                    'starts_at': str (ISO),
                    'ends_at': str (ISO) or None,
                },
                ...
            ]
        }
    """
    at = at or timezone.now()
    
    # Query active sanctions
    q = Q(subject_profile_id=subject_id)
    q &= Q(revoked_at__isnull=True)
    q &= Q(starts_at__lte=at)
    q &= Q(ends_at__isnull=True) | Q(ends_at__gt=at)
    
    sanctions = ModerationSanction.objects.filter(q).order_by('-created_at')
    
    return {
        'subject_profile_id': subject_id,
        'has_sanctions': sanctions.exists(),
        'sanctions': [
            {
                'sanction_id': s.id,
                'type': s.type,
                'scope': s.scope,
                'scope_id': s.scope_id,
                'reason_code': s.reason_code,
                'starts_at': s.starts_at.isoformat(),
                'ends_at': s.ends_at.isoformat() if s.ends_at else None,
            }
            for s in sanctions
        ]
    }
