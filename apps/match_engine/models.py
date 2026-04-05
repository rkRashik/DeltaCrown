"""
GameMatchPipeline — per-game phase sequence configuration.

Canonical location: apps.match_engine.models (Phase 6 extraction from apps.games).

Each Game can have one pipeline defining the exact phases a match room
loads, in order.  If no pipeline exists for a game the frontend falls
back to the existing ``_build_phase_order()`` logic in the match-room
view.

Phase 5 adds 5 archetype pipelines with new phases:
  hero_draft, side_selection, lobby_distribution, server_assignment,
  platform_match, matrix_results.
"""

from django.conf import settings
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
        app_label = "match_engine"
        db_table = "games_match_pipeline"
        verbose_name = "Game Match Pipeline"
        verbose_name_plural = "Game Match Pipelines"

    def __str__(self) -> str:
        arch = self.resolved_archetype()
        return f"Pipeline: {self.game} [{arch}] → {self.phases}"

    def resolved_archetype(self) -> str:
        """Return archetype — use stored value or auto-resolve from game."""
        if self.archetype:
            return self.archetype
        game = self.game
        return get_archetype_for_game(
            getattr(game, 'slug', ''),
            getattr(game, 'game_type', ''),
        )

    def get_phase_order(self) -> list:
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


# ───────────────────────────────────────────────────────────────────────
# MatchChatMessage — Persistent chat log for match lobby (Phase 8)
# ───────────────────────────────────────────────────────────────────────

class MatchChatMessage(models.Model):
    """A single chat message in a match lobby. Persists across page refreshes."""

    MSG_TYPE_CHOICES = [
        ("chat", "Chat"),
        ("system", "System"),
        ("voice_link", "Voice Link"),
    ]

    match_id = models.PositiveIntegerField(db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    display_name = models.CharField(max_length=100)
    avatar_url = models.URLField(max_length=500, blank=True, default="")
    side = models.SmallIntegerField(default=0, help_text="1=P1, 2=P2, 0=staff/system")
    text = models.TextField(max_length=500)
    msg_type = models.CharField(max_length=12, choices=MSG_TYPE_CHOICES, default="chat")
    is_official = models.BooleanField(default=False)
    extra = models.JSONField(default=dict, blank=True, help_text="voice_url etc.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = "match_engine"
        db_table = "match_engine_chat_message"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["match_id", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"[Match {self.match_id}] {self.display_name}: {self.text[:40]}"

    def to_ws_dict(self) -> dict:
        """Serialise for WebSocket broadcast."""
        return {
            "message_id": str(self.pk),
            "match_id": self.match_id,
            "user_id": self.user_id or 0,
            "username": self.display_name,
            "display_name": self.display_name,
            "side": self.side,
            "is_official": self.is_official,
            "avatar_url": self.avatar_url,
            "text": self.text,
            "msg_type": self.msg_type,
            "extra": self.extra or {},
            "timestamp": self.created_at.isoformat() if self.created_at else "",
        }
