"""
Team Registration Permission Request Model

Allows team members to request permission from team captain/manager
to register the team for tournaments.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from apps.tournaments.models import Tournament


class TeamRegistrationPermissionRequest(models.Model):
    """
    Request from team member to captain/manager for tournament registration permission.
    """
    
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CANCELLED = 'cancelled'
    
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]
    
    # Relationships
    team_id = models.IntegerField(
        db_index=True,
        db_column='team_id',
        help_text='Team ID for which permission is requested'
    )
    
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.CASCADE,
        related_name='permission_requests',
        help_text='Tournament the member wants to register for'
    )
    
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='registration_permission_requests',
        help_text='Team member requesting permission'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text='Current status of the request'
    )
    
    # Request details
    message = models.TextField(
        blank=True,
        help_text='Optional message from requester to captain'
    )
    
    # Response
    response_message = models.TextField(
        blank=True,
        help_text='Response from captain/manager'
    )
    
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permission_requests_responded',
        help_text='Captain/manager who responded to the request'
    )
    
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When the request was approved/rejected'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Team Registration Permission Request'
        verbose_name_plural = 'Team Registration Permission Requests'
        db_table = 'tournaments_team_permission_request'
        ordering = ['-created_at']
        unique_together = [
            ('team_id', 'tournament', 'requester', 'status')
        ]
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['team_id', 'status']),
            models.Index(fields=['requester', 'status']),
        ]
    
    def __str__(self):
        return f"{self.requester.username} → Team#{self.team_id} ({self.tournament.title}) - {self.get_status_display()}"
    
    def approve(self, approved_by, message: str = ''):
        """Approve the permission request"""
        self.status = self.STATUS_APPROVED
        self.responded_by = approved_by
        self.responded_at = timezone.now()
        self.response_message = message
        self.save()
        
        # Send notification to requester
        from apps.tournaments.services.notification_service import TournamentNotificationService
        TournamentNotificationService.notify_permission_approved(self)
    
    def reject(self, rejected_by, message: str = ''):
        """Reject the permission request"""
        self.status = self.STATUS_REJECTED
        self.responded_by = rejected_by
        self.responded_at = timezone.now()
        self.response_message = message
        self.save()
        
        # Send notification to requester
        from apps.tournaments.services.notification_service import TournamentNotificationService
        TournamentNotificationService.notify_permission_rejected(self)
    
    def cancel(self):
        """Cancel the request (by requester)"""
        if self.status == self.STATUS_PENDING:
            self.status = self.STATUS_CANCELLED
            self.save()
    
    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING
    
    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED
    
    @property
    def can_be_responded(self):
        return self.status == self.STATUS_PENDING
    
    def get_team_captains(self):
        """Get list of users who can respond to this request"""
        from apps.organizations.models import TeamMembership
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        
        return User.objects.filter(
            team_memberships__team=self.team,
            team_memberships__role__in=['captain', 'manager', 'admin'],
            team_memberships__is_active=True
        ).distinct()
