"""
GameMatchPipeline — per-game phase sequence configuration.

Each Game can have one pipeline defining the exact phases a match room
loads, in order.  If no pipeline exists for a game the frontend falls
back to the existing ``_build_phase_order()`` logic in the match-room
view.

Phase 5 adds 5 archetype pipelines with new phases:
  hero_draft, side_selection, lobby_distribution, server_assignment,
  platform_match, matrix_results.
"""

from django.db import models

from apps.games.constants import get_archetype_for_game, get_archetype_phases


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
        ("hero_draft", "Hero Draft"),
        ("side_selection", "Side Selection"),
        ("direct_ready", "Direct Ready"),
        ("lobby_distribution", "Lobby Distribution"),
        ("server_assignment", "Server Assignment"),
        ("platform_match", "Platform Match"),
        ("lobby_setup", "Lobby Setup"),
        ("live", "Live"),
        ("results", "Results"),
        ("matrix_results", "Matrix Results"),
        ("completed", "Completed"),
    ]

    ARCHETYPE_CHOICES = [
        ("tactical_fps", "Tactical FPS"),
        ("moba", "MOBA"),
        ("battle_royale", "Battle Royale"),
        ("sports", "Sports"),
        ("duel_1v1", "1v1 / Duel"),
    ]

    archetype = models.CharField(
        max_length=30,
        choices=ARCHETYPE_CHOICES,
        blank=True,
        default="",
        help_text="Game archetype — auto-resolved from game if blank.",
    )

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
        arch = self.resolved_archetype()
        return f"Pipeline: {self.game} [{arch}] → {self.phases}"

    def resolved_archetype(self):
        """Return archetype — use stored value or auto-resolve from game."""
        if self.archetype:
            return self.archetype
        game = self.game
        return get_archetype_for_game(
            getattr(game, 'slug', ''),
            getattr(game, 'game_type', ''),
        )

    def get_phase_order(self):
        """Return a validated copy of ``phases`` containing only known keys.

        If phases is empty, fall back to the archetype default phases.
        """
        valid = {key for key, _ in self.VALID_PHASES}
        ordered = [p for p in (self.phases or []) if p in valid]
        if ordered:
            return ordered
        return [
            p for p in get_archetype_phases(
                getattr(self.game, 'slug', ''),
                getattr(self.game, 'game_type', ''),
            ) if p in valid
        ]
