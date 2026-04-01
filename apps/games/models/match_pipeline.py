"""
GameMatchPipeline — per-game phase sequence configuration.

Each Game can have one pipeline defining the exact phases a match room
loads, in order.  If no pipeline exists for a game the frontend falls
back to the existing ``_build_phase_order()`` logic in the match-room
view.
"""

from django.db import models


class GameMatchPipeline(models.Model):
    """Maps a Game to its canonical match-room phase sequence."""

    game = models.OneToOneField(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="match_pipeline",
    )

    VALID_PHASES = [
        ("coin_toss", "Coin Toss"),
        ("map_veto", "Map Veto"),
        ("direct_ready", "Direct Ready"),
        ("lobby_setup", "Lobby Setup"),
        ("live", "Live"),
        ("results", "Results"),
        ("completed", "Completed"),
    ]

    phases = models.JSONField(
        default=list,
        help_text=(
            'Ordered list of phase keys the match room will execute. '
            'Example: ["direct_ready", "lobby_setup", "live", "results", "completed"]'
        ),
    )

    require_coin_toss = models.BooleanField(
        default=False,
        help_text="Pre-pend coin_toss phase even if not in phases list.",
    )

    require_map_veto = models.BooleanField(
        default=False,
        help_text="Use map_veto instead of direct_ready for phase1.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games_match_pipeline"
        verbose_name = "Game Match Pipeline"
        verbose_name_plural = "Game Match Pipelines"

    def __str__(self):
        return f"Pipeline: {self.game} → {self.phases}"

    def get_phase_order(self):
        """Return a validated copy of ``phases`` containing only known keys."""
        valid = {key for key, _ in self.VALID_PHASES}
        return [p for p in (self.phases or []) if p in valid]
