# apps/tournaments/models/registration_request.py
"""
Registration Request model for non-captain team members to request
captain approval for tournament registration.
"""
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class RegistrationRequest(models.Model):
    """
    Allows non-captain team members to request that their captain
    register the team for a tournament.
    """
    
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
    
    # Who is requesting
    requester = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="registration_requests_sent"
    )
    
    # What they want to register for
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="registration_requests"
    )
    
    # Which team
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="registration_requests"
    )
    
    # Captain who needs to approve
    captain = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="registration_requests_received"
    )
    
    # Request details
    message = models.TextField(
        blank=True,
        max_length=500,
        help_text="Optional message to the captain"
    )
    
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Response from captain
    response_message = models.TextField(blank=True, max_length=500)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Request expires if not responded to by this time"
    )
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tournament", "team", "status"]),
            models.Index(fields=["captain", "status"]),
            models.Index(fields=["requester", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tournament", "team", "requester"],
                condition=models.Q(status="PENDING"),
                name="uq_one_pending_request_per_requester_team_tournament"
            )
        ]
    
    def __str__(self):
        return f"{self.requester} → {self.captain} for {self.tournament.name}"
    
    def save(self, *args, **kwargs):
        # Set expiration to tournament registration close date or 7 days
        if not self.expires_at:
            try:
                reg_close = self.tournament.reg_close_at
                if reg_close:
                    self.expires_at = reg_close
                else:
                    self.expires_at = timezone.now() + timezone.timedelta(days=7)
            except Exception:
                self.expires_at = timezone.now() + timezone.timedelta(days=7)
        
        super().save(*args, **kwargs)
    
    def clean(self):
        # Verify requester is actually a member of the team
        try:
            from apps.teams.models import TeamMembership
            membership = TeamMembership.objects.filter(
                team=self.team,
                profile=self.requester,
                status="ACTIVE"
            ).first()
            
            if not membership:
                raise ValidationError({
                    "requester": "Requester must be an active member of the team."
                })
            
            # Verify captain is actually the captain
            if self.team.captain_id != self.captain_id:
                raise ValidationError({
                    "captain": "Specified captain is not the team captain."
                })
            
            # Don't allow captain to request from themselves
            if self.requester_id == self.captain_id:
                raise ValidationError({
                    "requester": "Captain can register directly without requesting."
                })
                
        except ImportError:
            pass
    
    def approve(self, response_message=""):
        """Mark request as approved"""
        self.status = self.Status.APPROVED
        self.response_message = response_message
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "response_message", "responded_at"])
    
    def reject(self, response_message=""):
        """Mark request as rejected"""
        self.status = self.Status.REJECTED
        self.response_message = response_message
        self.responded_at = timezone.now()
        self.save(update_fields=["status", "response_message", "responded_at"])
    
    @property
    def is_expired(self):
        """Check if request has expired"""
        return timezone.now() > self.expires_at
    
    def mark_expired(self):
        """Mark request as expired"""
        if self.status == self.Status.PENDING and self.is_expired:
            self.status = self.Status.EXPIRED
            self.save(update_fields=["status"])
            return True
        return False
