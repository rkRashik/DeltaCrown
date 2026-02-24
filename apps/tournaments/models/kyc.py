"""
KYC (Know Your Customer) Submission model.

TOC Sprint 4 — S4-M2
PRD Reference: §4.9 (KYC / Identity Verification for Prize Claims)

Players submit identity documents to claim prizes above a threshold.
Organizers/admins review and approve/reject in the TOC Prize tab.
"""

import uuid

from django.conf import settings
from django.db import models


class KYCSubmission(models.Model):
    """
    Player's identity verification submission for prize claims.

    Statuses:
        submitted — player uploaded docs
        approved  — organizer verified identity
        rejected  — docs rejected (blurry, mismatch, expired)
        flagged   — escalated to platform admin
        expired   — verification expired (>6 months)
    """

    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_FLAGGED = "flagged"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_FLAGGED, "Flagged"),
        (STATUS_EXPIRED, "Expired"),
    ]

    DOC_NATIONAL_ID = "national_id"
    DOC_PASSPORT = "passport"
    DOC_STUDENT_ID = "student_id"
    DOC_MFS_ACCOUNT = "mfs_account"
    DOC_SELFIE_WITH_ID = "selfie_with_id"

    DOCUMENT_TYPE_CHOICES = [
        (DOC_NATIONAL_ID, "National ID (NID)"),
        (DOC_PASSPORT, "Passport"),
        (DOC_STUDENT_ID, "Student ID"),
        (DOC_MFS_ACCOUNT, "MFS Account Screenshot"),
        (DOC_SELFIE_WITH_ID, "Selfie with ID"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kyc_submissions",
    )
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="kyc_submissions",
    )
    prize_claim = models.ForeignKey(
        "tournaments.PrizeClaim",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kyc_submissions",
    )

    document_type = models.CharField(
        max_length=30,
        choices=DOCUMENT_TYPE_CHOICES,
    )
    document_front = models.FileField(
        upload_to="kyc/documents/",
        help_text="Front of document (image/PDF).",
    )
    document_back = models.FileField(
        upload_to="kyc/documents/",
        null=True,
        blank=True,
        help_text="Back of document (for NID).",
    )
    selfie_image = models.ImageField(
        upload_to="kyc/selfies/",
        null=True,
        blank=True,
        help_text="Selfie with ID.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
        db_index=True,
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tournament_kyc_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(
        blank=True,
        default="",
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Verification valid until (default: 6 months from approval).",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tournaments"
        ordering = ["-created_at"]
        verbose_name = "KYC Submission"
        verbose_name_plural = "KYC Submissions"

    def __str__(self):
        return f"KYC({self.user}) [{self.document_type}] — {self.status}"

    def approve(self, reviewer):
        """Approve this KYC submission."""
        from django.utils import timezone
        from datetime import timedelta

        self.status = self.STATUS_APPROVED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.expires_at = timezone.now() + timedelta(days=180)
        self.save(update_fields=["status", "reviewer", "reviewed_at", "expires_at"])

    def reject(self, reviewer, reason=""):
        """Reject this KYC submission."""
        from django.utils import timezone

        self.status = self.STATUS_REJECTED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.rejection_reason = reason
        self.save(update_fields=["status", "reviewer", "reviewed_at", "rejection_reason"])

    def flag(self, reviewer):
        """Escalate to platform admin."""
        from django.utils import timezone

        self.status = self.STATUS_FLAGGED
        self.reviewer = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewer", "reviewed_at"])
