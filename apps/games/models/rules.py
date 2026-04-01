"""
Game configuration models for rules, validation, and identity requirements.

This module provides the configuration layer for all game-specific behavior:
- Player identity requirements (Riot ID, Steam ID, etc.) - using existing GamePlayerIdentityConfig
- Match result schemas (what fields are valid/required)
- Scoring rules (how winners are determined)

These models enable a declarative, database-driven approach to game logic,
eliminating hardcoded game-specific behavior.

Phase 2, Epic 2.1: Game Configuration Models
Reference: SMART_REG_AND_RULES_PART_3.md, ARCH_PLAN_PART_1.md
"""

from django.core.exceptions import ValidationError
from django.db import models


class GameMatchResultSchema(models.Model):
    """
    Defines the structure and validation rules for match results.

    Each game has different match result formats:
    - Valorant: rounds_won, rounds_lost, agent_used, acs, kills, deaths
    - PUBG: placement, kills, damage_dealt, survival_time
    - FIFA: goals_scored, goals_conceded, possession_percentage

    This model enables dynamic validation of match result submissions.
    """

    FIELD_TYPE_CHOICES = [
        ("integer", "Integer"),
        ("decimal", "Decimal"),
        ("text", "Text"),
        ("boolean", "Boolean"),
        ("enum", "Enum (predefined choices)"),
        ("json", "JSON Object"),
    ]

    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="match_result_schemas",
        help_text="The game this schema applies to",
    )
    field_name = models.CharField(
        max_length=100,
        help_text="Field name in match result payload (e.g., 'kills', 'placement')",
    )
    display_label = models.CharField(
        max_length=200,
        help_text="User-facing label (e.g., 'Kills', 'Final Placement')",
    )
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        help_text="Data type of this field",
    )
    validation = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional validation rules (e.g., {'min': 0, 'max': 100} for integers, {'choices': [...]} for enums)",
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this field must be present in match results",
    )
    help_text = models.TextField(
        blank=True,
        help_text="Instructions for tournament organizers/submitters",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["game", "field_name"]
        unique_together = [["game", "field_name"]]
        verbose_name = "Game Match Result Schema"
        verbose_name_plural = "Game Match Result Schemas"
        db_table = "games_match_result_schema"

    def __str__(self):
        required = "required" if self.is_required else "optional"
        return f"{self.game.slug}: {self.field_name} ({self.field_type}, {required})"

    def clean(self):
        """Validate schema configuration."""
        # Validate enum choices are provided
        if self.field_type == "enum" and not self.validation.get("choices"):
            raise ValidationError(
                {"validation": "Enum fields must specify 'choices' in validation"}
            )

        # Validate min/max are present for numeric types with bounds
        if self.field_type in ["integer", "decimal"]:
            if "min" in self.validation and "max" in self.validation:
                if self.validation["min"] > self.validation["max"]:
                    raise ValidationError(
                        {"validation": "min must be less than or equal to max"}
                    )


class GameScoringRule(models.Model):
    """
    Defines how match results are scored and winners determined.

    Different games have different scoring systems:
    - Win/Loss: Binary outcome (MOBAs, FPS 1v1)
    - Points Accumulation: Total kills, damage, etc.
    - Placement Order: Battle Royale ranking (1st = highest points)
    - Custom: Complex multi-factor scoring

    This model stores the scoring algorithm configuration.
    """

    RULE_TYPE_CHOICES = [
        ("win_loss", "Win/Loss (binary outcome)"),
        ("points_accumulation", "Points Accumulation (sum of stats)"),
        ("placement_order", "Placement Order (rank-based)"),
        ("time_based", "Time-Based (fastest time wins)"),
        ("custom", "Custom Logic"),
    ]

    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="scoring_rules",
        help_text="The game this scoring rule applies to",
    )
    rule_type = models.CharField(
        max_length=50,
        choices=RULE_TYPE_CHOICES,
        help_text="Type of scoring algorithm",
    )
    config = models.JSONField(
        default=dict,
        help_text="Scoring configuration (e.g., {'kill_points': 1, 'placement_points': [10, 6, 4, 2]})",
    )
    description = models.TextField(
        help_text="Human-readable explanation of this scoring rule",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rule is currently in use",
    )
    priority = models.IntegerField(
        default=0,
        help_text="Priority order when multiple rules exist (higher = used first)",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["game", "-priority", "rule_type"]
        verbose_name = "Game Scoring Rule"
        verbose_name_plural = "Game Scoring Rules"
        db_table = "games_scoring_rule"

    def __str__(self):
        return f"{self.game.slug}: {self.get_rule_type_display()}"

    def clean(self):
        """Validate scoring configuration."""
        if self.rule_type == "points_accumulation":
            # Must specify point fields
            if not self.config.get("point_fields"):
                raise ValidationError(
                    {
                        "config": "points_accumulation requires 'point_fields' in config"
                    }
                )

        if self.rule_type == "placement_order":
            # Must specify placement points mapping
            if not self.config.get("placement_points"):
                raise ValidationError(
                    {"config": "placement_order requires 'placement_points' in config"}
                )


# ---------------------------------------------------------------------------
# Phase 5 §5.2: VetoConfiguration — game-level veto / draft template
# ---------------------------------------------------------------------------

class VetoConfiguration(models.Model):
    """
    Defines game-level veto / draft rules that serve as the template when
    creating a MatchVetoSession.

    Supports customizable sequences:
      - Map veto: [{"action":"ban","team":"A"},{"action":"ban","team":"B"},
                   {"action":"pick","team":"A"}, ...]
      - Hero draft: [{"action":"ban","team":"A","count":2},
                     {"action":"pick","team":"B","count":3}, ...]

    The ``time_per_action_seconds`` field enforces strict draft timers.
    """

    VETO_DOMAIN_CHOICES = [
        ("map", "Map Veto"),
        ("hero", "Hero / Champion Draft"),
        ("operator", "Operator / Agent Ban"),
        ("custom", "Custom"),
    ]

    game = models.ForeignKey(
        "games.Game",
        on_delete=models.CASCADE,
        related_name="veto_configurations",
        help_text="The game this veto/draft configuration applies to.",
    )
    name = models.CharField(
        max_length=120,
        help_text='Human label, e.g. "BO3 Map Veto" or "Captain\'s Mode Draft".',
    )
    domain = models.CharField(
        max_length=20,
        choices=VETO_DOMAIN_CHOICES,
        default="map",
        help_text="What entity is being banned/picked (maps, heroes, etc.).",
    )
    sequence = models.JSONField(
        default=list,
        help_text=(
            'Ordered list of veto steps. Each step: '
            '{"action": "ban"|"pick", "team": "A"|"B", "count": 1}. '
            'Example BO3: Ban-Ban-Pick-Pick-Ban-Ban-Decider.'
        ),
    )
    pool = models.JSONField(
        default=list,
        blank=True,
        help_text="Default pool of available items (map names, hero names, etc.).",
    )
    time_per_action_seconds = models.PositiveIntegerField(
        default=30,
        help_text="Seconds allowed per ban/pick action before auto-random.",
    )
    auto_random_on_timeout = models.BooleanField(
        default=True,
        help_text="If True, a random choice is made when the timer expires.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "games_veto_configuration"
        verbose_name = "Veto Configuration"
        verbose_name_plural = "Veto Configurations"
        ordering = ["game", "name"]
        unique_together = [("game", "name")]

    def __str__(self):
        return f"{self.game.slug}: {self.name} ({self.get_domain_display()})"

    def total_steps(self):
        return sum(step.get("count", 1) for step in (self.sequence or []))
