"""
Moderation enforcement middleware and gates.

Provides runtime integration points for moderation sanctions:
- WebSocket CONNECT denial for banned/suspended users
- Economy/Shop purchase denial for banned/muted users

All enforcement is feature-flag guarded (default OFF).
Zero behavior change until flags are explicitly enabled.

PII Discipline: IDs only in logs/errors; never usernames/emails.
"""
from typing import Optional, Dict, Any
from django.conf import settings
from django.core.cache import cache

from apps.moderation.services.sanctions_service import is_sanctioned, effective_policies
from apps.moderation.models import ModerationSanction
from django.utils import timezone
from django.db.models import Q


def should_enforce_moderation() -> bool:
    """
    Check if moderation enforcement is globally enabled.
    
    Returns:
        bool: True if MODERATION_ENFORCEMENT_ENABLED flag is True
    """
    return getattr(settings, 'MODERATION_ENFORCEMENT_ENABLED', False)


def check_websocket_access(
    user_id: int,
    tournament_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check if user can access WebSocket connections (tournament chat, live updates).
    
    Blocks CONNECT for:
    - Active BAN (global or tournament-scoped)
    - Active SUSPEND (global or tournament-scoped)
    
    Allows CONNECT for:
    - MUTE (restricts message sending, not connection)
    - No active sanctions
    - Revoked sanctions
    
    Args:
        user_id: User ID to check
        tournament_id: Optional tournament ID for scoped check
    
    Returns:
        dict: {
            'allowed': bool,
            'reason_code': str | None,  # 'BANNED', 'SUSPENDED', None
            'sanction_id': int | None    # For audit/logging
        }
    
    PII: Only user_id/tournament_id in logs; no usernames/emails.
    """
    # Feature flag guard: if enforcement disabled, allow all
    if not should_enforce_moderation():
        return {'allowed': True, 'reason_code': None, 'sanction_id': None}
    
    if not getattr(settings, 'MODERATION_ENFORCEMENT_WS', False):
        return {'allowed': True, 'reason_code': None, 'sanction_id': None}
    
    # Check for blocking sanctions (BAN or SUSPEND)
    # MUTE does not block WebSocket connection
    
    # Check for BAN
    if is_sanctioned(subject_id=user_id, type='ban', scope_id=tournament_id):
        # Get the actual sanction for audit purposes
        sanction = ModerationSanction.objects.filter(
            subject_profile_id=user_id,
            type='ban',
            revoked_at__isnull=True,
            starts_at__lte=timezone.now()
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gt=timezone.now())
        ).filter(
            Q(scope='global') | Q(scope_id=tournament_id) if tournament_id else Q()
        ).first()
        
        return {
            'allowed': False,
            'reason_code': 'BANNED',
            'sanction_id': sanction.id if sanction else None
        }
    
    # Check for SUSPEND
    if is_sanctioned(subject_id=user_id, type='suspend', scope_id=tournament_id):
        sanction = ModerationSanction.objects.filter(
            subject_profile_id=user_id,
            type='suspend',
            revoked_at__isnull=True,
            starts_at__lte=timezone.now()
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gt=timezone.now())
        ).filter(
            Q(scope='global') | Q(scope_id=tournament_id) if tournament_id else Q()
        ).first()
        
        return {
            'allowed': False,
            'reason_code': 'SUSPENDED',
            'sanction_id': sanction.id if sanction else None
        }
    
    # No blocking sanctions
    return {'allowed': True, 'reason_code': None, 'sanction_id': None}


def check_purchase_access(
    user_id: int,
    tournament_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check if user can make economy/shop purchases.
    
    Blocks purchases for:
    - Active BAN (global or tournament-scoped)
    - Active MUTE (prevents all economy interactions per policy)
    
    Allows purchases for:
    - SUSPEND (tournament participation blocked, but purchases allowed)
    - No active sanctions
    - Revoked sanctions
    
    Args:
        user_id: User ID to check
        tournament_id: Optional tournament ID for scoped check
    
    Returns:
        dict: {
            'allowed': bool,
            'reason_code': str | None,  # 'BANNED', 'MUTED', None
            'sanction_id': int | None    # For audit/logging
        }
    
    PII: Only user_id/tournament_id in logs; no usernames/emails.
    """
    # Feature flag guard: if enforcement disabled, allow all
    if not should_enforce_moderation():
        return {'allowed': True, 'reason_code': None, 'sanction_id': None}
    
    if not getattr(settings, 'MODERATION_ENFORCEMENT_PURCHASE', False):
        return {'allowed': True, 'reason_code': None, 'sanction_id': None}
    
    # Check for blocking sanctions (BAN or MUTE)
    # SUSPEND does NOT block purchases
    
    # Build query for active sanctions
    now = timezone.now()
    base_query = Q(
        subject_profile_id=user_id,
        revoked_at__isnull=True,
        starts_at__lte=now
    ) & (Q(ends_at__isnull=True) | Q(ends_at__gt=now))
    
    # Scope filter: global always applies, tournament-scoped only if tournament_id matches
    if tournament_id is not None:
        scope_query = Q(scope='global') | Q(scope='tournament', scope_id=tournament_id)
    else:
        # No tournament context: only global sanctions apply
        scope_query = Q(scope='global')
    
    # Check for BAN
    ban = ModerationSanction.objects.filter(
        base_query & scope_query & Q(type='ban')
    ).first()
    
    if ban:
        return {
            'allowed': False,
            'reason_code': 'BANNED',
            'sanction_id': ban.id
        }
    
    # Check for MUTE
    mute = ModerationSanction.objects.filter(
        base_query & scope_query & Q(type='mute')
    ).first()
    
    if mute:
        return {
            'allowed': False,
            'reason_code': 'MUTED',
            'sanction_id': mute.id
        }
    
    # No blocking sanctions
    return {'allowed': True, 'reason_code': None, 'sanction_id': None}


def get_all_active_policies(
    user_id: int,
    tournament_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get comprehensive view of all active sanctions affecting user.
    
    Useful for UI display (showing why actions are blocked) and
    admin dashboards (seeing full sanction state).
    
    Args:
        user_id: User ID to check
        tournament_id: Optional tournament ID for scoped check
    
    Returns:
        dict: {
            'has_active_sanctions': bool,
            'sanctions': List[dict],  # Each with type, scope, expires_at, reason
            'blocked_actions': List[str]  # e.g., ['WEBSOCKET', 'PURCHASE']
        }
    
    PII: Only user_id/tournament_id; no usernames/emails in response.
    """
    policies = effective_policies(subject_id=user_id)
    
    blocked_actions = []
    
    # Filter by tournament_id if specified
    relevant_sanctions = policies['sanctions']
    if tournament_id is not None:
        relevant_sanctions = [
            s for s in policies['sanctions']
            if s['scope'] == 'global' or (s['scope'] == 'tournament' and s['scope_id'] == tournament_id)
        ]
    
    # Determine which actions are blocked
    for sanction in relevant_sanctions:
        sanction_type = sanction['type']
        
        if sanction_type in ('ban', 'suspend'):
            if 'WEBSOCKET' not in blocked_actions:
                blocked_actions.append('WEBSOCKET')
        
        if sanction_type in ('ban', 'mute'):
            if 'PURCHASE' not in blocked_actions:
                blocked_actions.append('PURCHASE')
    
    return {
        'has_active_sanctions': len(relevant_sanctions) > 0,
        'sanctions': relevant_sanctions,
        'blocked_actions': blocked_actions
    }
