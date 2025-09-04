# apps/tournaments/models_registration_policy.py
from __future__ import annotations
from django.db import models
from django.core.exceptions import ValidationError


class TournamentRegistrationPolicy(models.Model):
    MODE_SOLO = "solo"
    MODE_TEAM = "team"
    MODE_DUO = "duo"
    MODE_CHOICES = (
        (MODE_SOLO, "Solo (1v1)"),
        (MODE_TEAM, "Team"),
        (MODE_DUO, "Duo (2v2)"),
    )

    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="registration_policy",
    )
    mode = models.CharField(max_length=8, choices=MODE_CHOICES, default=MODE_TEAM)
    team_size_min = models.PositiveSmallIntegerField(default=1)
    team_size_max = models.PositiveSmallIntegerField(default=5)

    def __str__(self):
        return f"{self.tournament} – {self.mode} [{self.team_size_min}-{self.team_size_max}]"

    # Server-side guardrail so choices depend on the game's logic even on ADD
    def clean(self):
        # Infer allowed modes by game (extend as you add more game configs)
        game = (getattr(self.tournament, "game", "") or "").strip().lower() if self.tournament_id else ""
        allowed = {self.MODE_SOLO, self.MODE_TEAM, self.MODE_DUO}
        if game == "valorant":
            allowed = {self.MODE_TEAM}
        elif game == "efootball":
            allowed = {self.MODE_SOLO, self.MODE_DUO}

        if self.mode not in allowed:
            raise ValidationError({"mode": f"Mode '{self.mode}' is not permitted for game '{game or 'Unknown'}'."})

        # Simple team-size sanity
        if self.team_size_min > self.team_size_max:
            raise ValidationError({"team_size_min": "Minimum cannot exceed maximum."})
