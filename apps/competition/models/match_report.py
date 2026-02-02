"""MatchReport model - self-reported match results."""
from django.conf import settings
from django.db import models


class MatchReport(models.Model):
    """
    Self-reported match results (Phase 3A-B).
    
    Teams submit match reports with evidence URLs (screenshots, VODs, etc.).
    Each report enters verification workflow via MatchVerification.
    """
    
    MATCH_TYPE_CHOICES = [
        ('CASUAL', 'Casual Match'),
        ('RANKED', 'Ranked Match'),
        ('CHALLENGE', 'Challenge Match'),
        ('SCRIM', 'Scrim / Practice'),
        ('TOURNAMENT', 'Tournament Match'),
    ]
    
    RESULT_CHOICES = [
        ('WIN', 'Win'),
        ('LOSS', 'Loss'),
        ('DRAW', 'Draw'),
    ]
    
    # Match identification
    game_id = models.CharField(
        max_length=10,
        db_index=True,
        help_text="Game this match was played in (e.g., 'LOL', 'VAL')"
    )
    
    match_type = models.CharField(
        max_length=20,
        choices=MATCH_TYPE_CHOICES,
        default='CASUAL'
    )
    
    # Teams involved (FK to organizations.Team)
    # Note: db_column preserves existing DB column names (team1_id, team2_id)
    # while allowing proper Django FK naming (.team1, .team2 in Python)
    team1 = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='match_reports_as_team1',
        help_text="Reporting team (always the submitter)",
        db_column='team1_id'
    )
    
    team2 = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='match_reports_as_team2',
        help_text="Opponent team",
        null=True,
        blank=True,
        db_column='team2_id'
    )
    
    # Match result (from team1's perspective)
    result = models.CharField(
        max_length=10,
        choices=RESULT_CHOICES
    )
    
    # Evidence
    evidence_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Screenshot, VOD, or match history link"
    )
    
    evidence_notes = models.TextField(
        blank=True,
        help_text="Additional context or notes about the match"
    )
    
    # Submission metadata
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='submitted_match_reports',
        help_text="User who submitted this report (must be team1 member)"
    )
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    # Match date/time (can differ from submitted_at for backfill)
    played_at = models.DateTimeField(
        help_text="When the match was actually played"
    )
    
    class Meta:
        db_table = 'competition_match_report'
        verbose_name = 'Match Report'
        verbose_name_plural = 'Match Reports'
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['game_id', '-played_at']),
            models.Index(fields=['team1', '-played_at']),
            models.Index(fields=['team2', '-played_at']),
        ]
    
    def __str__(self):
        opponent = self.team2.name if self.team2 else 'Unknown'
        return f"{self.team1.name} vs {opponent} ({self.result}) - {self.played_at.strftime('%Y-%m-%d')}"
