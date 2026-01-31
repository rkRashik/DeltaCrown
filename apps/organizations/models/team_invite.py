"""
Team invitation model for manager and member invites.

TeamInvite represents an invitation to join a team roster,
supporting both existing users and email-based invitations.
"""

import uuid
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

from ..choices import MembershipRole, MembershipStatus

User = get_user_model()


class TeamInvite(models.Model):
    """
    Invitation to join a team roster.
    
    Supports two invitation modes:
    1. Existing user: invited_user is set (user has an account)
    2. Email invite: invited_email is set (user needs to sign up)
    
    Workflow:
    - Creator sends invite → status=PENDING
    - Invitee accepts → TeamMembership created, status=ACCEPTED
    - Invitee declines → status=DECLINED
    - Expires after 7 days → status=EXPIRED
    
    Database Table: organizations_team_invite
    """
    
    # Core relationships
    team = models.ForeignKey(
        'teams.Team',  # Using legacy Team model
        on_delete=models.CASCADE,
        related_name='vnext_invites',  # Changed to avoid clash with teams.TeamInvite.invites
        help_text='Team extending invitation'
    )
    invited_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='team_invites',
        help_text="User being invited (NULL if invite by email)"
    )
    invited_email = models.EmailField(
        blank=True,
        help_text="Email for non-registered users"
    )
    inviter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sent_team_invites',
        help_text="User who sent the invitation"
    )
    
    # Invitation details
    role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        default=MembershipRole.PLAYER,
        help_text="Role to assign upon acceptance"
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('ACCEPTED', 'Accepted'),
            ('DECLINED', 'Declined'),
            ('EXPIRED', 'Expired'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='PENDING',
        db_index=True,
        help_text="Invitation status"
    )
    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text="Unique token for accepting invitation"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When invitation was sent"
    )
    expires_at = models.DateTimeField(
        help_text="When invitation expires (7 days from creation)"
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When invitee responded (accepted/declined)"
    )
    
    class Meta:
        db_table = 'organizations_team_invite'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', 'status'], name='team_invite_team_status_idx'),
            models.Index(fields=['invited_user'], name='team_invite_user_idx'),
            models.Index(fields=['invited_email'], name='team_invite_email_idx'),
            models.Index(fields=['token'], name='team_invite_token_idx'),
        ]
        verbose_name = 'Team Invitation'
        verbose_name_plural = 'Team Invitations'
    
    def __str__(self):
        """Return human-readable representation."""
        who = self.invited_user or self.invited_email or 'Unknown'
        return f"Invite({who}) → {self.team.name} [{self.status}]"
    
    def save(self, *args, **kwargs):
        """Auto-set expires_at if not provided."""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if invitation has expired."""
        return (
            self.status == 'PENDING' and
            timezone.now() > self.expires_at
        )
    
    def mark_expired_if_needed(self):
        """Mark as expired if past expiration date."""
        if self.is_expired():
            self.status = 'EXPIRED'
            self.save(update_fields=['status'])
