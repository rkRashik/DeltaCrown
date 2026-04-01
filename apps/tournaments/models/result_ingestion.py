"""
Phase 5 §5.4–5.5: Automated Result Ingestion & Integrity Check models.

MatchIntegrityCheck compares manual player-submitted scores against
automated API-fetched data. Mismatches flag potential fraud for admin review.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class MatchIntegrityCheck(models.Model):
    """
    Stores the automated vs. manual result comparison for a match.

    Workflow:
    1. Players submit scores manually (MatchResultSubmission).
    2. AutomatedResultIngestionService fetches official data from
       the game API (Riot, Steam/Valve, etc.).
    3. This model records both payloads, the diff, and the verdict.
    4. If ``status`` is ``mismatch``, an admin alert is raised and
       the match is flagged for review.
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending API fetch")
        MATCH = "match", _("Scores match")
        MISMATCH = "mismatch", _("Score mismatch — flagged")
        API_ERROR = "api_error", _("API fetch failed")
        SKIPPED = "skipped", _("No API available for this game")

    class Source(models.TextChoices):
        RIOT = "riot", _("Riot Games API")
        STEAM = "steam", _("Steam / Valve API")
        FACEIT = "faceit", _("FACEIT API")
        MANUAL_OVERRIDE = "manual", _("Admin manual override")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    match = models.OneToOneField(
        "tournaments.Match",
        on_delete=models.CASCADE,
        related_name="integrity_check",
        verbose_name=_("Match"),
    )

    # What the players submitted
    manual_payload = models.JSONField(
        default=dict,
        verbose_name=_("Manual Submission"),
        help_text=_("Score data from player-submitted results."),
    )

    # What the API returned
    api_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("API Response"),
        help_text=_("Raw data fetched from the external game API."),
    )

    # Computed diff
    diff = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Diff"),
        help_text=_("Field-level differences between manual and API data."),
    )

    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.RIOT,
        verbose_name=_("API Source"),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name=_("Verification Status"),
    )

    # Admin resolution
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Reviewed By"),
    )
    review_notes = models.TextField(
        blank=True,
        default="",
        verbose_name=_("Review Notes"),
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    fetched_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("API Fetched At"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tournament_match_integrity_check"
        verbose_name = _("Match Integrity Check")
        verbose_name_plural = _("Match Integrity Checks")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Integrity — Match {self.match_id} ({self.status})"

    @property
    def is_flagged(self):
        return self.status == self.Status.MISMATCH
