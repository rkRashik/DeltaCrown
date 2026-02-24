"""
Emergency Substitution Request model.

TOC Sprint 3 — S3-M1
PRD Reference: §3.10 (Roster Lock & Emergency Substitution)

Allows team captains to request a player swap during a live tournament.
Organizers review and approve/deny in the TOC Participants Advanced panel.
"""

import uuid

from django.conf import settings
from django.db import models


class EmergencySubRequest(models.Model):
    """
    Emergency substitution request for an active tournament.

    Workflow:
        Captain submits → auto-checks (duplicate, eligibility, ban) →
        Organizer reviews in TOC → approve/deny → roster updated.
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_DENIED = "denied"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_DENIED, "Denied"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="emergency_sub_requests",
    )
    registration = models.ForeignKey(
        "tournaments.Registration",
        on_delete=models.CASCADE,
        related_name="emergency_sub_requests",
        help_text="The team registration this substitution is for.",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_sub_requests_made",
        help_text="Captain who submitted the request.",
    )

    dropping_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_sub_dropped",
        help_text="Player being removed from the roster.",
    )
    substitute_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_sub_incoming",
        help_text="Player being added to the roster.",
    )

    reason = models.TextField(
        help_text="Captain's explanation for the substitution.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_sub_reviews",
        help_text="Organizer/staff who reviewed the request.",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tournaments"
        ordering = ["-created_at"]
        verbose_name = "Emergency Sub Request"
        verbose_name_plural = "Emergency Sub Requests"

    def __str__(self):
        return (
            f"EmergencySub({self.tournament_id}) "
            f"{self.dropping_player} → {self.substitute_player} [{self.status}]"
        )

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    def approve(self, reviewer, notes=""):
        """Mark as approved by organizer."""
        from django.utils import timezone

        self.status = self.STATUS_APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes"])

    def deny(self, reviewer, notes=""):
        """Mark as denied by organizer."""
        from django.utils import timezone

        self.status = self.STATUS_DENIED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes"])
