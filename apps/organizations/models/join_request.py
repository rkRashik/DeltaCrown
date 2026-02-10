"""
Team Join Request model for user-initiated applications.

Allows non-member users to request to join a team that has
is_recruiting=True. Team admins can then accept or decline.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TeamJoinRequest(models.Model):
    """
    User-initiated request to join a team.

    Lifecycle:
        PENDING → ACCEPTED (creates TeamMembership)
        PENDING → DECLINED
        PENDING → WITHDRAWN (by applicant)
    """

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        TRYOUT_SCHEDULED = 'TRYOUT_SCHEDULED', 'Tryout Scheduled'
        TRYOUT_COMPLETED = 'TRYOUT_COMPLETED', 'Tryout Completed'
        OFFER_SENT = 'OFFER_SENT', 'Offer Sent'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='join_requests',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_join_requests',
    )
    message = models.TextField(
        blank=True,
        max_length=500,
        help_text='Optional message from the applicant',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    # Tryout workflow fields (Point 1B)
    tryout_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Scheduled tryout date/time',
    )
    tryout_notes = models.TextField(
        blank=True,
        default='',
        max_length=1000,
        help_text='Internal notes about the tryout',
    )
    applied_position = models.CharField(
        max_length=60,
        blank=True,
        default='',
        help_text='Position the applicant is trying out for',
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_join_requests',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations_teamjoinrequest'
        ordering = ['-created_at']
        constraints = [
            # At most one pending request per user per team
            models.UniqueConstraint(
                fields=['team', 'user'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_join_request',
            ),
        ]

    def __str__(self):
        return f'{self.user} → {self.team} ({self.status})'
