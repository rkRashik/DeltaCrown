"""
Tournament Team Invitation Model
Allows tournament organizers to invite teams to participate in tournaments.
This is a modern esports feature where organizers can directly invite professional teams.
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class TournamentTeamInvitation(models.Model):
    """
    Invitation from tournament organizer to a team.
    
    Modern esports tournaments often invite specific teams (e.g., previous champions,
    top-ranked teams, sponsored teams) in addition to open registration.
    """
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Response"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled by Organizer"
    
    # Core relationships
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='team_invitations',
        help_text="Tournament extending the invitation"
    )
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='tournament_invitations',
        help_text="Team being invited"
    )
    
    # Invitation details
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    message = models.TextField(
        blank=True,
        help_text="Optional message from organizer to team"
    )
    
    # Metadata
    invited_by = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_tournament_invitations',
        help_text="Organizer/staff who sent the invitation"
    )
    invited_at = models.DateTimeField(
        default=timezone.now,
        db_index=True
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the invitation expires (if set)"
    )
    
    # Response tracking
    responded_by = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_tournament_invitations',
        help_text="Team member who responded to invitation"
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When team responded (accepted/declined)"
    )
    response_message = models.TextField(
        blank=True,
        help_text="Optional message from team when responding"
    )
    
    # Auto-registration feature
    auto_register_on_accept = models.BooleanField(
        default=True,
        help_text="Automatically create tournament registration when invitation is accepted"
    )
    registration = models.OneToOneField(
        'tournaments.Registration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_from_invitation',
        help_text="Registration created when invitation was accepted"
    )
    
    class Meta:
        ordering = ['-invited_at']
        unique_together = [('tournament', 'team')]
        indexes = [
            models.Index(fields=['tournament', 'status'], name='tournament_inv_status_idx'),
            models.Index(fields=['team', 'status'], name='team_inv_status_idx'),
            models.Index(fields=['invited_at']), 
            models.Index(fields=['expires_at']),
        ]
        verbose_name = "Tournament Team Invitation"
        verbose_name_plural = "Tournament Team Invitations"
    
    def __str__(self):
        return f"{self.tournament.name} → {self.team.name} ({self.get_status_display()})"
    
    def clean(self):
        """Validation logic for invitations"""
        # Cannot invite if tournament registration is closed
        if self.tournament and not self.tournament.allow_registration:
            raise ValidationError({
                'tournament': 'Cannot send invitations when tournament registration is closed.'
            })
        
        # Check if tournament has already started
        if self.tournament and self.tournament.start_date and timezone.now() > self.tournament.start_date:
            raise ValidationError({
                'tournament': 'Cannot send invitations after tournament has started.'
            })
        
        # Check if team is already registered
        if self.team and self.tournament:
            from .registration import Registration
            if Registration.objects.filter(
                tournament=self.tournament,
                team=self.team,
                status__in=['confirmed', 'pending', 'payment_submitted']
            ).exists():
                raise ValidationError({
                    'team': f'{self.team.name} is already registered for this tournament.'
                })
        
        # Validate team game matches tournament game
        if self.team and self.tournament:
            if self.team.game != self.tournament.game:
                raise ValidationError({
                    'team': f'Team game ({self.team.game}) does not match tournament game ({self.tournament.game}).'
                })
    
    def is_expired(self) -> bool:
        """Check if invitation has expired"""
        if self.status != self.Status.PENDING:
            return False
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def accept(self, responded_by, response_message: str = ""):
        """
        Accept the invitation and optionally create tournament registration.
        
        Args:
            responded_by: UserProfile of team member accepting
            response_message: Optional message from team
        """
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot accept invitation with status: {self.get_status_display()}")
        
        if self.is_expired():
            self.status = self.Status.EXPIRED
            self.save(update_fields=['status'])
            raise ValidationError("Invitation has expired")
        
        # Mark as accepted
        self.status = self.Status.ACCEPTED
        self.responded_by = responded_by
        self.responded_at = timezone.now()
        self.response_message = response_message
        self.save(update_fields=['status', 'responded_by', 'responded_at', 'response_message'])
        
        # Auto-register if enabled
        if self.auto_register_on_accept and not self.registration:
            from .registration import Registration
            registration = Registration.objects.create(
                tournament=self.tournament,
                team=self.team,
                status=Registration.CONFIRMED,  # Invited teams skip approval
                user=responded_by.user if hasattr(responded_by, 'user') else None,
                registration_data={'invited': True, 'invitation_id': self.id},
            )
            self.registration = registration
            self.save(update_fields=['registration'])
    
    def decline(self, responded_by, response_message: str = ""):
        """
        Decline the invitation.
        
        Args:
            responded_by: UserProfile of team member declining
            response_message: Optional message explaining decline
        """
        if self.status != self.Status.PENDING:
            raise ValidationError(f"Cannot decline invitation with status: {self.get_status_display()}")
        
        self.status = self.Status.DECLINED
        self.responded_by = responded_by
        self.responded_at = timezone.now()
        self.response_message = response_message
        self.save(update_fields=['status', 'responded_by', 'responded_at', 'response_message'])
    
    def cancel(self):
        """Cancel the invitation (organizer action)"""
        if self.status not in [self.Status.PENDING]:
            raise ValidationError(f"Cannot cancel invitation with status: {self.get_status_display()}")
        
        self.status = self.Status.CANCELLED
        self.save(update_fields=['status'])
    
    def mark_expired(self):
        """Mark invitation as expired (called by cron/task)"""
        if self.status == self.Status.PENDING and self.is_expired():
            self.status = self.Status.EXPIRED
            self.save(update_fields=['status'])
