"""
Hub support ticket model for participant-facing support/dispute history.

Stores support requests submitted from The Hub so users can see their own
ticket history and organizers can triage requests with clear status labels.
"""

from django.conf import settings
from django.db import models


class HubSupportTicket(models.Model):
    CATEGORY_GENERAL = 'general'
    CATEGORY_DISPUTE = 'dispute'
    CATEGORY_TECHNICAL = 'technical'
    CATEGORY_PAYMENT = 'payment'

    CATEGORY_CHOICES = [
        (CATEGORY_GENERAL, 'General Inquiry'),
        (CATEGORY_DISPUTE, 'Match Dispute'),
        (CATEGORY_TECHNICAL, 'Technical Issue'),
        (CATEGORY_PAYMENT, 'Payment / Prize'),
    ]

    STATUS_OPEN = 'open'
    STATUS_IN_REVIEW = 'in_review'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_REVIEW, 'In Review'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]

    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='hub_support_tickets',
    )
    registration = models.ForeignKey(
        'tournaments.Registration',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hub_support_tickets',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hub_support_tickets',
    )
    team_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Team ID for team registrations (if applicable).',
    )

    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_GENERAL)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    match_ref = models.CharField(max_length=120, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)

    organizer_notes = models.TextField(blank=True, default='')
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_hub_support_tickets',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tournaments_hub_support_ticket'
        verbose_name = 'Hub Support Ticket'
        verbose_name_plural = 'Hub Support Tickets'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tournament', 'created_at'], name='idx_hub_ticket_tour_created'),
            models.Index(fields=['created_by', 'created_at'], name='idx_hub_ticket_user_created'),
            models.Index(fields=['registration', 'status'], name='idx_hub_ticket_reg_status'),
            models.Index(fields=['team_id', 'status'], name='idx_hub_ticket_team_status'),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.subject}"
