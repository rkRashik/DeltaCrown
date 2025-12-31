# apps/user_profile/services/bounty_service.py
"""
Bounty Service Layer - Business logic for peer-to-peer challenges.

Handles:
- Bounty creation with escrow locking
- Acceptance and participant verification
- Result submission and proof tracking
- Dispute management and moderator resolution
- Expiry automation and refunds
- Economy integration via idempotent transactions

Design: 03a_bounty_system_design.md
"""

from typing import Optional, Dict, Any, Tuple, List
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.user_profile.models import (
    Bounty,
    BountyAcceptance,
    BountyProof,
    BountyDispute,
    BountyStatus,
    DisputeStatus,
)
from apps.economy import services as economy_services
from apps.economy.models import DeltaCrownWallet
from apps.core.models import Game

User = get_user_model()


# ============================================================================
# BOUNTY CREATION & ESCROW
# ============================================================================

@transaction.atomic
def create_bounty(
    creator: User,
    title: str,
    game: Game,
    stake_amount: int,
    description: str = "",
    target_user: Optional[User] = None,
    expires_in_hours: int = 72,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Bounty:
    """
    Create bounty and lock stake in escrow.
    
    Process:
    1. Validate creator has sufficient available balance
    2. Create Bounty record with status=OPEN
    3. Lock funds: Debit cached_balance, increment pending_balance
    4. Set expiry timestamp
    
    Args:
        creator: User creating the bounty
        title: Challenge title
        game: Game for challenge
        stake_amount: DeltaCoins to lock in escrow
        description: Optional detailed requirements
        target_user: Optional private challenge target
        expires_in_hours: Hours until auto-refund (default 72)
        ip_address: Creator's IP for audit
        user_agent: Creator's user agent
    
    Returns:
        Bounty instance
    
    Raises:
        ValidationError: Invalid stake amount or parameters
        PermissionDenied: Insufficient balance or rate limit exceeded
    """
    
    # Validate stake amount
    if stake_amount < 100:
        raise ValidationError("Minimum stake is 100 DC")
    if stake_amount > 50000:
        raise ValidationError("Maximum stake is 50,000 DC")
    
    # Validate target user
    if target_user and target_user == creator:
        raise ValidationError("Cannot challenge yourself")
    
    # Check rate limit (10 bounties per 24 hours)
    recent_bounties = Bounty.objects.filter(
        creator=creator,
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    if recent_bounties >= 10:
        raise PermissionDenied("Rate limit exceeded: Maximum 10 bounties per 24 hours")
    
    # Check available balance
    wallet, _ = DeltaCrownWallet.objects.select_for_update().get_or_create(
        profile=creator.profile
    )
    
    available = wallet.cached_balance - wallet.pending_balance
    if available < stake_amount:
        raise PermissionDenied(
            f"Insufficient funds: {available} DC available, need {stake_amount} DC"
        )
    
    # Create bounty record
    expires_at = timezone.now() + timedelta(hours=expires_in_hours)
    
    bounty = Bounty.objects.create(
        creator=creator,
        title=title,
        description=description,
        game=game,
        stake_amount=stake_amount,
        target_user=target_user,
        status=BountyStatus.OPEN,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Lock funds in escrow
    _lock_bounty_escrow(bounty)
    
    return bounty


def _lock_bounty_escrow(bounty: Bounty) -> Dict[str, Any]:
    """
    Lock bounty stake in creator's wallet.pending_balance.
    
    Process:
    1. Debit cached_balance (BOUNTY_ESCROW transaction)
    2. Increment pending_balance by stake_amount
    3. Use idempotency key to prevent duplicate locks
    """
    
    idempotency_key = f"bounty:escrow:{bounty.id}:{bounty.creator.id}"
    
    # Debit from cached_balance
    result = economy_services.debit(
        profile=bounty.creator.profile,
        amount=bounty.stake_amount,
        reason='BOUNTY_ESCROW',
        idempotency_key=idempotency_key,
        meta={'bounty_id': bounty.id, 'title': bounty.title},
    )
    
    # Increment pending_balance (escrow lock)
    wallet = DeltaCrownWallet.objects.select_for_update().get(
        profile=bounty.creator.profile
    )
    wallet.pending_balance += bounty.stake_amount
    wallet.save(update_fields=['pending_balance', 'updated_at'])
    
    return result


# ============================================================================
# BOUNTY ACCEPTANCE
# ============================================================================

@transaction.atomic
def accept_bounty(
    bounty_id: int,
    acceptor: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BountyAcceptance:
    """
    Accept an open bounty challenge.
    
    Process:
    1. Lock bounty row with select_for_update()
    2. Validate bounty is OPEN and not expired
    3. Validate acceptor eligibility
    4. Create BountyAcceptance record
    5. Transition bounty to ACCEPTED state
    6. Clear expires_at (no longer applicable)
    
    Args:
        bounty_id: Bounty to accept
        acceptor: User accepting challenge
        ip_address: Acceptor's IP
        user_agent: Acceptor's user agent
    
    Returns:
        BountyAcceptance instance
    
    Raises:
        ValidationError: Bounty not found or invalid state
        PermissionDenied: Acceptor not eligible
    """
    
    # Lock bounty row
    try:
        bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    except Bounty.DoesNotExist:
        raise ValidationError("Bounty not found")
    
    # Validate state
    if bounty.status != BountyStatus.OPEN:
        raise ValidationError(f"Bounty is not open (status: {bounty.status})")
    
    # Check expiry
    if bounty.is_expired:
        raise ValidationError("Bounty has expired")
    
    # Validate acceptor eligibility
    if acceptor == bounty.creator:
        raise PermissionDenied("Cannot accept your own bounty")
    
    if bounty.target_user and acceptor != bounty.target_user:
        raise PermissionDenied("This is a private challenge for another user")
    
    # Check active bounties limit (3 max)
    active_count = Bounty.objects.filter(
        acceptor=acceptor,
        status__in=[BountyStatus.ACCEPTED, BountyStatus.IN_PROGRESS, BountyStatus.PENDING_RESULT]
    ).count()
    
    if active_count >= 3:
        raise PermissionDenied("Maximum 3 active bounties at a time")
    
    # Create acceptance record
    acceptance = BountyAcceptance.objects.create(
        bounty=bounty,
        acceptor=acceptor,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # Update bounty state
    bounty.acceptor = acceptor
    bounty.status = BountyStatus.ACCEPTED
    bounty.accepted_at = timezone.now()
    bounty.expires_at = None  # No longer applicable
    bounty.save(update_fields=['acceptor', 'status', 'accepted_at', 'expires_at'])
    
    return acceptance


# ============================================================================
# MATCH PROGRESSION
# ============================================================================

@transaction.atomic
def start_match(bounty_id: int, started_by: User) -> Bounty:
    """
    Transition bounty from ACCEPTED to IN_PROGRESS.
    
    Args:
        bounty_id: Bounty to start
        started_by: User starting match (must be participant)
    
    Returns:
        Updated Bounty instance
    """
    
    bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    
    # Validate state
    if bounty.status != BountyStatus.ACCEPTED:
        raise ValidationError(f"Cannot start match: bounty is {bounty.status}")
    
    # Validate participant
    if started_by not in [bounty.creator, bounty.acceptor]:
        raise PermissionDenied("Only participants can start match")
    
    # Update state
    bounty.status = BountyStatus.IN_PROGRESS
    bounty.started_at = timezone.now()
    bounty.save(update_fields=['status', 'started_at'])
    
    return bounty


@transaction.atomic
def submit_result(
    bounty_id: int,
    submitted_by: User,
    claimed_winner: User,
    proof_url: str,
    proof_type: str = 'screenshot',
    description: str = "",
    ip_address: Optional[str] = None,
) -> BountyProof:
    """
    Submit match result with proof.
    
    Process:
    1. Validate bounty is IN_PROGRESS
    2. Validate submitter is participant
    3. Create BountyProof record
    4. Transition bounty to PENDING_RESULT
    5. Start 24-hour dispute window
    
    Args:
        bounty_id: Bounty to submit result for
        submitted_by: User submitting proof
        claimed_winner: User claimed as winner
        proof_url: Screenshot/video URL
        proof_type: Type of proof (screenshot, video, replay)
        description: Additional context
        ip_address: Submitter's IP
    
    Returns:
        BountyProof instance
    """
    
    bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    
    # Validate state
    if bounty.status != BountyStatus.IN_PROGRESS:
        raise ValidationError(f"Cannot submit result: bounty is {bounty.status}")
    
    # Validate participant
    if submitted_by not in [bounty.creator, bounty.acceptor]:
        raise PermissionDenied("Only participants can submit results")
    
    # Validate winner
    if claimed_winner not in [bounty.creator, bounty.acceptor]:
        raise ValidationError("Winner must be creator or acceptor")
    
    # Create proof record
    proof = BountyProof.objects.create(
        bounty=bounty,
        submitted_by=submitted_by,
        claimed_winner=claimed_winner,
        proof_url=proof_url,
        proof_type=proof_type,
        description=description,
        ip_address=ip_address,
    )
    
    # Update bounty state (first submission)
    if bounty.status == BountyStatus.IN_PROGRESS:
        bounty.status = BountyStatus.PENDING_RESULT
        bounty.result_submitted_at = timezone.now()
        bounty.winner = claimed_winner  # Tentative winner
        bounty.save(update_fields=['status', 'result_submitted_at', 'winner'])
    
    return proof


# ============================================================================
# BOUNTY COMPLETION & PAYOUT
# ============================================================================

@transaction.atomic
def complete_bounty(bounty_id: int, confirmed_winner: Optional[User] = None) -> Bounty:
    """
    Complete bounty and pay winner (auto-confirm or moderator decision).
    
    Process:
    1. Validate bounty is PENDING_RESULT and dispute window expired
    2. Release escrow from creator's pending_balance
    3. Pay winner (95% of stake)
    4. Transfer platform fee (5% of stake)
    5. Transition bounty to COMPLETED
    
    Args:
        bounty_id: Bounty to complete
        confirmed_winner: Optional override for moderator resolution
    
    Returns:
        Completed Bounty instance
    """
    
    bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    
    # Validate state
    if bounty.status not in [BountyStatus.PENDING_RESULT, BountyStatus.DISPUTED]:
        raise ValidationError(f"Cannot complete: bounty is {bounty.status}")
    
    # Validate dispute window (if not moderator override)
    if not confirmed_winner and bounty.can_dispute:
        raise ValidationError("Cannot auto-complete: still within 24-hour dispute window")
    
    # Determine final winner
    winner = confirmed_winner or bounty.winner
    if not winner:
        raise ValidationError("No winner specified")
    
    # Calculate payout
    payout = int(bounty.stake_amount * 0.95)
    platform_fee = bounty.stake_amount - payout
    
    # Release escrow lock
    _release_bounty_escrow(bounty)
    
    # Pay winner
    idempotency_key_win = f"bounty:win:{bounty.id}:{winner.id}"
    economy_services.credit(
        profile=winner.profile,
        amount=payout,
        reason='BOUNTY_WIN',
        idempotency_key=idempotency_key_win,
        meta={'bounty_id': bounty.id, 'title': bounty.title, 'stake': bounty.stake_amount},
    )
    
    # Transfer platform fee (optional - could skip if want to keep as commission)
    # For now, we track it but don't transfer (platform keeps it)
    
    # Update bounty
    bounty.status = BountyStatus.COMPLETED
    bounty.completed_at = timezone.now()
    bounty.winner = winner
    bounty.payout_amount = payout
    bounty.platform_fee = platform_fee
    bounty.save(update_fields=[
        'status', 'completed_at', 'winner', 'payout_amount', 'platform_fee'
    ])
    
    return bounty


def _release_bounty_escrow(bounty: Bounty) -> None:
    """Decrement pending_balance to release escrow lock."""
    
    wallet = DeltaCrownWallet.objects.select_for_update().get(
        profile=bounty.creator.profile
    )
    wallet.pending_balance = max(0, wallet.pending_balance - bounty.stake_amount)
    wallet.save(update_fields=['pending_balance', 'updated_at'])


# ============================================================================
# DISPUTES
# ============================================================================

@transaction.atomic
def raise_dispute(
    bounty_id: int,
    disputer: User,
    reason: str,
) -> BountyDispute:
    """
    Raise dispute contesting submitted result.
    
    Process:
    1. Validate bounty is PENDING_RESULT
    2. Validate disputer is participant (not submitter)
    3. Validate within 24-hour window
    4. Create BountyDispute record
    5. Transition bounty to DISPUTED
    
    Args:
        bounty_id: Bounty to dispute
        disputer: User raising dispute
        reason: Why result is disputed (min 50 chars)
    
    Returns:
        BountyDispute instance
    """
    
    bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    
    # Validate state
    if bounty.status != BountyStatus.PENDING_RESULT:
        raise ValidationError(f"Cannot dispute: bounty is {bounty.status}")
    
    # Validate disputer is participant
    if disputer not in [bounty.creator, bounty.acceptor]:
        raise PermissionDenied("Only participants can dispute")
    
    # Validate within dispute window
    if not bounty.can_dispute:
        raise ValidationError("Dispute window expired (24 hours after result submission)")
    
    # Validate reason length
    if len(reason) < 50:
        raise ValidationError("Dispute reason must be at least 50 characters")
    
    # Check if already disputed
    if hasattr(bounty, 'dispute'):
        raise ValidationError("Dispute already exists for this bounty")
    
    # Create dispute
    dispute = BountyDispute.objects.create(
        bounty=bounty,
        disputer=disputer,
        reason=reason,
        status=DisputeStatus.OPEN,
    )
    
    # Update bounty state
    bounty.status = BountyStatus.DISPUTED
    bounty.save(update_fields=['status'])
    
    return dispute


@transaction.atomic
def resolve_dispute(
    dispute_id: int,
    moderator: User,
    decision: str,
    resolution: str,
    moderator_notes: str = "",
) -> Tuple[BountyDispute, Bounty]:
    """
    Moderator resolves dispute.
    
    Decisions:
    - 'confirm': Confirm original winner, pay them
    - 'reverse': Reverse winner, pay opponent
    - 'void': Void match, refund both parties
    
    Args:
        dispute_id: Dispute to resolve
        moderator: Staff user resolving dispute
        decision: 'confirm', 'reverse', or 'void'
        resolution: Explanation of decision
        moderator_notes: Internal moderator notes
    
    Returns:
        Tuple of (BountyDispute, Bounty)
    """
    
    if not moderator.is_staff:
        raise PermissionDenied("Only staff can resolve disputes")
    
    dispute = BountyDispute.objects.select_for_update().get(pk=dispute_id)
    bounty = dispute.bounty
    
    # Validate not already resolved
    if dispute.is_resolved:
        raise ValidationError("Dispute already resolved")
    
    # Process decision
    if decision == 'confirm':
        # Confirm original winner
        dispute.status = DisputeStatus.RESOLVED_CONFIRM
        complete_bounty(bounty.id, confirmed_winner=bounty.winner)
        
    elif decision == 'reverse':
        # Reverse winner
        original_winner = bounty.winner
        new_winner = bounty.acceptor if original_winner == bounty.creator else bounty.creator
        dispute.status = DisputeStatus.RESOLVED_REVERSE
        complete_bounty(bounty.id, confirmed_winner=new_winner)
        
    elif decision == 'void':
        # Void match, refund both
        dispute.status = DisputeStatus.RESOLVED_VOID
        _void_bounty(bounty)
        
    else:
        raise ValidationError("Invalid decision: must be 'confirm', 'reverse', or 'void'")
    
    # Update dispute
    dispute.assigned_moderator = moderator
    dispute.resolution = resolution
    dispute.moderator_notes = moderator_notes
    dispute.resolved_at = timezone.now()
    dispute.save(update_fields=[
        'status', 'assigned_moderator', 'resolution', 'moderator_notes', 'resolved_at'
    ])
    
    return dispute, bounty


def _void_bounty(bounty: Bounty) -> None:
    """
    Void match and refund creator (acceptor gets nothing since no stake from them).
    
    Note: In current design, only creator stakes. If we want both to stake,
    this would refund both parties.
    """
    
    # Release escrow
    _release_bounty_escrow(bounty)
    
    # Refund creator
    idempotency_key = f"bounty:void:{bounty.id}:{bounty.creator.id}"
    economy_services.credit(
        profile=bounty.creator.profile,
        amount=bounty.stake_amount,
        reason='BOUNTY_REFUND',
        idempotency_key=idempotency_key,
        meta={'bounty_id': bounty.id, 'title': bounty.title, 'reason': 'voided'},
    )
    
    # Update bounty
    bounty.status = BountyStatus.CANCELLED
    bounty.completed_at = timezone.now()
    bounty.save(update_fields=['status', 'completed_at'])


# ============================================================================
# CANCELLATION & EXPIRY
# ============================================================================

@transaction.atomic
def cancel_bounty(bounty_id: int, cancelled_by: User) -> Bounty:
    """
    Cancel bounty (only allowed in OPEN state before acceptance).
    
    Process:
    1. Validate bounty is OPEN
    2. Validate cancelled_by is creator
    3. Release escrow and refund creator
    4. Transition bounty to CANCELLED
    
    Args:
        bounty_id: Bounty to cancel
        cancelled_by: User cancelling (must be creator)
    
    Returns:
        Cancelled Bounty instance
    """
    
    bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    
    # Validate state
    if bounty.status != BountyStatus.OPEN:
        raise ValidationError(f"Cannot cancel: bounty is {bounty.status} (only OPEN bounties can be cancelled)")
    
    # Validate permissions
    if cancelled_by != bounty.creator:
        raise PermissionDenied("Only creator can cancel bounty")
    
    # Release escrow and refund
    _refund_bounty(bounty, reason='cancelled')
    
    # Update bounty
    bounty.status = BountyStatus.CANCELLED
    bounty.completed_at = timezone.now()
    bounty.save(update_fields=['status', 'completed_at'])
    
    return bounty


@transaction.atomic
def expire_bounty(bounty_id: int) -> Bounty:
    """
    Expire bounty (called by scheduled task for OPEN bounties past expires_at).
    
    Process:
    1. Validate bounty is OPEN and expired
    2. Release escrow and refund creator
    3. Transition bounty to EXPIRED
    
    Args:
        bounty_id: Bounty to expire
    
    Returns:
        Expired Bounty instance
    """
    
    bounty = Bounty.objects.select_for_update().get(pk=bounty_id)
    
    # Validate state
    if bounty.status != BountyStatus.OPEN:
        # Already transitioned, skip (idempotent)
        return bounty
    
    # Validate expiry
    if not bounty.is_expired:
        raise ValidationError("Bounty has not expired yet")
    
    # Release escrow and refund
    _refund_bounty(bounty, reason='expired')
    
    # Update bounty
    bounty.status = BountyStatus.EXPIRED
    bounty.completed_at = timezone.now()
    bounty.save(update_fields=['status', 'completed_at'])
    
    return bounty


def _refund_bounty(bounty: Bounty, reason: str) -> Dict[str, Any]:
    """
    Refund bounty stake to creator.
    
    Process:
    1. Release escrow lock (decrement pending_balance)
    2. Credit creator's cached_balance (BOUNTY_REFUND transaction)
    """
    
    # Release escrow
    _release_bounty_escrow(bounty)
    
    # Credit refund
    idempotency_key = f"bounty:refund:{bounty.id}:{bounty.creator.id}:{reason}"
    result = economy_services.credit(
        profile=bounty.creator.profile,
        amount=bounty.stake_amount,
        reason='BOUNTY_REFUND',
        idempotency_key=idempotency_key,
        meta={'bounty_id': bounty.id, 'title': bounty.title, 'reason': reason},
    )
    
    return result


# ============================================================================
# BATCH EXPIRY (FOR SCHEDULED TASK)
# ============================================================================

def expire_open_bounties(batch_size: int = 100) -> Dict[str, int]:
    """
    Expire all OPEN bounties past expires_at (called by management command).
    
    Process:
    1. Query OPEN bounties with expires_at <= now()
    2. For each bounty, call expire_bounty()
    3. Return counts of processed/failed
    
    Args:
        batch_size: Maximum bounties to process per run
    
    Returns:
        Dict with 'processed', 'failed', 'skipped' counts
    """
    
    now = timezone.now()
    expired_bounties = Bounty.objects.filter(
        status=BountyStatus.OPEN,
        expires_at__lte=now
    )[:batch_size]
    
    processed = 0
    failed = 0
    skipped = 0
    
    for bounty in expired_bounties:
        try:
            expire_bounty(bounty.id)
            processed += 1
        except ValidationError:
            # Already transitioned (race condition)
            skipped += 1
        except Exception as e:
            # Log error and continue
            failed += 1
            print(f"Failed to expire bounty {bounty.id}: {e}")
    
    return {
        'processed': processed,
        'failed': failed,
        'skipped': skipped,
        'total_found': len(expired_bounties),
    }


# ============================================================================
# QUERY HELPERS
# ============================================================================

def get_user_bounty_stats(user: User) -> Dict[str, Any]:
    """
    Get bounty statistics for user profile.
    
    Returns:
        Dict with created_count, accepted_count, won_count, lost_count, win_rate, total_earnings, total_wagered
    """
    
    created_count = Bounty.objects.filter(creator=user).count()
    accepted_count = Bounty.objects.filter(acceptor=user).count()
    
    won_count = Bounty.objects.filter(
        winner=user,
        status=BountyStatus.COMPLETED
    ).count()
    
    # Lost = participated but didn't win
    participated = Bounty.objects.filter(
        models.Q(creator=user) | models.Q(acceptor=user),
        status=BountyStatus.COMPLETED
    ).count()
    lost_count = participated - won_count
    
    # Win rate
    total_completed = won_count + lost_count
    win_rate = (won_count / total_completed * 100) if total_completed > 0 else 0
    
    # Earnings (sum of BOUNTY_WIN transactions)
    from apps.economy.models import DeltaCrownTransaction
    total_earnings = DeltaCrownTransaction.objects.filter(
        wallet__profile__user=user,
        reason='BOUNTY_WIN'
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    # Wagered (sum of BOUNTY_ESCROW transactions)
    total_wagered = abs(DeltaCrownTransaction.objects.filter(
        wallet__profile__user=user,
        reason='BOUNTY_ESCROW'
    ).aggregate(total=models.Sum('amount'))['total'] or 0)
    
    return {
        'created_count': created_count,
        'accepted_count': accepted_count,
        'won_count': won_count,
        'lost_count': lost_count,
        'win_rate': round(win_rate, 1),
        'total_earnings': total_earnings,
        'total_wagered': total_wagered,
    }


def get_active_bounties(user: User) -> 'QuerySet[Bounty]':
    """Get user's active bounties (OPEN, ACCEPTED, IN_PROGRESS, PENDING_RESULT, DISPUTED)."""
    from django.db.models import Q
    
    return Bounty.objects.filter(
        Q(creator=user) | Q(acceptor=user),
        status__in=[
            BountyStatus.OPEN,
            BountyStatus.ACCEPTED,
            BountyStatus.IN_PROGRESS,
            BountyStatus.PENDING_RESULT,
            BountyStatus.DISPUTED,
        ]
    ).select_related('game', 'creator', 'acceptor')


def get_completed_bounties(user: User) -> 'QuerySet[Bounty]':
    """Get user's completed bounties (COMPLETED, EXPIRED, CANCELLED)."""
    from django.db.models import Q
    
    return Bounty.objects.filter(
        Q(creator=user) | Q(acceptor=user),
        status__in=[
            BountyStatus.COMPLETED,
            BountyStatus.EXPIRED,
            BountyStatus.CANCELLED,
        ]
    ).select_related('game', 'creator', 'acceptor', 'winner')


# Missing import for Q
from django.db.models import Q, Sum
from django.db import models
