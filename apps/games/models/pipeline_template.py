"""
GamePipelineTemplate — centralized per-game tournament pipeline templates.

Combines scoring configuration, map pool selection, and match pipeline
settings into reusable templates that tournament organizers can apply.

This replaces scattered hardcoded config (PIPELINE_OVERRIDES, DEFAULT_MAP_POOLS,
DEFAULT_CREDENTIAL_SCHEMA) with a single database-driven source of truth.
"""

from django.db import models


class GamePipelineTemplate(models.Model):
    """Reusable tournament configuration template for a game."""

    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="pipeline_templates",
        help_text="The game this template applies to",
    )
    name = models.CharField(
        max_length=150,
        help_text="Template name (e.g. 'Standard Competitive', 'Casual Scrims')",
    )
    is_default = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this is the default template for the game",
    )

    # Pipeline configuration
    PIPELINE_MODE_CHOICES = [
        ("veto", "Map Veto"),
        ("direct", "Direct Ready"),
        ("coin_toss", "Coin Toss"),
    ]
    pipeline_mode = models.CharField(
        max_length=20,
        choices=PIPELINE_MODE_CHOICES,
        default="direct",
        help_text="How the match-room pipeline starts (veto, direct, etc.)",
    )

    # Scoring configuration
    scoring_type = models.CharField(
        max_length=20,
        choices=[
            ('WIN_LOSS', 'Win/Loss Only'),
            ('POINTS', 'Points-based'),
            ('ROUNDS', 'Round-based (FPS)'),
            ('KILLS', 'Kill-based (BR)'),
            ('PLACEMENT', 'Placement-based (BR)'),
            ('GOALS', 'Goal-based (Sports)'),
            ('CUSTOM', 'Custom Scoring'),
        ],
        default='WIN_LOSS',
        help_text="Default scoring type for matches using this template",
    )

    # Match format
    DEFAULT_FORMAT_CHOICES = [
        ('BO1', 'Best of 1'),
        ('BO3', 'Best of 3'),
        ('BO5', 'Best of 5'),
        ('BO7', 'Best of 7'),
    ]
    default_match_format = models.CharField(
        max_length=10,
        choices=DEFAULT_FORMAT_CHOICES,
        default='BO3',
    )

    # Credential schema for lobby setup
    credential_schema = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'JSON array of lobby credential fields. Example: '
            '[{"key": "lobby_code", "label": "Lobby Code", "kind": "text", "required": true}]'
        ),
    )

    # Tiebreaker order for group stages
    tiebreakers = models.JSONField(
        default=list,
        blank=True,
        help_text="Ordered list of tiebreaker keys (e.g. ['goal_difference', 'goals_for'])",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games_pipeline_template"
        ordering = ["game", "-is_default", "name"]
        verbose_name = "Game Pipeline Template"
        verbose_name_plural = "Game Pipeline Templates"
        constraints = [
            # Only one default template per game
            models.UniqueConstraint(
                fields=["game"],
                condition=models.Q(is_default=True),
                name="unique_default_template_per_game",
            ),
        ]

    def __str__(self):
        default = " [DEFAULT]" if self.is_default else ""
        return f"{self.game.slug}: {self.name}{default}"

    @classmethod
    def get_default_for_game(cls, game):
        """Return the default template for a game, or None."""
        return cls.objects.filter(game=game, is_default=True, is_active=True).first()

    @classmethod
    def get_default_for_slug(cls, game_slug: str):
        """Return the default template for a game slug, or None."""
        return cls.objects.filter(
            game__slug=game_slug, is_default=True, is_active=True
        ).select_related("game").first()
