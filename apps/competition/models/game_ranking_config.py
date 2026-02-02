"""GameRankingConfig model - per-game ranking configuration."""
from django.db import models


class GameRankingConfig(models.Model):
    """
    Per-game ranking configuration (Phase 3A-B).
    
    Stores scoring weights, tier thresholds, decay policies, and verification
    rules for each supported game. Used by RankingComputeService to calculate
    team rankings.
    
    Supported Games (11):
    - League of Legends (LOL)
    - VALORANT (VAL)
    - Counter-Strike 2 (CS2)
    - Dota 2 (DOTA2)
    - Rocket League (RL)
    - Apex Legends (APEX)
    - Overwatch 2 (OW2)
    - Fortnite (FORT)
    - Call of Duty (COD)
    - Rainbow Six Siege (R6)
    - PUBG: Battlegrounds (PUBG)
    """
    
    # Primary key on game_id (no auto-increment, manually set)
    game_id = models.CharField(
        max_length=10,
        primary_key=True,
        help_text="Game identifier (e.g., 'LOL', 'VAL', 'CS2')"
    )
    
    game_name = models.CharField(
        max_length=100,
        help_text="Human-readable game name (e.g., 'League of Legends')"
    )
    
    # Scoring configuration (JSON)
    scoring_weights = models.JSONField(
        default=dict,
        help_text=(
            "Point values for different activities. "
            "Example: {tournament_win: 500, verified_match_win: 10, "
            "challenge_completion: 50, activity_participation: 5}"
        )
    )
    
    # Tier boundaries (JSON)
    tier_thresholds = models.JSONField(
        default=dict,
        help_text=(
            "Score thresholds for each tier. "
            "Example: {DIAMOND: 2000, PLATINUM: 1200, GOLD: 600, "
            "SILVER: 250, BRONZE: 100, UNRANKED: 0}"
        )
    )
    
    # Decay policy (JSON)
    decay_policy = models.JSONField(
        default=dict,
        help_text=(
            "Inactivity decay settings. "
            "Example: {enabled: true, inactivity_threshold_days: 30, "
            "decay_rate_per_day: 0.01}"
        )
    )
    
    # Verification rules (JSON)
    verification_rules = models.JSONField(
        default=dict,
        help_text=(
            "Match verification requirements. "
            "Example: {require_opponent_confirmation: true, "
            "auto_verify_after_hours: 72, provisional_weight: 0.3}"
        )
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this game is currently accepting match reports"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'competition_game_ranking_config'
        verbose_name = 'Game Ranking Config'
        verbose_name_plural = 'Game Ranking Configs'
        ordering = ['game_name']
    
    def __str__(self):
        return f"{self.game_name} ({self.game_id})"
