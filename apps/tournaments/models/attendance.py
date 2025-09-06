# apps/tournaments/models/attendance.py
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import UniqueConstraint


class MatchAttendance(models.Model):
    """
    Per-user attendance for a Match.
    - user: the account confirming attendance (usually a player)
    - match: the match in question
    - status: invited / confirmed / declined / late / absent
    - note: optional free text
    """
    STATUS = [
        ("invited", "Invited"),
        ("confirmed", "Confirmed"),
        ("declined", "Declined"),
        ("late", "Late"),
        ("absent", "Absent"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="match_attendance")
    match = models.ForeignKey("tournaments.Match", on_delete=models.CASCADE, related_name="attendance")
    status = models.CharField(max_length=16, choices=STATUS, default="invited", db_index=True)
    note = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["user", "match"], name="uq_match_attendance_user_match"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}→{self.match_id} [{self.status}]"
