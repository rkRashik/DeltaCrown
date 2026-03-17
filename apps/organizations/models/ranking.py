"""
Ranking models for Crown Point (CP) system.

TeamRanking tracks individual team rankings with Crown Points.
OrganizationRanking aggregates rankings across an organization's teams.
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta

from ..choices import RankingTier


class TeamRanking(models.Model):
    """
    Crown Point rankings for teams.

    Database Table: organizations_ranking
    """

    # Relationship
    team = models.OneToOneField(
        'Team',
        on_delete=models.CASCADE,
        related_name='ranking',
        primary_key=True,
        help_text="Team this ranking belongs to"
    )

    # Crown Points
    current_cp = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Current Crown Points (can decrease via decay)"
    )
    season_cp = models.IntegerField(
        default=0,
        help_text="CP earned this season (resets every 4 months)"
    )
    all_time_cp = models.IntegerField(
        default=0,
        help_text="Lifetime maximum CP achieved (never decreases)"
    )

    # Tier classification
    tier = models.CharField(
        max_length=20,
        choices=RankingTier.choices,
        default=RankingTier.UNRANKED,
        db_index=True,
        help_text="Tier based on current CP thresholds"
    )

    # Leaderboard positions
    global_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Global position (all games, updated every 5 minutes)"
    )
    regional_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Regional position (same region, updated every 5 minutes)"
    )
    rank_change_24h = models.IntegerField(
        default=0,
        help_text="Rank change in last 24 hours (positive = climbing)"
    )
    rank_change_7d = models.IntegerField(
        default=0,
        help_text="Rank change in last 7 days (positive = climbing)"
    )

    # Streaks
    is_hot_streak = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Currently on hot streak (3+ consecutive wins)"
    )
    streak_count = models.IntegerField(
        default=0,
        help_text="Current win streak count (resets on loss)"
    )

    # Activity tracking
    last_activity_date = models.DateTimeField(
        auto_now=True,
        help_text="Last match played timestamp"
    )
    last_decay_applied = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time inactivity decay was applied"
    )

    class Meta:
        db_table = 'organizations_ranking'
        ordering = ['-current_cp']
        indexes = [
            models.Index(fields=['-current_cp'], name='ranking_cp_desc_idx'),
            models.Index(fields=['tier'], name='ranking_tier_idx'),
            models.Index(fields=['is_hot_streak'], name='ranking_streak_idx'),
            models.Index(fields=['-current_cp', 'tier'], name='ranking_cp_tier_idx'),
        ]
        verbose_name = 'Team Ranking'
        verbose_name_plural = 'Team Rankings'

    def __str__(self):
        """Return human-readable ranking representation."""
        return f"{self.team.name}: {self.current_cp} CP ({self.tier})"

    def recalculate_tier(self):
        """Determine tier based on current CP thresholds."""
        if self.current_cp >= 80000:
            self.tier = RankingTier.CROWN
        elif self.current_cp >= 40000:
            self.tier = RankingTier.ASCENDANT
        elif self.current_cp >= 15000:
            self.tier = RankingTier.DIAMOND
        elif self.current_cp >= 5000:
            self.tier = RankingTier.PLATINUM
        elif self.current_cp >= 1500:
            self.tier = RankingTier.GOLD
        elif self.current_cp >= 500:
            self.tier = RankingTier.SILVER
        elif self.current_cp >= 50:
            self.tier = RankingTier.BRONZE
        else:
            self.tier = RankingTier.UNRANKED

    def update_cp(self, points_delta, reason=""):
        """Add or subtract CP and recalculate tier."""
        self.current_cp = max(0, self.current_cp + points_delta)
        self.season_cp = max(0, self.season_cp + points_delta)
        self.all_time_cp = max(self.all_time_cp, self.current_cp)
        self.recalculate_tier()
        self.save()

    def apply_decay(self):
        """Apply 5% CP decay for inactivity (>7 days)."""
        days_inactive = (timezone.now() - self.last_activity_date).days
        if days_inactive >= 7:
            decay_amount = int(self.current_cp * 0.05)
            if decay_amount > 0:
                self.update_cp(-decay_amount, reason="Weekly inactivity decay")
                self.last_decay_applied = timezone.now()
                self.save()

    def update_hot_streak(self, won_match):
        """Update hot streak status based on match result."""
        if won_match:
            self.streak_count += 1
            if self.streak_count >= 3:
                self.is_hot_streak = True
        else:
            self.streak_count = 0
            self.is_hot_streak = False
        self.save()


class OrganizationRanking(models.Model):
    """
    Aggregated rankings for Organizations.

    Empire Score is calculated from top 3 teams' CP:
    - 1st best team: 100% CP
    - 2nd best team: 75% CP
    - 3rd best team: 50% CP

    Updated nightly via Celery job.

    Database Table: organizations_org_ranking
    """

    # Relationship
    organization = models.OneToOneField(
        'Organization',
        on_delete=models.CASCADE,
        related_name='ranking',
        primary_key=True,
        help_text="Organization this ranking belongs to"
    )

    # Empire Score
    empire_score = models.IntegerField(
        default=0,
        db_index=True,
        help_text="Aggregated score from top 3 teams' CP"
    )

    # Leaderboard positions
    global_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Global organization rank (updated nightly)"
    )
    regional_rank = models.IntegerField(
        null=True,
        blank=True,
        help_text="Regional organization rank (updated nightly)"
    )

    # Trophy count
    total_trophies = models.IntegerField(
        default=0,
        help_text="Total tournament wins across all teams"
    )

    # Timestamps
    last_calculated = models.DateTimeField(
        auto_now=True,
        help_text="Last empire score calculation timestamp"
    )

    class Meta:
        db_table = 'organizations_org_ranking'
        ordering = ['-empire_score']
        indexes = [
            models.Index(fields=['-empire_score'], name='org_ranking_score_desc_idx'),
            models.Index(fields=['global_rank'], name='org_ranking_rank_idx'),
        ]
        verbose_name = 'Organization Ranking'
        verbose_name_plural = 'Organization Rankings'

    def __str__(self):
        """Return human-readable org ranking representation."""
        return f"{self.organization.name}: {self.empire_score} Empire Score"

    def recalculate_empire_score(self):
        """Recalculate Empire Score from top 3 teams' CP."""
        top_teams = (
            self.organization.teams
            .filter(status='ACTIVE', is_temporary=False)
            .select_related('ranking')
            .order_by('-ranking__current_cp')[:3]
        )

        weights = [1.0, 0.75, 0.5]
        score = 0

        for i, team in enumerate(top_teams):
            if hasattr(team, 'ranking'):
                score += int(team.ranking.current_cp * weights[i])

        self.empire_score = score
        self.save()

        return score
