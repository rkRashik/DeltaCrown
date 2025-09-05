from __future__ import annotations

from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        REG_CONFIRMED    = "reg_confirmed",    "Registration confirmed"
        BRACKET_READY    = "bracket_ready",    "Bracket generated"
        MATCH_SCHEDULED  = "match_scheduled",  "Match scheduled"
        RESULT_VERIFIED  = "result_verified",  "Result verified"
        PAYMENT_VERIFIED = "payment_verified", "Payment verified"
        CHECKIN_OPEN     = "checkin_open",     "Check-in window open"
        GENERIC          = "generic",          "Generic"

    # NOTE: tests filter on `event`, so we keep a free-form field here.
    # `type` remains the canonical enum used by admin/filters.
    event = models.CharField(max_length=64, db_index=True, default="generic")

    # Canonical enum for internal use (admin filters, etc.)
    type = models.CharField(max_length=40, choices=Type.choices, db_index=True, default=Type.GENERIC)

    title = models.CharField(max_length=140)
    body = models.TextField(blank=True)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Your project uses auth.User as recipient
    recipient = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )
    match = models.ForeignKey(
        "tournaments.Match",
        on_delete=models.SET_NULL,
        related_name="notifications",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read", "created_at"]),
            models.Index(fields=["recipient", "type", "tournament", "match"]),
        ]

    def __str__(self) -> str:
        return f"{self.event or self.type}: {self.title}"

    def save(self, *args, **kwargs):
        """
        Keep `event` and `type` sensibly in sync:
        - event is free-form (e.g. "match_result") used by tests.
        - type is constrained; if event isn't a known enum, fall back to GENERIC.
        """
        if not self.event:
            self.event = self.type or self.Type.GENERIC
        if self.type not in self.Type.values:
            # map unknown to GENERIC but retain the exact event string
            self.type = self.Type.GENERIC
        super().save(*args, **kwargs)
