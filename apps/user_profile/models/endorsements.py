# apps/user_profile/models/endorsements.py
"""
Post-Match Skill Endorsement System (P0 Feature).

Allows tournament match participants to award skill recognition to teammates
after match completion. Features:
- Match-bound only (tournament matches that reached COMPLETED state)
- Teammate verification (only same-team participants can endorse)
- Uniqueness constraints (one endorsement per endorser per match)
- Permission enforcement (no self-endorsement, no opponent endorsement)
- Immutable records (cannot delete/modify after creation)
- Aggregation helpers for profile display

Design: 03b_endorsements_and_showcase_design.md
Risk Review: 04b_endorsements_showcase_risk_review.md
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta

User = get_user_model()


class SkillType(models.TextChoices):
    """
    Predefined skill categories for endorsements.
    
    These are game-agnostic competitive skills that apply across
    all supported titles (Valorant, CS2, PUBG, etc.).
    """
    SHOTCALLING = 'shotcalling', _('Shotcalling')
    AIM = 'aim', _('Aim')
    CLUTCH = 'clutch', _('Clutch')
    SUPPORT = 'support', _('Support')
    IGL = 'igl', _('IGL (In-Game Leader)')
    ENTRY_FRAGGING = 'entry_fragging', _('Entry Fragging')


class SkillEndorsement(models.Model):
    """
    Peer-awarded skill recognition from post-match endorsement.
    
    Features:
    - Match-bound: Each endorsement tied to specific tournament match
    - Teammate-only: Endorser and receiver must be on same team
    - One per match: Endorser can only endorse ONE teammate per match
    - Immutable: Cannot modify or delete after creation
    - Anonymous display: Profile shows aggregate counts only
    
    Permission Rules:
    - Only tournament match participants can endorse
    - Match must be in COMPLETED state
    - 24-hour window after match completion (endorsement expires)
    - Cannot endorse yourself (self-endorsement blocked)
    - Cannot endorse opponent (teammate verification required)
    
    Uniqueness Constraints:
    - unique_together = ['match', 'endorser'] (one endorsement per match per endorser)
    - Check constraint: endorser != receiver
    
    Usage:
    >>> from apps.user_profile.services.endorsement_service import create_endorsement
    >>> endorsement = create_endorsement(
    ...     endorser=user1,
    ...     receiver=user2,
    ...     match=match,
    ...     skill=SkillType.AIM
    ... )
    """
    
    # Core relationships
    # UP-PHASE2E: Made match nullable to support bounty endorsements
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='skill_endorsements',
        verbose_name=_('Match'),
        help_text=_('Tournament match where skill was recognized'),
        null=True,
        blank=True,
    )
    
    # UP-PHASE2E: Added bounty FK for post-bounty endorsements
    bounty = models.ForeignKey(
        'user_profile.Bounty',
        on_delete=models.CASCADE,
        related_name='skill_endorsements',
        verbose_name=_('Bounty'),
        help_text=_('Bounty match where skill was recognized'),
        null=True,
        blank=True,
    )
    
    endorser = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='endorsements_given',
        verbose_name=_('Endorser'),
        help_text=_('Player who gave the endorsement (teammate)'),
    )
    
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='endorsements_received',
        verbose_name=_('Receiver'),
        help_text=_('Player who received the endorsement'),
        db_index=True,
    )
    
    # Skill category
    skill_name = models.CharField(
        max_length=20,
        choices=SkillType.choices,
        verbose_name=_('Skill'),
        help_text=_('Recognized skill category'),
        db_index=True,
    )
    
    # Optional comment (future feature - currently not implemented)
    comment = models.TextField(
        blank=True,
        verbose_name=_('Comment'),
        help_text=_('Optional endorsement message (max 500 chars)'),
        max_length=500,
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
        help_text=_('When endorsement was awarded'),
        db_index=True,
    )
    
    # Audit tracking
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address'),
        help_text=_('IP address of endorser (for fraud detection)'),
    )
    
    user_agent = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('User Agent'),
        help_text=_('Browser user agent (for fraud detection)'),
    )
    
    # Moderation flags
    is_flagged = models.BooleanField(
        default=False,
        verbose_name=_('Flagged'),
        help_text=_('Endorsement flagged for review (spam/manipulation)'),
    )
    
    flag_reason = models.TextField(
        blank=True,
        verbose_name=_('Flag Reason'),
        help_text=_('Reason for flagging (moderator notes)'),
    )
    
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='endorsements_reviewed',
        verbose_name=_('Reviewed By'),
        help_text=_('Moderator who reviewed flagged endorsement'),
    )
    
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Reviewed At'),
        help_text=_('When endorsement was reviewed'),
    )
    
    class Meta:
        db_table = 'user_profile_skill_endorsement'
        verbose_name = _('Skill Endorsement')
        verbose_name_plural = _('Skill Endorsements')
        
        # UP-PHASE2E: Updated constraints to support bounty endorsements
        constraints = [
            # Uniqueness for tournament matches
            models.UniqueConstraint(
                fields=['match', 'endorser'],
                condition=models.Q(match__isnull=False),
                name='unique_endorsement_per_match_endorser',
            ),
            # Uniqueness for bounties
            models.UniqueConstraint(
                fields=['bounty', 'endorser'],
                condition=models.Q(bounty__isnull=False),
                name='unique_endorsement_per_bounty_endorser',
            ),
            # Prevent self-endorsement
            models.CheckConstraint(
                check=~models.Q(endorser=models.F('receiver')),
                name='no_self_endorsement',
            ),
            # Ensure either match or bounty is set (not both, not neither)
            models.CheckConstraint(
                check=(
                    models.Q(match__isnull=False, bounty__isnull=True) |
                    models.Q(match__isnull=True, bounty__isnull=False)
                ),
                name='endorsement_has_match_or_bounty',
            ),
        ]
        
        indexes = [
            # Query endorsements by receiver (profile display)
            models.Index(fields=['receiver', '-created_at']),
            # Query endorsements by match (audit trail)
            models.Index(fields=['match', 'created_at']),
            # UP-PHASE2E: Query endorsements by bounty
            models.Index(fields=['bounty', 'created_at']),
            # Query endorsements by skill (aggregation)
            models.Index(fields=['receiver', 'skill_name']),
            # Query flagged endorsements (moderation queue)
            models.Index(fields=['is_flagged', 'created_at']),
        ]
        
        ordering = ['-created_at']
    
    def __str__(self):
        if self.match_id:
            return f'{self.endorser.username} → {self.receiver.username}: {self.get_skill_name_display()} (Match #{self.match_id})'
        elif self.bounty_id:
            return f'{self.endorser.username} → {self.receiver.username}: {self.get_skill_name_display()} (Bounty #{self.bounty_id})'
        return f'{self.endorser.username} → {self.receiver.username}: {self.get_skill_name_display()}'
    
    def clean(self):
        """Validate endorsement rules."""
        errors = {}
        
        # 1. Self-endorsement check
        if self.endorser_id and self.receiver_id and self.endorser_id == self.receiver_id:
            errors['receiver'] = _('Cannot endorse yourself.')
        
        # 2. Match completion check
        if self.match_id:
            if self.match.state != 'completed':
                errors['match'] = _('Can only endorse after match is completed.')
        
        # 3. Time window check (24 hours after match completion)
        if self.match_id and self.match.completed_at:
            expiry_time = self.match.completed_at + timedelta(hours=24)
            if timezone.now() > expiry_time:
                errors['match'] = _('Endorsement window expired (24 hours after match completion).')
        
        # 4. Participant verification (checked in service layer, not model)
        # Note: Teammate verification requires querying Match participants and Team rosters,
        # which is too complex for model.clean(). Service layer handles this.
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_match_context(self):
        """
        Return match context for display.
        
        Returns dict with:
        - match_id: Match primary key
        - tournament_name: Tournament name
        - completed_at: Match completion timestamp
        - match_url: Link to match detail page (if available)
        """
        return {
            'match_id': self.match_id,
            'tournament_name': self.match.tournament.name if self.match.tournament else 'Unknown',
            'completed_at': self.match.completed_at,
            'round_number': self.match.round_number,
            'match_number': self.match.match_number,
        }
    
    @property
    def is_within_window(self):
        """Check if endorsement was created within 24-hour window."""
        if not self.match.completed_at:
            return False
        
        expiry_time = self.match.completed_at + timedelta(hours=24)
        return self.created_at <= expiry_time
    
    @property
    def time_until_expiry(self):
        """
        Get time remaining until endorsement window expires.
        
        Returns timedelta or None if expired/no completion time.
        """
        if not self.match.completed_at:
            return None
        
        expiry_time = self.match.completed_at + timedelta(hours=24)
        remaining = expiry_time - timezone.now()
        
        return remaining if remaining.total_seconds() > 0 else None


class EndorsementOpportunity(models.Model):
    """
    Tracks 24-hour endorsement window for each player after match completion.
    
    Created automatically when match transitions to COMPLETED state.
    Used for:
    - Notifying players of endorsement opportunity
    - Tracking who has/hasn't endorsed
    - Cleanup of expired opportunities
    
    Note: This is a tracking model, not required for endorsement creation.
    Endorsements can be created directly via SkillEndorsement if within time window.
    """
    
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='endorsement_opportunities',
        verbose_name=_('Match'),
    )
    
    player = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='endorsement_opportunities',
        verbose_name=_('Player'),
        help_text=_('Player who can give endorsement'),
    )
    
    # Expiry tracking
    expires_at = models.DateTimeField(
        verbose_name=_('Expires At'),
        help_text=_('When endorsement window closes (24 hours after match completion)'),
        db_index=True,
    )
    
    # Status tracking
    is_used = models.BooleanField(
        default=False,
        verbose_name=_('Used'),
        help_text=_('Player has given endorsement for this match'),
    )
    
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Used At'),
        help_text=_('When player gave endorsement'),
    )
    
    # Notification tracking
    notified = models.BooleanField(
        default=False,
        verbose_name=_('Notified'),
        help_text=_('Player was notified of endorsement opportunity'),
    )
    
    notified_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Notified At'),
        help_text=_('When notification was sent'),
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At'),
    )
    
    class Meta:
        db_table = 'user_profile_endorsement_opportunity'
        verbose_name = _('Endorsement Opportunity')
        verbose_name_plural = _('Endorsement Opportunities')
        
        constraints = [
            # One opportunity per player per match
            models.UniqueConstraint(
                fields=['match', 'player'],
                name='unique_opportunity_per_match_player',
            ),
        ]
        
        indexes = [
            # Query expired opportunities for cleanup
            models.Index(fields=['expires_at', 'is_used']),
            # Query opportunities for player
            models.Index(fields=['player', 'is_used', 'expires_at']),
        ]
        
        ordering = ['-created_at']
    
    def __str__(self):
        status = 'Used' if self.is_used else 'Expired' if self.is_expired else 'Active'
        return f'{self.player.username} - Match #{self.match_id} ({status})'
    
    @property
    def is_expired(self):
        """Check if opportunity has expired."""
        return timezone.now() > self.expires_at
    
    @property
    def time_remaining(self):
        """Get time remaining until expiry."""
        remaining = self.expires_at - timezone.now()
        return remaining if remaining.total_seconds() > 0 else None
    
    def mark_used(self):
        """Mark opportunity as used."""
        self.is_used = True
        self.used_at = timezone.now()
        self.save(update_fields=['is_used', 'used_at'])
