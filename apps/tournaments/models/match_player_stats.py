"""
Match Player Statistics — Per-player per-match/map performance tracking.

Provides detailed player stats for FPS esports (Valorant primary):
  - MatchPlayerStat: individual player performance in a match (aggregated across maps)
  - MatchMapPlayerStat: individual player performance on a single map within a series

Designed to support VLR.gg / TheSpike.gg-style scoreboard display.
"""

from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedModel


class MatchPlayerStat(TimestampedModel):
    """
    Aggregated player statistics for an entire match (series).

    For a BO3 match, this contains totals/averages across all maps played.
    Links to the player (User), the match, and optionally the team.
    """

    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='player_stats',
        verbose_name=_('Match'),
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='match_stats',
        verbose_name=_('Player'),
    )
    team_id = models.PositiveIntegerField(
        verbose_name=_('Team ID'),
        null=True,
        blank=True,
        db_index=True,
        help_text=_('Team this player played for in this match'),
    )

    # Agent selection (for Valorant)
    agent = models.CharField(
        max_length=30,
        blank=True,
        default='',
        verbose_name=_('Agent'),
        help_text=_('Primary agent played (Valorant-specific)'),
    )

    # Core FPS stats
    kills = models.PositiveIntegerField(default=0, verbose_name=_('Kills'))
    deaths = models.PositiveIntegerField(default=0, verbose_name=_('Deaths'))
    assists = models.PositiveIntegerField(default=0, verbose_name=_('Assists'))

    # Valorant-specific
    acs = models.DecimalField(
        max_digits=7, decimal_places=1, default=0,
        verbose_name=_('ACS'),
        help_text=_('Average Combat Score'),
    )
    adr = models.DecimalField(
        max_digits=7, decimal_places=1, default=0,
        verbose_name=_('ADR'),
        help_text=_('Average Damage per Round'),
    )
    headshot_pct = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('HS%'),
        help_text=_('Headshot percentage'),
    )

    # Advanced stats
    first_kills = models.PositiveIntegerField(
        default=0, verbose_name=_('First Kills'),
        help_text=_('First bloods / opening kills'),
    )
    first_deaths = models.PositiveIntegerField(
        default=0, verbose_name=_('First Deaths'),
        help_text=_('Times died first in a round'),
    )
    clutches = models.PositiveIntegerField(
        default=0, verbose_name=_('Clutches'),
        help_text=_('Clutch rounds won'),
    )
    multi_kills = models.PositiveIntegerField(
        default=0, verbose_name=_('Multi-kills'),
        help_text=_('Rounds with 3+ kills'),
    )
    plants = models.PositiveIntegerField(
        default=0, verbose_name=_('Plants'),
        help_text=_('Spike plants'),
    )
    defuses = models.PositiveIntegerField(
        default=0, verbose_name=_('Defuses'),
        help_text=_('Spike defuses'),
    )

    # Computed / cached
    kd_ratio = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_('K/D'),
        help_text=_('Kill/Death ratio (cached)'),
    )
    kast_pct = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('KAST%'),
        help_text=_('Kill/Assist/Survive/Trade percentage'),
    )

    # MVP flag
    is_mvp = models.BooleanField(
        default=False,
        verbose_name=_('MVP'),
        help_text=_('Match MVP designation'),
    )

    class Meta:
        db_table = 'tournament_match_player_stat'
        verbose_name = _('Match Player Stat')
        verbose_name_plural = _('Match Player Stats')
        ordering = ['-acs']
        unique_together = [('match', 'player')]
        indexes = [
            models.Index(fields=['match', 'team_id'], name='idx_mps_match_team'),
            models.Index(fields=['player', '-acs'], name='idx_mps_player_acs'),
            models.Index(fields=['match', '-acs'], name='idx_mps_match_acs'),
        ]

    def __str__(self):
        return f"{self.player} — Match #{self.match_id} ({self.kills}/{self.deaths}/{self.assists})"

    @property
    def team(self):
        """Lazy-load Team from organizations app."""
        if not self.team_id:
            return None
        if not hasattr(self, '_team_cache'):
            from apps.organizations.models import Team
            self._team_cache = Team.objects.filter(pk=self.team_id).first()
        return self._team_cache

    def save(self, *args, **kwargs):
        # Auto-compute K/D ratio as Decimal
        if self.deaths > 0:
            self.kd_ratio = (Decimal(str(self.kills)) / Decimal(str(self.deaths))).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        elif self.kills > 0:
            self.kd_ratio = Decimal(str(self.kills))
        super().save(*args, **kwargs)


class MatchMapPlayerStat(TimestampedModel):
    """
    Per-map player statistics within a series (BO3/BO5).

    For a 3-map BO3, there would be 3 rows per player.
    Enables map-by-map scoreboard display like VLR.gg.
    """

    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='map_player_stats',
        verbose_name=_('Match'),
    )
    player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='map_match_stats',
        verbose_name=_('Player'),
    )
    team_id = models.PositiveIntegerField(
        verbose_name=_('Team ID'),
        null=True,
        blank=True,
        help_text=_('Team this player played for'),
    )

    # Map identification
    map_number = models.PositiveSmallIntegerField(
        verbose_name=_('Map Number'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Map number in the series (1, 2, 3...)'),
    )
    map_name = models.CharField(
        max_length=50,
        blank=True,
        default='',
        verbose_name=_('Map Name'),
        help_text=_('Map name (e.g., Ascent, Haven)'),
    )

    # Agent
    agent = models.CharField(
        max_length=30,
        blank=True,
        default='',
        verbose_name=_('Agent'),
    )

    # Stats
    kills = models.PositiveIntegerField(default=0, verbose_name=_('Kills'))
    deaths = models.PositiveIntegerField(default=0, verbose_name=_('Deaths'))
    assists = models.PositiveIntegerField(default=0, verbose_name=_('Assists'))
    acs = models.DecimalField(max_digits=7, decimal_places=1, default=0, verbose_name=_('ACS'))
    adr = models.DecimalField(max_digits=7, decimal_places=1, default=0, verbose_name=_('ADR'))
    headshot_pct = models.DecimalField(
        max_digits=5, decimal_places=1, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name=_('HS%'),
    )
    first_kills = models.PositiveIntegerField(default=0, verbose_name=_('FK'))
    first_deaths = models.PositiveIntegerField(default=0, verbose_name=_('FD'))

    class Meta:
        db_table = 'tournament_match_map_player_stat'
        verbose_name = _('Match Map Player Stat')
        verbose_name_plural = _('Match Map Player Stats')
        ordering = ['map_number', '-acs']
        unique_together = [('match', 'player', 'map_number')]
        indexes = [
            models.Index(fields=['match', 'map_number', 'team_id'], name='idx_mmps_match_map_team'),
        ]

    def __str__(self):
        return f"{self.player} — Match #{self.match_id} Map {self.map_number} ({self.kills}/{self.deaths}/{self.assists})"

    @property
    def team(self):
        """Lazy-load Team from organizations app."""
        if not self.team_id:
            return None
        if not hasattr(self, '_team_cache'):
            from apps.organizations.models import Team
            self._team_cache = Team.objects.filter(pk=self.team_id).first()
        return self._team_cache
