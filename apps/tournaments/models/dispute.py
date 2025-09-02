# apps/tournaments/models/dispute.py
from django.db import models

class MatchDispute(models.Model):
    match = models.ForeignKey("Match", on_delete=models.CASCADE, related_name="disputes")
    opened_by = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes_opened",
    )
    resolver = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disputes_resolved",
    )

    # Status flag used in views/tests: filter(match=m, is_open=True)
    is_open = models.BooleanField(default=True)

    status = models.CharField(
        max_length=16,
        choices=[("open", "Open"), ("resolved", "Resolved"), ("rejected", "Rejected")],
        default="open",
    )
    reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["match", "status"]),
            models.Index(fields=["match", "is_open"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Dispute #{self.id} on match #{self.match_id}"
