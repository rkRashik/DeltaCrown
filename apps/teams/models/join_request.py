# apps/teams/models/join_request.py
"""
Team Join Request Models
========================
Models for handling professional team join requests with approval workflow.
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class TeamJoinRequest(models.Model):
    """
    Model for team join requests.
    Users apply to join a team, team management can approve/reject.
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled by User'),
    ]
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='join_requests'
    )
    applicant = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='team_join_requests'
    )
    
    # Application details
    message = models.TextField(
        max_length=1000,
        blank=True,
        help_text="Optional message from applicant explaining why they want to join"
    )
    preferred_role = models.CharField(
        max_length=20,
        blank=True,
        help_text="Player, Substitute, Coach, etc."
    )
    game_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Applicant's game ID at time of request"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    # Review information
    reviewed_by = models.ForeignKey(
        'user_profile.UserProfile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewed_join_requests'
    )
    review_note = models.TextField(
        max_length=500,
        blank=True,
        help_text="Optional note from reviewer"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', 'status', '-created_at']),
            models.Index(fields=['applicant', 'status', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'applicant'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_request_per_team'
            )
        ]
    
    def __str__(self):
        return f"{self.applicant.user.username} → {self.team.name} ({self.status})"
    
    def approve(self, reviewer):
        """Approve the join request and create team membership."""
        from .membership import TeamMembership
        
        if self.status != 'PENDING':
            raise ValueError(f"Cannot approve request with status {self.status}")
        
        # Create team membership
        membership = TeamMembership.objects.create(
            team=self.team,
            profile=self.applicant,
            role=self.preferred_role or 'PLAYER',
            status='ACTIVE',
            joined_at=timezone.now()
        )
        
        # Update request status
        self.status = 'APPROVED'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save()
        
        return membership
    
    def reject(self, reviewer, note=""):
        """Reject the join request."""
        if self.status != 'PENDING':
            raise ValueError(f"Cannot reject request with status {self.status}")
        
        self.status = 'REJECTED'
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_note = note
        self.save()
    
    def cancel(self):
        """Allow user to cancel their own request."""
        if self.status != 'PENDING':
            raise ValueError(f"Cannot cancel request with status {self.status}")
        
        self.status = 'CANCELLED'
        self.updated_at = timezone.now()
        self.save()
    
    @property
    def is_pending(self):
        return self.status == 'PENDING'
    
    @property
    def can_be_reviewed(self):
        return self.status == 'PENDING'
