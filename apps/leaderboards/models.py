"""
Leaderboard Models.

Database tables for storing pre-computed leaderboard entries and historical snapshots.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class LeaderboardEntry(models.Model):
    """
    Pre-computed leaderboard entry for fast reads.
    
    Stores current rank, points, and stats for a player or team in a specific leaderboard.
    Updated by Celery tasks (hourly for seasonal, daily for all-time, real-time for tournaments).
    """
    
    LEADERBOARD_TYPES = [
        ("tournament", "Tournament"),
        ("seasonal", "Seasonal"),
        ("all_time", "All-Time"),
        ("team", "Team"),
        ("game_specific", "Game-Specific"),
    ]
    
    leaderboard_type = models.CharField(max_length=50, choices=LEADERBOARD_TYPES, db_index=True)
    
    # Scope (what leaderboard is this for?)
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries"
    )
    game = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    season = models.CharField(max_length=50, null=True, blank=True, db_index=True)
    
    # Entity (who is ranked?)
    player = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries"
    )
    team = models.ForeignKey(
        "teams.Team",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="leaderboard_entries"
    )
    
    # Ranking
    rank = models.IntegerField(db_index=True)
    points = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        db_table = "leaderboards_leaderboardentry"
        indexes = [
            models.Index(fields=["leaderboard_type", "rank"]),
            models.Index(fields=["leaderboard_type", "tournament", "rank"]),
            models.Index(fields=["leaderboard_type", "game", "season", "rank"]),
            models.Index(fields=["player", "leaderboard_type"]),
            models.Index(fields=["team", "leaderboard_type"]),
            models.Index(fields=["is_active", "leaderboard_type", "rank"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["leaderboard_type", "tournament", "player"],
                name="unique_tournament_player",
                condition=models.Q(player__isnull=False, tournament__isnull=False)
            ),
            models.UniqueConstraint(
                fields=["leaderboard_type", "tournament", "team"],
                name="unique_tournament_team",
                condition=models.Q(team__isnull=False, tournament__isnull=False)
            ),
        ]
    
    def __str__(self):
        entity = self.player or self.team
        return f"{self.leaderboard_type} - Rank {self.rank}: {entity}"


class LeaderboardSnapshot(models.Model):
    """
    Daily snapshot of leaderboard entry for historical tracking.
    
    Used to generate rank history charts (trend over time).
    Created by daily Celery task at 00:00 UTC.
    """
    
    date = models.DateField(db_index=True)
    leaderboard_type = models.CharField(max_length=50, db_index=True)
    
    player = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="leaderboard_snapshots"
    )
    team = models.ForeignKey(
        "teams.Team",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="leaderboard_snapshots"
    )
    
    rank = models.IntegerField()
    points = models.IntegerField()
    
    class Meta:
        db_table = "leaderboards_leaderboardsnapshot"
        indexes = [
            models.Index(fields=["player", "date"]),
            models.Index(fields=["team", "date"]),
            models.Index(fields=["date", "leaderboard_type"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["date", "leaderboard_type", "player"],
                name="unique_snapshot_player",
                condition=models.Q(player__isnull=False)
            ),
            models.UniqueConstraint(
                fields=["date", "leaderboard_type", "team"],
                name="unique_snapshot_team",
                condition=models.Q(team__isnull=False)
            ),
        ]
    
    def __str__(self):
        entity = self.player or self.team
        return f"{self.date} - {self.leaderboard_type} - Rank {self.rank}: {entity}"
