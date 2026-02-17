# apps/user_profile/models/bounties.py
"""
Bounty System Models - Peer-to-Peer Challenge System.

Models:
- Bounty: Main challenge entity with escrow-backed stakes
- BountyAcceptance: Records challenge acceptances
- BountyProof: Stores proof submissions (screenshots/videos)
- BountyDispute: Tracks disputes and moderator resolutions

Design: 03a_bounty_system_design.md
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class BountyStatus(models.TextChoices):
    """Bounty state machine."""
    OPEN = 'open', 'Open'
    ACCEPTED = 'accepted', 'Accepted'
    IN_PROGRESS = 'in_progress', 'In Progress'
    PENDING_RESULT = 'pending_result', 'Pending Result'
    DISPUTED = 'disputed', 'Disputed'
    COMPLETED = 'completed', 'Completed'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'


class Bounty(models.Model):
    """
    Peer-to-peer challenge with escrow-backed stake.
    
    Lifecycle:
    - OPEN: Waiting for acceptor (expires after 72h default)
    - ACCEPTED: Acceptor confirmed, match pending
    - IN_PROGRESS: Match started/lobby created
    - PENDING_RESULT: Result submitted, 24h dispute window
    - DISPUTED: Result challenged by opponent
    - COMPLETED: Winner paid, escrow released (terminal)
    - EXPIRED: No acceptor, refunded (terminal)
    - CANCELLED: Creator cancelled before acceptance (terminal)
    
    Escrow Integration:
    - On create: Locks stake in creator's wallet.pending_balance
    - On complete: Releases escrow, pays winner (95%), platform fee (5%)
    - On expire/cancel: Releases escrow, refunds creator 100%
    """
    
    # Core Fields
    title = models.CharField(
        max_length=200,
        help_text="Challenge title (e.g., 'First to 100k in Gridshot')"
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed challenge requirements and rules"
    )
    
    # Participants
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_bounties',
        help_text="User who created and funded the bounty"
    )
    acceptor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='accepted_bounties',
        null=True,
        blank=True,
        help_text="User who accepted the challenge"
    )
    target_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='targeted_bounties',
        null=True,
        blank=True,
        help_text="If set, only this user can accept (private challenge)"
    )
    winner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='won_bounties',
        null=True,
        blank=True,
        help_text="Final winner after verification"
    )
    
    # Game Context
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.PROTECT,
        help_text="Game for this challenge"
    )
    
    # Financial
    stake_amount = models.IntegerField(
        help_text="DeltaCoins locked in escrow (creator's stake)"
    )
    payout_amount = models.IntegerField(
        null=True,
        blank=True,
        help_text="Actual payout to winner (stake * 0.95)"
    )
    platform_fee = models.IntegerField(
        null=True,
        blank=True,
        help_text="Platform fee retained (stake * 0.05)"
    )
    
    # State Management
    status = models.CharField(
        max_length=20,
        choices=BountyStatus.choices,
        default=BountyStatus.OPEN,
        db_index=True,
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When match started (IN_PROGRESS)"
    )
    result_submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(
        db_index=True,
        help_text="Auto-refund if still OPEN after this timestamp"
    )
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    
    # Optional Match Reference
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bounties',
        help_text="Optional link to tournament match if used"
    )
    
    class Meta:
        verbose_name = "Bounty"
        verbose_name_plural = "Bounties"
        indexes = [
            models.Index(fields=['status', 'expires_at']),  # For expiry task
            models.Index(fields=['creator', 'status']),
            models.Index(fields=['acceptor', 'status']),
            models.Index(fields=['game', 'status']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Bounty #{self.id}: {self.title} ({self.stake_amount} DC)"
    
    def clean(self):
        """Validate bounty constraints."""
        super().clean()
        
        # Stake amount validation
        if self.stake_amount and self.stake_amount < 100:
            raise ValidationError("Minimum stake is 100 DC")
        if self.stake_amount and self.stake_amount > 50000:
            raise ValidationError("Maximum stake is 50,000 DC")
        
        # Target user cannot be creator
        if self.target_user and self.target_user == self.creator:
            raise ValidationError("Cannot challenge yourself")
        
        # Acceptor cannot be creator
        if self.acceptor and self.acceptor == self.creator:
            raise ValidationError("Creator cannot accept their own bounty")
        
        # Winner must be participant
        if self.winner:
            if self.winner not in [self.creator, self.acceptor]:
                raise ValidationError("Winner must be creator or acceptor")
    
    def save(self, *args, **kwargs):
        # Set expiry time on creation if not set
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=72)
        
        # Calculate payout and fee on completion
        if self.status == BountyStatus.COMPLETED and not self.payout_amount:
            self.payout_amount = int(self.stake_amount * 0.95)
            self.platform_fee = self.stake_amount - self.payout_amount
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if bounty expired."""
        return (
            self.status == BountyStatus.OPEN and 
            self.expires_at and 
            timezone.now() > self.expires_at
        )
    
    @property
    def time_until_expiry(self):
        """Time remaining until expiry (for OPEN bounties)."""
        if self.status != BountyStatus.OPEN or not self.expires_at:
            return None
        delta = self.expires_at - timezone.now()
        return delta if delta.total_seconds() > 0 else timedelta(0)
    
    @property
    def can_dispute(self):
        """Check if still within 24-hour dispute window."""
        if self.status != BountyStatus.PENDING_RESULT:
            return False
        if not self.result_submitted_at:
            return False
        dispute_deadline = self.result_submitted_at + timedelta(hours=24)
        return timezone.now() <= dispute_deadline
    
    @property
    def dispute_deadline(self):
        """Timestamp when dispute window closes."""
        if self.result_submitted_at:
            return self.result_submitted_at + timedelta(hours=24)
        return None


class BountyAcceptance(models.Model):
    """
    Records when a user accepts a bounty challenge.
    
    One acceptance per bounty. Once accepted, bounty transitions
    from OPEN to ACCEPTED state.
    """
    
    bounty = models.OneToOneField(
        Bounty,
        on_delete=models.CASCADE,
        related_name='acceptance',
        primary_key=True,
    )
    acceptor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bounty_acceptances',
    )
    accepted_at = models.DateTimeField(auto_now_add=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    
    class Meta:
        verbose_name = "Bounty Acceptance"
        verbose_name_plural = "Bounty Acceptances"
    
    def __str__(self):
        return f"{self.acceptor.username} accepted Bounty #{self.bounty.id}"


class BountyProof(models.Model):
    """
    Proof submission for bounty result (screenshot or video).
    
    Both participants can submit proofs. First submission transitions
    bounty to PENDING_RESULT state.
    """
    
    bounty = models.ForeignKey(
        Bounty,
        on_delete=models.CASCADE,
        related_name='proofs',
    )
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bounty_proofs',
    )
    claimed_winner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bounty_win_claims',
        help_text="User claimed as winner in this proof"
    )
    
    # Proof Data
    proof_url = models.URLField(
        max_length=500,
        help_text="Screenshot or video URL (Imgur, YouTube, etc.)"
    )
    proof_type = models.CharField(
        max_length=20,
        choices=[
            ('screenshot', 'Screenshot'),
            ('video', 'Video'),
            ('replay', 'Replay File'),
        ],
        default='screenshot',
    )
    description = models.TextField(
        blank=True,
        help_text="Additional context for proof"
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Bounty Proof"
        verbose_name_plural = "Bounty Proofs"
        ordering = ['submitted_at']
        indexes = [
            models.Index(fields=['bounty', 'submitted_at']),
        ]
    
    def __str__(self):
        return f"Proof for Bounty #{self.bounty.id} by {self.submitted_by.username}"
    
    def clean(self):
        """Validate proof submission."""
        super().clean()
        
        # Submitter must be participant
        if self.submitted_by not in [self.bounty.creator, self.bounty.acceptor]:
            raise ValidationError("Only participants can submit proof")
        
        # Claimed winner must be participant
        if self.claimed_winner not in [self.bounty.creator, self.bounty.acceptor]:
            raise ValidationError("Winner must be creator or acceptor")


class DisputeStatus(models.TextChoices):
    """Dispute resolution states."""
    OPEN = 'open', 'Open'
    UNDER_REVIEW = 'under_review', 'Under Review'
    RESOLVED_CONFIRM = 'resolved_confirm', 'Resolved - Confirmed Winner'
    RESOLVED_REVERSE = 'resolved_reverse', 'Resolved - Reversed Winner'
    RESOLVED_VOID = 'resolved_void', 'Resolved - Match Voided'


class BountyDispute(models.Model):
    """
    Dispute raised by participant contesting result.
    
    Only the opponent (non-submitter) can raise dispute within
    24 hours of result submission. Moderators resolve disputes.
    """
    
    bounty = models.OneToOneField(
        Bounty,
        on_delete=models.CASCADE,
        related_name='dispute',
        primary_key=True,
    )
    disputer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bounty_disputes_raised',
        help_text="User who raised the dispute"
    )
    reason = models.TextField(
        help_text="Why the result is disputed"
    )
    
    # Moderation
    status = models.CharField(
        max_length=20,
        choices=DisputeStatus.choices,
        default=DisputeStatus.OPEN,
    )
    assigned_moderator = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_bounty_disputes',
        limit_choices_to={'is_staff': True},
    )
    moderator_notes = models.TextField(blank=True)
    resolution = models.TextField(
        blank=True,
        help_text="Moderator's final decision explanation"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Bounty Dispute"
        verbose_name_plural = "Bounty Disputes"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Dispute for Bounty #{self.bounty.id} by {self.disputer.username}"
    
    def clean(self):
        """Validate dispute constraints."""
        super().clean()
        
        # Disputer must be participant
        if self.disputer not in [self.bounty.creator, self.bounty.acceptor]:
            raise ValidationError("Only participants can dispute")
        
        # Must be within 24-hour window
        if not self.bounty.can_dispute:
            raise ValidationError("Dispute window expired (24 hours after result submission)")
    
    @property
    def is_resolved(self):
        """Check if dispute has been resolved."""
        return self.status in [
            DisputeStatus.RESOLVED_CONFIRM,
            DisputeStatus.RESOLVED_REVERSE,
            DisputeStatus.RESOLVED_VOID,
        ]
