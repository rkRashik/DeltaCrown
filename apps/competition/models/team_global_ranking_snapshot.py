"""TeamGlobalRankingSnapshot model - cross-game global rankings."""
from django.db import models


class TeamGlobalRankingSnapshot(models.Model):
    """
    Cross-game global ranking snapshot (Phase 3A-B).
    
    Aggregates ranking scores across all games a team plays. Used for
    global leaderboards and "best overall esports organization" rankings.
    
    This is the SOURCE OF TRUTH for global rankings displayed in
    team detail pages (stats.global_score, stats.global_tier).
    """
    
    TIER_CHOICES = [
        ('DIAMOND', 'Diamond'),
        ('PLATINUM', 'Platinum'),
        ('GOLD', 'Gold'),
        ('SILVER', 'Silver'),
        ('BRONZE', 'Bronze'),
        ('UNRANKED', 'Unranked'),
    ]
    
    # One-to-one with Team
    team = models.OneToOneField(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='global_ranking_snapshot',
        primary_key=True
    )
    
    # Global ranking data
    global_score = models.IntegerField(
        default=0,
        help_text="Aggregate score across all games"
    )
    
    global_tier = models.CharField(
        max_length=10,
        choices=TIER_CHOICES,
        default='UNRANKED'
    )
    
    global_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Global rank across all teams (1 = best)"
    )
    
    # Breadth metrics
    games_played = models.IntegerField(
        default=0,
        help_text="Number of games this team has ranked in"
    )
    
    # Game contributions (JSON)
    game_contributions = models.JSONField(
        default=dict,
        help_text=(
            "Per-game score breakdown. "
            "Example: {LOL: 2500, VAL: 1800, CS2: 1200}"
        )
    )
    
    # Metadata
    snapshot_date = models.DateTimeField(
        auto_now=True,
        help_text="When this snapshot was last updated"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'competition_team_global_ranking_snapshot'
        verbose_name = 'Team Global Ranking Snapshot'
        verbose_name_plural = 'Team Global Ranking Snapshots'
        ordering = ['-global_score']
        indexes = [
            models.Index(fields=['-global_score']),
            models.Index(fields=['global_tier', '-global_score']),
            models.Index(fields=['games_played']),
        ]
    
    def __str__(self):
        return f"{self.team.name} - Global - {self.global_tier} ({self.global_score})"
