from __future__ import annotations
from django.db import models

class TeamStats(models.Model):
    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="stats_snapshots")
    matches_played = models.PositiveIntegerField(default=0)
    wins = models.PositiveIntegerField(default=0)
    losses = models.PositiveIntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # 0–100
    streak = models.IntegerField(default=0, help_text="Positive = current win streak, negative = current loss streak")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["team"]),
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return f"Stats for {self.team_id} @ {self.updated_at:%Y-%m-%d %H:%M}"
