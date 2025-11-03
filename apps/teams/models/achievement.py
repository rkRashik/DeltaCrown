from __future__ import annotations
from django.db import models

class TeamAchievement(models.Model):
    class Placement(models.TextChoices):
        WINNER = "WINNER", "Winner"
        RUNNER_UP = "RUNNER_UP", "Runner-up"
        TOP4 = "TOP4", "Top 4"
        TOP8 = "TOP8", "Top 8"
        PARTICIPANT = "PARTICIPANT", "Participant"

    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="achievements")
    title = models.CharField(max_length=160, help_text="Tournament or event name")
    placement = models.CharField(max_length=20, choices=Placement.choices, default=Placement.PARTICIPANT)
    year = models.PositiveIntegerField(blank=True, null=True)
    notes = models.CharField(max_length=255, blank=True, default="")
    # NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    tournament_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "title"]
        indexes = [
            models.Index(fields=["team"]),
            models.Index(fields=["year"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.get_placement_display()}"
