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
    
    Enhanced in Epic 8.5 with generic reference_id, payload_json, and computed_at tracking.
    """
    
    LEADERBOARD_TYPES = [
        ("tournament", "Tournament"),
        ("seasonal", "Seasonal"),
        ("all_time", "All-Time"),
        ("team", "Team"),
        ("game_specific", "Game-Specific"),
        ("mmr", "MMR Ranking"),          # Epic 8.5: MMR-based leaderboard
        ("elo", "ELO Ranking"),          # Epic 8.5: ELO-based leaderboard
        ("tier", "Tier Ranking"),        # Epic 8.5: Tier-based leaderboard
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
    
    # Entity (who is ranked?) - Legacy approach
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
    
    # Epic 8.5: Generic reference for flexible entity types
    reference_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Generic entity ID (user ID or team ID) - preferred over FK for performance"
    )
    
    # Ranking
    rank = models.IntegerField(db_index=True)
    points = models.IntegerField(default=0)  # Could be ELO, MMR, or custom score
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # Epic 8.5: Flexible payload for additional leaderboard-specific data
    payload_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Flexible payload: {'tier': str, 'percentile': float, 'streak': int, 'kda': float, ...}"
    )
    
    # Metadata
    last_updated = models.DateTimeField(auto_now=True)
    computed_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="When leaderboard entry was last computed (Epic 8.5)"
    )
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
            models.Index(fields=["reference_id", "leaderboard_type"]),  # Epic 8.5
            models.Index(fields=["game", "leaderboard_type", "-points"]),  # Epic 8.5: game leaderboards
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
        entity = self.player or self.team or f"Ref#{self.reference_id}"
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


class UserStats(models.Model):
    """
    Per-user statistics aggregated across all matches.
    
    Tracks competitive performance metrics for individual players.
    Updated automatically via MatchCompletedEvent handlers (Epic 8.2).
    
    Stats are maintained per-game to support multi-game tournaments.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_stats"
    )
    game_slug = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Game identifier (e.g., 'valorant', 'csgo')"
    )
    
    # Match participation
    matches_played = models.IntegerField(default=0)
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    matches_drawn = models.IntegerField(default=0)  # For games supporting draws
    
    # Tournament participation
    tournaments_played = models.IntegerField(default=0)
    tournaments_won = models.IntegerField(default=0)
    
    # Performance metrics
    win_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Win percentage (0-100)"
    )
    
    # Game-specific stats (optional, depends on game type)
    total_kills = models.IntegerField(default=0, help_text="Total eliminations across all matches")
    total_deaths = models.IntegerField(default=0, help_text="Total deaths across all matches")
    kd_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.0,
        help_text="Kill/Death ratio"
    )
    
    # Timestamps
    last_match_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "leaderboards_userstats"
        verbose_name = "User Stats"
        verbose_name_plural = "User Stats"
        indexes = [
            models.Index(fields=["user", "game_slug"]),
            models.Index(fields=["game_slug", "matches_played"]),
            models.Index(fields=["game_slug", "win_rate"]),
            models.Index(fields=["game_slug", "kd_ratio"]),
            models.Index(fields=["last_match_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "game_slug"],
                name="unique_user_game_stats"
            ),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.game_slug}: {self.matches_won}/{self.matches_played} wins"
    
    def calculate_win_rate(self):
        """Calculate and update win rate percentage."""
        if self.matches_played > 0:
            self.win_rate = (self.matches_won / self.matches_played) * 100
        else:
            self.win_rate = 0.0
    
    def calculate_kd_ratio(self):
        """Calculate and update K/D ratio."""
        if self.total_deaths > 0:
            self.kd_ratio = self.total_kills / self.total_deaths
        else:
            self.kd_ratio = self.total_kills  # Infinite K/D when no deaths


class TeamStats(models.Model):
    """
    Per-team statistics aggregated across all matches.
    
    Tracks competitive performance metrics for teams.
    Updated automatically via MatchCompletedEvent handlers (Epic 8.3).
    
    Stats are maintained per-game to support multi-game tournaments.
    Reference: Phase 8, Epic 8.3 - Team Stats & Ranking System
    """
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name="team_stats"
    )
    game_slug = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Game identifier (e.g., 'valorant', 'csgo')"
    )
    
    # Match participation
    matches_played = models.IntegerField(default=0)
    matches_won = models.IntegerField(default=0)
    matches_lost = models.IntegerField(default=0)
    matches_drawn = models.IntegerField(default=0)  # For games supporting draws
    
    # Tournament participation
    tournaments_played = models.IntegerField(default=0)
    tournaments_won = models.IntegerField(default=0)
    
    # Performance metrics
    win_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Win percentage (0-100)"
    )
    
    # Timestamps
    last_match_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "leaderboards_teamstats"
        verbose_name = "Team Stats"
        verbose_name_plural = "Team Stats"
        indexes = [
            models.Index(fields=["team", "game_slug"]),
            models.Index(fields=["game_slug", "matches_played"]),
            models.Index(fields=["game_slug", "win_rate"]),
            models.Index(fields=["last_match_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "game_slug"],
                name="unique_team_game_stats"
            ),
        ]
    
    def __str__(self):
        return f"{self.team.name} - {self.game_slug}: {self.matches_won}/{self.matches_played} wins"
    
    def calculate_win_rate(self):
        """Calculate and update win rate percentage."""
        if self.matches_played > 0:
            self.win_rate = (self.matches_won / self.matches_played) * 100
        else:
            self.win_rate = 0.0


class TeamRanking(models.Model):
    """
    Team ELO ratings and rankings per game.
    
    Implements competitive ranking system using ELO algorithm (K-factor = 32).
    Updated automatically when team matches complete (Epic 8.3).
    
    Supports per-game rankings and historical peak tracking.
    Reference: Phase 8, Epic 8.3 - Team Stats & Ranking System
    """
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name="team_rankings"
    )
    game_slug = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Game identifier for this ranking ladder"
    )
    
    # ELO rating system
    elo_rating = models.IntegerField(
        default=1200,
        help_text="Current ELO rating (default 1200 for new teams)"
    )
    peak_elo = models.IntegerField(
        default=1200,
        help_text="Highest ELO rating achieved"
    )
    
    # Match record (denormalized for faster ranking queries)
    games_played = models.IntegerField(default=0)
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    draws = models.IntegerField(default=0)
    
    # Ranking position (computed or cached)
    rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Current rank position (1 = top team), computed via queries"
    )
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "leaderboards_teamranking"
        verbose_name = "Team Ranking"
        verbose_name_plural = "Team Rankings"
        ordering = ["-elo_rating"]  # Default ordering: highest ELO first
        indexes = [
            models.Index(fields=["team", "game_slug"]),
            models.Index(fields=["game_slug", "-elo_rating"]),  # Leaderboard queries
            models.Index(fields=["game_slug", "rank"]),  # Rank-based queries
            models.Index(fields=["last_updated"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "game_slug"],
                name="unique_team_game_ranking"
            ),
        ]
    
    def __str__(self):
        return f"{self.team.name} - {self.game_slug}: ELO {self.elo_rating}"
    
    def update_peak_elo(self):
        """Update peak ELO if current rating exceeds previous peak."""
        if self.elo_rating > self.peak_elo:
            self.peak_elo = self.elo_rating


# =============================================================================
# Phase 8, Epic 8.4: Match History Engine
# =============================================================================

class UserMatchHistory(models.Model):
    """
    Complete match history entry for a user.
    
    Stores finalized match results for user profile history, timeline, and search.
    Created by event handlers on MatchCompletedEvent/MatchResultFinalizedEvent.
    
    Reference: Phase 8, Epic 8.4 - Match History Engine
    """
    
    # Match reference
    match = models.ForeignKey(
        "tournaments.Match",
        on_delete=models.CASCADE,
        related_name="user_history_entries",
        db_index=True,
    )
    
    # User reference (participant in match)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="match_history",
        db_index=True,
    )
    
    # Context
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="user_match_history",
        db_index=True,
    )
    game_slug = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Game identifier (valorant, csgo, etc.)"
    )
    
    # Result (denormalized for fast queries)
    is_winner = models.BooleanField(default=False)
    is_draw = models.BooleanField(default=False)
    opponent_user_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Opponent user ID (for 1v1 matches)"
    )
    opponent_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Opponent display name (cached for performance)"
    )
    
    # Score summary (denormalized for timeline display)
    score_summary = models.CharField(
        max_length=100,
        blank=True,
        help_text="Score summary (e.g., '13-7', '2-1', etc.)"
    )
    
    # Match stats (denormalized, optional)
    kills = models.IntegerField(default=0, help_text="Kills in match")
    deaths = models.IntegerField(default=0, help_text="Deaths in match")
    assists = models.IntegerField(default=0, help_text="Assists in match")
    
    # Flags
    had_dispute = models.BooleanField(
        default=False,
        help_text="Whether match had dispute(s)"
    )
    is_forfeit = models.BooleanField(
        default=False,
        help_text="Whether match ended in forfeit"
    )
    
    # Timestamps
    completed_at = models.DateTimeField(
        db_index=True,
        help_text="When match was completed/finalized"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "leaderboards_usermatchhistory"
        verbose_name = "User Match History"
        verbose_name_plural = "User Match Histories"
        ordering = ["-completed_at"]  # Most recent first
        indexes = [
            models.Index(fields=["user", "-completed_at"]),  # User timeline
            models.Index(fields=["tournament", "-completed_at"]),  # Tournament history
            models.Index(fields=["game_slug", "-completed_at"]),  # Game history
            models.Index(fields=["user", "game_slug", "-completed_at"]),  # Filtered user history
        ]
    
    def __str__(self):
        result = "Win" if self.is_winner else ("Draw" if self.is_draw else "Loss")
        return f"{self.user.username} - {self.game_slug} - {result} ({self.completed_at.date()})"


class TeamMatchHistory(models.Model):
    """
    Complete match history entry for a team.
    
    Stores finalized match results for team profile history, timeline, and search.
    Created by event handlers on team match completion.
    
    Reference: Phase 8, Epic 8.4 - Match History Engine
    """
    
    # Match reference
    match = models.ForeignKey(
        "tournaments.Match",
        on_delete=models.CASCADE,
        related_name="team_history_entries",
        db_index=True,
    )
    
    # Team reference (participant in match)
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="match_history",
        db_index=True,
    )
    
    # Context
    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="team_match_history",
        db_index=True,
    )
    game_slug = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Game identifier"
    )
    
    # Result (denormalized for fast queries)
    is_winner = models.BooleanField(default=False)
    is_draw = models.BooleanField(default=False)
    opponent_team_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Opponent team ID"
    )
    opponent_team_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Opponent team name (cached)"
    )
    
    # Score summary
    score_summary = models.CharField(
        max_length=100,
        blank=True,
        help_text="Score summary for timeline display"
    )
    
    # ELO tracking (snapshot at match time)
    elo_before = models.IntegerField(
        null=True,
        blank=True,
        help_text="Team ELO before match"
    )
    elo_after = models.IntegerField(
        null=True,
        blank=True,
        help_text="Team ELO after match"
    )
    elo_change = models.IntegerField(
        default=0,
        help_text="ELO rating change from match"
    )
    
    # Flags
    had_dispute = models.BooleanField(default=False)
    is_forfeit = models.BooleanField(default=False)
    
    # Timestamps
    completed_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "leaderboards_teammatchhistory"
        verbose_name = "Team Match History"
        verbose_name_plural = "Team Match Histories"
        ordering = ["-completed_at"]
        indexes = [
            models.Index(fields=["team", "-completed_at"]),  # Team timeline
            models.Index(fields=["tournament", "-completed_at"]),  # Tournament history
            models.Index(fields=["game_slug", "-completed_at"]),  # Game history
            models.Index(fields=["team", "game_slug", "-completed_at"]),  # Filtered team history
        ]
    
    def __str__(self):
        result = "Win" if self.is_winner else ("Draw" if self.is_draw else "Loss")
        elo_info = f" ({self.elo_change:+d} ELO)" if self.elo_change else ""
        return f"{self.team.name} - {self.game_slug} - {result}{elo_info} ({self.completed_at.date()})"


# =============================================================================
# Phase 8, Epic 8.5: Advanced Analytics, Ranking Tiers & Real-Time Leaderboards
# =============================================================================

class Season(models.Model):
    """
    Competitive season with time boundaries and decay rules.
    
    Defines time-bounded competitive periods for seasonal leaderboards.
    Supports ELO decay rules and seasonal rollover logic.
    
    Reference: Phase 8, Epic 8.5 - Advanced Analytics & Ranking Tiers
    """
    
    season_id = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text="Unique season identifier (e.g., 'S1-2024', 'WINTER-2024')"
    )
    name = models.CharField(
        max_length=100,
        help_text="Display name (e.g., 'Season 1 - 2024', 'Winter Championship 2024')"
    )
    
    # Time boundaries
    start_date = models.DateTimeField(db_index=True)
    end_date = models.DateTimeField(db_index=True)
    
    # Status
    is_active = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether season is currently active (only one active season per time)"
    )
    
    # Decay rules (JSON for flexibility)
    decay_rules_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Decay rules: {'enabled': bool, 'days_inactive': int, 'decay_percentage': float, 'min_elo': int}"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "leaderboards_season"
        verbose_name = "Season"
        verbose_name_plural = "Seasons"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["is_active", "start_date"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
    
    def __str__(self):
        status = " (Active)" if self.is_active else ""
        return f"{self.name}{status}"
    
    def is_current(self):
        """Check if season is currently active (based on time)."""
        from django.utils import timezone
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class UserAnalyticsSnapshot(models.Model):
    """
    Rich analytics snapshot for user performance tracking.
    
    Stores pre-computed analytics with tier assignment, percentile ranking,
    rolling averages, and streak detection. Updated by nightly Celery job.
    
    Supports multi-dimensional ranking:
    - Tier system (Bronze → Silver → Gold → Diamond → Crown)
    - Percentile ranking (top 1%, top 5%, etc.)
    - Rolling performance windows (7d, 30d)
    - Streak detection (current win/loss streak)
    
    Reference: Phase 8, Epic 8.5 - Advanced Analytics & Ranking Tiers
    """
    
    # Tier choices (ranked from lowest to highest)
    TIER_BRONZE = "bronze"
    TIER_SILVER = "silver"
    TIER_GOLD = "gold"
    TIER_DIAMOND = "diamond"
    TIER_CROWN = "crown"
    
    TIER_CHOICES = [
        (TIER_BRONZE, "Bronze"),      # 0-1199 ELO
        (TIER_SILVER, "Silver"),      # 1200-1599 ELO
        (TIER_GOLD, "Gold"),          # 1600-1999 ELO
        (TIER_DIAMOND, "Diamond"),    # 2000-2399 ELO
        (TIER_CROWN, "Crown"),        # 2400+ ELO
    ]
    
    # User reference
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="analytics_snapshots",
        db_index=True,
    )
    game_slug = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Game identifier"
    )
    
    # Skill rating snapshot
    mmr_snapshot = models.IntegerField(
        default=1200,
        help_text="MMR snapshot at calculation time (for MMR-based games)"
    )
    elo_snapshot = models.IntegerField(
        default=1200,
        help_text="ELO snapshot at calculation time (fallback/alternative)"
    )
    
    # Performance metrics
    win_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Overall win rate percentage (0-100)"
    )
    kda_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.0,
        help_text="(Kills + Assists) / Deaths ratio"
    )
    
    # Rolling averages
    matches_last_7d = models.IntegerField(
        default=0,
        help_text="Matches played in last 7 days"
    )
    matches_last_30d = models.IntegerField(
        default=0,
        help_text="Matches played in last 30 days"
    )
    win_rate_7d = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Win rate in last 7 days"
    )
    win_rate_30d = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Win rate in last 30 days"
    )
    
    # Streak detection
    current_streak = models.IntegerField(
        default=0,
        help_text="Current win/loss streak (positive = wins, negative = losses)"
    )
    longest_win_streak = models.IntegerField(
        default=0,
        help_text="Longest consecutive win streak"
    )
    
    # Tier assignment
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default=TIER_BRONZE,
        db_index=True,
        help_text="Assigned tier based on ELO/MMR"
    )
    
    # Percentile ranking
    percentile_rank = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.0,
        help_text="Percentile rank (0-100, higher = better)"
    )
    
    # Timestamps
    recalculated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="When analytics were last computed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "leaderboards_useranalyticssnapshot"
        verbose_name = "User Analytics Snapshot"
        verbose_name_plural = "User Analytics Snapshots"
        ordering = ["-elo_snapshot"]
        indexes = [
            models.Index(fields=["user", "game_slug"]),
            models.Index(fields=["game_slug", "-elo_snapshot"]),  # Leaderboard queries
            models.Index(fields=["game_slug", "tier", "-elo_snapshot"]),  # Tier leaderboards
            models.Index(fields=["game_slug", "-percentile_rank"]),  # Percentile queries
            models.Index(fields=["recalculated_at"]),  # Freshness checks
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "game_slug"],
                name="unique_user_game_analytics"
            ),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.game_slug}: {self.get_tier_display()} ({self.elo_snapshot} ELO)"
    
    @staticmethod
    def calculate_tier(elo_or_mmr: int) -> str:
        """Calculate tier based on ELO/MMR rating."""
        if elo_or_mmr >= 2400:
            return UserAnalyticsSnapshot.TIER_CROWN
        elif elo_or_mmr >= 2000:
            return UserAnalyticsSnapshot.TIER_DIAMOND
        elif elo_or_mmr >= 1600:
            return UserAnalyticsSnapshot.TIER_GOLD
        elif elo_or_mmr >= 1200:
            return UserAnalyticsSnapshot.TIER_SILVER
        else:
            return UserAnalyticsSnapshot.TIER_BRONZE


class TeamAnalyticsSnapshot(models.Model):
    """
    Rich analytics snapshot for team performance tracking.
    
    Stores pre-computed team analytics with tier assignment, percentile ranking,
    synergy score, and activity metrics. Updated by nightly Celery job.
    
    Supports team-specific metrics:
    - ELO snapshot with volatility tracking
    - Average member skill (computed from member analytics)
    - Team synergy score (consistency across matches)
    - Activity score (recent match participation)
    - Tier assignment and percentile ranking
    
    Reference: Phase 8, Epic 8.5 - Advanced Analytics & Ranking Tiers
    """
    
    # Tier choices (same as user tiers)
    TIER_BRONZE = "bronze"
    TIER_SILVER = "silver"
    TIER_GOLD = "gold"
    TIER_DIAMOND = "diamond"
    TIER_CROWN = "crown"
    
    TIER_CHOICES = [
        (TIER_BRONZE, "Bronze"),
        (TIER_SILVER, "Silver"),
        (TIER_GOLD, "Gold"),
        (TIER_DIAMOND, "Diamond"),
        (TIER_CROWN, "Crown"),
    ]
    
    # Team reference
    team = models.ForeignKey(
        "teams.Team",
        on_delete=models.CASCADE,
        related_name="analytics_snapshots",
        db_index=True,
    )
    game_slug = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Game identifier"
    )
    
    # Team ELO snapshot
    elo_snapshot = models.IntegerField(
        default=1200,
        help_text="Team ELO rating snapshot"
    )
    elo_volatility = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0.0,
        help_text="ELO volatility (standard deviation of recent changes)"
    )
    
    # Skill metrics
    avg_member_skill = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=1200.0,
        help_text="Average skill rating of active team members"
    )
    
    # Performance metrics
    win_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Overall win rate percentage"
    )
    win_rate_7d = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Win rate in last 7 days"
    )
    win_rate_30d = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Win rate in last 30 days"
    )
    
    # Team synergy & activity
    synergy_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Team synergy score (0-100, based on consistency)"
    )
    activity_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.0,
        help_text="Activity score (0-100, based on recent match participation)"
    )
    
    # Match volume
    matches_last_7d = models.IntegerField(default=0)
    matches_last_30d = models.IntegerField(default=0)
    
    # Tier assignment
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default=TIER_BRONZE,
        db_index=True,
        help_text="Assigned tier based on team ELO"
    )
    
    # Percentile ranking
    percentile_rank = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.0,
        help_text="Percentile rank among all teams (0-100)"
    )
    
    # Timestamps
    recalculated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="When analytics were last computed"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "leaderboards_teamanalyticssnapshot"
        verbose_name = "Team Analytics Snapshot"
        verbose_name_plural = "Team Analytics Snapshots"
        ordering = ["-elo_snapshot"]
        indexes = [
            models.Index(fields=["team", "game_slug"]),
            models.Index(fields=["game_slug", "-elo_snapshot"]),  # Team leaderboards
            models.Index(fields=["game_slug", "tier", "-elo_snapshot"]),  # Tier leaderboards
            models.Index(fields=["game_slug", "-percentile_rank"]),  # Percentile queries
            models.Index(fields=["recalculated_at"]),  # Freshness checks
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["team", "game_slug"],
                name="unique_team_game_analytics"
            ),
        ]
    
    def __str__(self):
        return f"{self.team.name} - {self.game_slug}: {self.get_tier_display()} ({self.elo_snapshot} ELO)"
    
    @staticmethod
    def calculate_tier(elo: int) -> str:
        """Calculate tier based on team ELO rating."""
        if elo >= 2400:
            return TeamAnalyticsSnapshot.TIER_CROWN
        elif elo >= 2000:
            return TeamAnalyticsSnapshot.TIER_DIAMOND
        elif elo >= 1600:
            return TeamAnalyticsSnapshot.TIER_GOLD
        elif elo >= 1200:
            return TeamAnalyticsSnapshot.TIER_SILVER
        else:
            return TeamAnalyticsSnapshot.TIER_BRONZE
