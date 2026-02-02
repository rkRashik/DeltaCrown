"""TeamGameRankingSnapshot model - per-game team rankings."""
from django.db import models


class TeamGameRankingSnapshot(models.Model):
    """
    Per-game team ranking snapshot (Phase 3A-B).
    
    Stores current ranking for a team in a specific game. Updated by
    RankingComputeService whenever new verified matches are processed.
    
    This is the SOURCE OF TRUTH for game-specific rankings displayed in
    team detail pages and leaderboards.
    """
    
    TIER_CHOICES = [
        ('DIAMOND', 'Diamond'),
        ('PLATINUM', 'Platinum'),
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'),
        ('BRONZE', 'Bronze'),
        ('UNRANKED', 'Unranked'),
    ]
    
    CONFIDENCE_CHOICES = [
        ('STABLE', 'Stable'),           # 20+ verified matches
        ('ESTABLISHED', 'Established'),  # 10-19 verified matches
        ('PROVISIONAL', 'Provisional'),  # 1-9 verified matches
    ]
    
    # Composite key: team + game
    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='game_ranking_snapshots'
    )
    
    game_id = models.CharField(
        max_length=10,
        help_text="Game identifier (e.g., 'LOL', 'VAL', 'CS2')"
    )
    
    # Ranking data
    score = models.IntegerField(
        default=0,
        help_text="Total ranking score for this game"
    )
    
    tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default='UNRANKED'
    )
    
    rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Global rank for this game (1 = best)"
    )
    
    percentile = models.FloatField(
        default=0.0,
        help_text="Percentile ranking (0.0 to 100.0)"
    )
    
    # Match statistics
    verified_match_count = models.IntegerField(
        default=0,
        help_text="Number of verified matches contributing to this rank"
    )
    
    confidence_level = models.CharField(
        max_length=15,
        choices=CONFIDENCE_CHOICES,
        default='PROVISIONAL'
    )
    
    # Score breakdown (JSON)
    breakdown = models.JSONField(
        default=dict,
        help_text=(
            "Score breakdown by source. "
            "Example: {tournament_wins: 1500, verified_matches: 450, "
            "challenges: 200, decay_penalty: -50}"
        )
    )
    
    # Metadata
    last_match_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When team last played this game"
    )
    
    snapshot_date = models.DateTimeField(
        auto_now=True,
        help_text="When this snapshot was last updated"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'competition_team_game_ranking_snapshot'
        verbose_name = 'Team Game Ranking Snapshot'
        verbose_name_plural = 'Team Game Ranking Snapshots'
        unique_together = [('team', 'game_id')]
        ordering = ['-score']
        indexes = [
            models.Index(fields=['game_id', '-score']),
            models.Index(fields=['tier', '-score']),
            models.Index(fields=['confidence_level']),
        ]
    
    def __str__(self):
        return f"{self.team.name} - {self.game_id} - {self.tier} ({self.score})"
