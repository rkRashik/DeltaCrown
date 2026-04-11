# apps/economy/models/policy.py
from __future__ import annotations

from django.db import models

from apps.common.models import SoftDeleteModel


class CoinPolicy(SoftDeleteModel):
    """
    Per-tournament coin policy. Enabled by default.
    NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    """
    tournament_id = models.IntegerField(unique=True, null=True, blank=True, db_index=True, help_text="Legacy tournament ID (reference only)")
    enabled = models.BooleanField(default=True)

    participation = models.PositiveIntegerField(default=5)
    top4 = models.PositiveIntegerField(default=25)
    runner_up = models.PositiveIntegerField(default=50)
    winner = models.PositiveIntegerField(default=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"CoinPolicy(tournament_id={self.tournament_id})"
