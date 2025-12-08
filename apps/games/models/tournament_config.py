"""
Tournament configuration for game-specific tournament rules.
"""

from django.db import models


class GameTournamentConfig(models.Model):
    """
    Tournament-specific configuration for a game.
    Defines match formats, scoring, tiebreakers, etc.
    """
    game = models.OneToOneField(
        'games.Game',
        on_delete=models.CASCADE,
        related_name='tournament_config'
    )
    
    # === MATCH FORMATS ===
    MATCH_FORMAT_CHOICES = [
        ('BO1', 'Best of 1'),
        ('BO3', 'Best of 3'),
        ('BO5', 'Best of 5'),
        ('BO7', 'Best of 7'),
        ('SINGLE', 'Single Match'),
        ('SERIES', 'Match Series'),
    ]
    available_match_formats = models.JSONField(
        default=list,
        help_text="List of allowed match formats (e.g., ['BO1', 'BO3', 'BO5'])"
    )
    default_match_format = models.CharField(
        max_length=20,
        choices=MATCH_FORMAT_CHOICES,
        default='BO3'
    )
    
    # === SCORING RULES ===
    SCORING_TYPE_CHOICES = [
        ('WIN_LOSS', 'Win/Loss Only'),
        ('POINTS', 'Points-based'),
        ('ROUNDS', 'Round-based (FPS)'),
        ('KILLS', 'Kill-based (BR)'),
        ('PLACEMENT', 'Placement-based (BR)'),
        ('GOALS', 'Goal-based (Sports)'),
        ('CUSTOM', 'Custom Scoring'),
    ]
    default_scoring_type = models.CharField(
        max_length=20,
        choices=SCORING_TYPE_CHOICES,
        default='WIN_LOSS'
    )
    
    scoring_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detailed scoring configuration (JSON)"
    )
    
    # === TIEBREAKERS ===
    default_tiebreakers = models.JSONField(
        default=list,
        help_text="Ordered list of tiebreaker criteria (e.g., ['head_to_head', 'round_diff', 'rounds_won'])"
    )
    
    # === BRACKET SETTINGS ===
    supports_single_elimination = models.BooleanField(default=True)
    supports_double_elimination = models.BooleanField(default=True)
    supports_round_robin = models.BooleanField(default=True)
    supports_swiss = models.BooleanField(default=False)
    supports_group_stage = models.BooleanField(default=True)
    
    # === MATCH SETTINGS ===
    default_match_duration_minutes = models.IntegerField(
        default=60,
        help_text="Expected match duration in minutes"
    )
    allow_draws = models.BooleanField(
        default=False,
        help_text="Can matches end in a draw?"
    )
    overtime_enabled = models.BooleanField(
        default=True,
        help_text="Is overtime/sudden death available?"
    )
    
    # === CHECK-IN SETTINGS ===
    require_check_in = models.BooleanField(
        default=True,
        help_text="Do teams need to check in before matches?"
    )
    check_in_window_minutes = models.IntegerField(
        default=30,
        help_text="How long before match start can teams check in?"
    )
    
    # === ADVANCED CONFIG ===
    extra_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Game-specific tournament configuration (JSON)"
    )
    
    # === REGISTRATION REQUIREMENTS (Phase 2) ===
    min_team_size = models.IntegerField(
        default=1,
        help_text="Minimum number of players per team"
    )
    max_team_size = models.IntegerField(
        default=5,
        help_text="Maximum number of players per team"
    )
    allow_cross_region = models.BooleanField(
        default=False,
        help_text="Whether teams can have players from different regions"
    )
    require_verified_email = models.BooleanField(
        default=True,
        help_text="Whether all players must have verified email addresses"
    )
    require_verified_phone = models.BooleanField(
        default=False,
        help_text="Whether all players must have verified phone numbers"
    )
    identity_requirements = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional identity validation requirements (e.g., {'min_account_level': 30})"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'games_tournament_config'
        verbose_name = 'Tournament Configuration'
        verbose_name_plural = 'Tournament Configurations'
    
    def __str__(self):
        return f"{self.game.name} - Tournament Config"
    
    def get_tiebreakers_display(self):
        """Get human-readable tiebreaker list."""
        tiebreaker_names = {
            'head_to_head': 'Head-to-Head',
            'round_diff': 'Round Difference',
            'rounds_won': 'Rounds Won',
            'goal_diff': 'Goal Difference',
            'goals_for': 'Goals For',
            'kills': 'Total Kills',
            'placement': 'Average Placement',
            'kda': 'KDA Ratio',
        }
        return [tiebreaker_names.get(tb, tb.title()) for tb in self.default_tiebreakers]
    
    def supports_format(self, format_type):
        """Check if this game supports a specific tournament format."""
        format_support = {
            'SINGLE_ELIMINATION': self.supports_single_elimination,
            'DOUBLE_ELIMINATION': self.supports_double_elimination,
            'ROUND_ROBIN': self.supports_round_robin,
            'SWISS': self.supports_swiss,
            'GROUP_STAGE': self.supports_group_stage,
        }
        return format_support.get(format_type, False)
