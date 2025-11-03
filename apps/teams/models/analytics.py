"""
Analytics Models for Team Performance Tracking

This module provides comprehensive analytics tracking for teams including:
- Overall team statistics
- Player-specific performance metrics
- Match history and records
- Game-specific analytics
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal


class TeamAnalytics(models.Model):
    """
    Comprehensive team statistics aggregated across all competitions.
    Tracks wins, losses, points, and game-specific metrics.
    
    Note: This is the new advanced analytics model. 
    The legacy TeamStats model in stats.py is kept for backward compatibility.
    """
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='statistics'
    )
    
    game = models.CharField(
        max_length=50,
        help_text="Game for which these stats apply"
    )
    
    # Overall Match Statistics
    total_matches = models.PositiveIntegerField(
        default=0,
        help_text="Total matches played"
    )
    
    matches_won = models.PositiveIntegerField(
        default=0,
        help_text="Total matches won"
    )
    
    matches_lost = models.PositiveIntegerField(
        default=0,
        help_text="Total matches lost"
    )
    
    matches_drawn = models.PositiveIntegerField(
        default=0,
        help_text="Total matches drawn"
    )
    
    win_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Win percentage (0-100)"
    )
    
    # Points Tracking
    total_points = models.PositiveIntegerField(
        default=0,
        help_text="Total points earned"
    )
    
    points_history = models.JSONField(
        default=list,
        help_text="Historical points data: [{date, points, change, reason}]"
    )
    
    # Tournament Statistics
    tournaments_participated = models.PositiveIntegerField(
        default=0,
        help_text="Total tournaments entered"
    )
    
    tournaments_won = models.PositiveIntegerField(
        default=0,
        help_text="Total tournaments won"
    )
    
    # Game-Specific Statistics
    game_specific_stats = models.JSONField(
        default=dict,
        help_text="Game-specific statistics (maps, heroes, etc.)"
    )
    
    # Performance Trends
    current_streak = models.IntegerField(
        default=0,
        help_text="Current win/loss streak (positive = wins, negative = losses)"
    )
    
    best_win_streak = models.PositiveIntegerField(
        default=0,
        help_text="Best winning streak achieved"
    )
    
    # Timestamps
    last_match_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of last match played"
    )
    
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teams_analytics_team_stats'  # Different table name to avoid conflict
        verbose_name = 'Team Analytics'
        verbose_name_plural = 'Team Analytics'
        unique_together = ['team', 'game']
        indexes = [
            models.Index(fields=['team', 'game']),
            models.Index(fields=['win_rate']),
            models.Index(fields=['-total_points']),
        ]
    
    def __str__(self):
        return f"{self.team.name} - {self.game} Stats"
    
    def update_win_rate(self):
        """Calculate and update win rate based on match results"""
        if self.total_matches > 0:
            self.win_rate = Decimal((self.matches_won / self.total_matches) * 100)
        else:
            self.win_rate = Decimal('0.00')
        self.save(update_fields=['win_rate'])
    
    def add_match_result(self, result: str, points_change: int = 0):
        """
        Add a match result and update statistics.
        
        Args:
            result: 'win', 'loss', or 'draw'
            points_change: Points gained or lost
        """
        self.total_matches += 1
        
        if result == 'win':
            self.matches_won += 1
            if self.current_streak >= 0:
                self.current_streak += 1
            else:
                self.current_streak = 1
            self.best_win_streak = max(self.best_win_streak, self.current_streak)
        elif result == 'loss':
            self.matches_lost += 1
            if self.current_streak <= 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1
        elif result == 'draw':
            self.matches_drawn += 1
            self.current_streak = 0
        
        self.total_points += points_change
        self.last_match_date = timezone.now()
        
        # Record in points history
        self.points_history.append({
            'date': timezone.now().isoformat(),
            'points': self.total_points,
            'change': points_change,
            'reason': f'Match {result}'
        })
        
        self.update_win_rate()


class PlayerStats(models.Model):
    """
    Individual player performance statistics within a team.
    Tracks participation, contribution, and game-specific metrics.
    """
    
    player = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='player_statistics'
    )
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='player_stats'
    )
    
    game = models.CharField(
        max_length=50,
        help_text="Game for which these stats apply"
    )
    
    # Participation Metrics
    tournaments_played = models.PositiveIntegerField(
        default=0,
        help_text="Total tournaments participated in"
    )
    
    matches_played = models.PositiveIntegerField(
        default=0,
        help_text="Total matches played"
    )
    
    matches_won = models.PositiveIntegerField(
        default=0,
        help_text="Matches won"
    )
    
    attendance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('100.00'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Attendance percentage (0-100)"
    )
    
    # Performance Metrics
    mvp_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times awarded MVP"
    )
    
    contribution_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Overall contribution score"
    )
    
    individual_rating = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('1000.00'),
        help_text="Individual skill rating"
    )
    
    # Game-Specific Statistics
    game_specific_stats = models.JSONField(
        default=dict,
        help_text="Game-specific performance metrics (KDA, accuracy, etc.)"
    )
    
    # Activity Tracking
    last_active = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time player was active in a match"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether player is currently active in the team"
    )
    
    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teams_analytics_player_stats'
        verbose_name = 'Player Analytics'
        verbose_name_plural = 'Player Analytics'
        unique_together = ['player', 'team', 'game']
        indexes = [
            models.Index(fields=['team', 'game']),
            models.Index(fields=['player', 'game']),
            models.Index(fields=['-contribution_score']),
            models.Index(fields=['-mvp_count']),
        ]
    
    def __str__(self):
        return f"{self.player.user.username} - {self.team.name} ({self.game})"
    
    def update_attendance_rate(self, total_team_matches: int):
        """Calculate attendance rate based on matches played vs total team matches"""
        if total_team_matches > 0:
            self.attendance_rate = Decimal((self.matches_played / total_team_matches) * 100)
        else:
            self.attendance_rate = Decimal('100.00')
        self.save(update_fields=['attendance_rate'])


class MatchRecord(models.Model):
    """
    Individual match history record.
    Stores complete match information including participants and results.
    """
    
    RESULT_CHOICES = [
        ('win', 'Win'),
        ('loss', 'Loss'),
        ('draw', 'Draw'),
    ]
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='match_records'
    )
    
    # NOTE: Changed to IntegerField - tournament app moved to legacy (Nov 2, 2025)
    tournament_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Legacy tournament ID - Tournament this match was part of (if any)"
    )
    
    opponent_name = models.CharField(
        max_length=200,
        help_text="Name of the opponent team"
    )
    
    opponent_team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches_against',
        help_text="Opponent team (if in our system)"
    )
    
    # Match Details
    match_date = models.DateTimeField(
        help_text="When the match was played"
    )
    
    game = models.CharField(
        max_length=50,
        help_text="Game played"
    )
    
    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES,
        help_text="Match outcome"
    )
    
    score = models.CharField(
        max_length=50,
        help_text="Match score (e.g., '13-7', '2-1', '3-0')"
    )
    
    team_score = models.PositiveIntegerField(
        default=0,
        help_text="Our team's score"
    )
    
    opponent_score = models.PositiveIntegerField(
        default=0,
        help_text="Opponent's score"
    )
    
    # Match Metadata
    map_played = models.CharField(
        max_length=100,
        blank=True,
        help_text="Map or arena where match was played"
    )
    
    duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Match duration in minutes"
    )
    
    # Points Impact
    points_earned = models.IntegerField(
        default=0,
        help_text="Points earned/lost from this match"
    )
    
    # Game-Specific Data
    game_specific_data = models.JSONField(
        default=dict,
        help_text="Additional game-specific match data"
    )
    
    # Participating Players
    participants = models.ManyToManyField(
        'user_profile.UserProfile',
        through='MatchParticipation',
        related_name='match_participations'
    )
    
    # Match Notes
    notes = models.TextField(
        blank=True,
        help_text="Match notes or highlights"
    )
    
    # VOD/Replay
    replay_url = models.URLField(
        blank=True,
        help_text="URL to match replay or VOD"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teams_analytics_match_record'
        verbose_name = 'Match Record'
        verbose_name_plural = 'Match Records'
        ordering = ['-match_date']
        indexes = [
            models.Index(fields=['team', '-match_date']),
            models.Index(fields=['tournament_id', '-match_date']),
            models.Index(fields=['game', '-match_date']),
            models.Index(fields=['result']),
        ]
    
    def __str__(self):
        return f"{self.team.name} vs {self.opponent_name} - {self.result.upper()}"


class MatchParticipation(models.Model):
    """
    Through model for tracking individual player participation in matches.
    Stores player-specific performance data for each match.
    """
    
    match = models.ForeignKey(
        MatchRecord,
        on_delete=models.CASCADE,
        related_name='player_participations'
    )
    
    player = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='match_participation_records'
    )
    
    # Participation Details
    role_played = models.CharField(
        max_length=50,
        help_text="Role/position played in this match"
    )
    
    was_starter = models.BooleanField(
        default=True,
        help_text="Whether player started or was substitute"
    )
    
    was_mvp = models.BooleanField(
        default=False,
        help_text="Whether player was awarded MVP for this match"
    )
    
    # Performance Metrics (game-agnostic)
    performance_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Individual performance score for this match"
    )
    
    # Game-Specific Performance
    game_specific_performance = models.JSONField(
        default=dict,
        help_text="Game-specific performance metrics (kills, deaths, assists, etc.)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teams_analytics_match_participation'
        verbose_name = 'Match Participation'
        verbose_name_plural = 'Match Participations'
        unique_together = ['match', 'player']
        indexes = [
            models.Index(fields=['match', 'player']),
        ]
    
    def __str__(self):
        return f"{self.player.user.username} in {self.match}"
