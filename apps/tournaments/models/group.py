"""
Group Stage Models

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 4: Tournament Models)
- Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md (Section 2.5)

Models:
- Group: Represents a group in group stage tournament
- GroupStanding: Tracks standings/points for participants in a group
- GroupMatch: Tracks matches within groups (extends Match)

Supports 9 games:
- eFootball, FC Mobile, FIFA (goals-based)
- Valorant, CS2 (rounds-based)
- PUBG Mobile, Free Fire (placement + kills)
- Mobile Legends (kills/deaths/assists)
- Call of Duty Mobile (eliminations/score)
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, CheckConstraint, F
from django.contrib.postgres.fields import JSONField
from decimal import Decimal

from apps.common.models import TimestampedModel


class Group(TimestampedModel):
    """
    Represents a group in a group stage tournament.
    
    A tournament with group format will have multiple groups,
    each containing a subset of participants who play against each other.
    """
    
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name=_('Tournament'),
        help_text=_('Tournament this group belongs to')
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Group Name'),
        help_text=_('e.g., "Group A", "Group B", or custom name')
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Display Order'),
        help_text=_('Order in which groups are displayed (0 = first)')
    )
    
    max_participants = models.PositiveIntegerField(
        validators=[MinValueValidator(2)],
        verbose_name=_('Max Participants'),
        help_text=_('Maximum number of participants in this group')
    )
    
    advancement_count = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        verbose_name=_('Advancement Count'),
        help_text=_('Number of top teams/players that advance to next phase')
    )
    
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Group Configuration'),
        help_text=_('JSON config: points_system, tiebreaker_rules, match_format')
    )
    
    # Example config:
    # {
    #     "points_system": {"win": 3, "draw": 1, "loss": 0},
    #     "tiebreaker_rules": ["head_to_head", "goal_difference", "goals_for"],
    #     "match_format": "round_robin",  # or "double_round_robin"
    #     "matches_per_matchday": 2
    # }
    
    is_finalized = models.BooleanField(
        default=False,
        verbose_name=_('Is Finalized'),
        help_text=_('Whether group assignments are finalized (can no longer edit)')
    )
    
    draw_seed = models.CharField(
        max_length=64,
        blank=True,
        verbose_name=_('Draw Seed'),
        help_text=_('Random seed used for provable draw (transparency)')
    )
    
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('Is Deleted'),
        help_text=_('Soft delete flag')
    )
    
    class Meta:
        db_table = 'tournament_groups'
        verbose_name = _('Group')
        verbose_name_plural = _('Groups')
        ordering = ['tournament', 'display_order', 'name']
        indexes = [
            models.Index(fields=['tournament', 'is_deleted']),
            models.Index(fields=['tournament', 'display_order']),
        ]
        constraints = [
            CheckConstraint(
                check=Q(max_participants__gte=2),
                name='group_min_participants'
            ),
            CheckConstraint(
                check=Q(advancement_count__gte=1),
                name='group_min_advancement'
            ),
        ]
    
    def __str__(self):
        return f"{self.tournament.name} - {self.name}"
    
    @property
    def current_participant_count(self):
        """Get current number of participants in this group."""
        return self.standings.filter(is_deleted=False).count()
    
    @property
    def is_full(self):
        """Check if group is at capacity."""
        return self.current_participant_count >= self.max_participants
    
    @property
    def points_for_win(self):
        """Get points awarded for a win."""
        return self.config.get('points_system', {}).get('win', 3)
    
    @property
    def points_for_draw(self):
        """Get points awarded for a draw."""
        return self.config.get('points_system', {}).get('draw', 1)
    
    @property
    def points_for_loss(self):
        """Get points awarded for a loss."""
        return self.config.get('points_system', {}).get('loss', 0)


class GroupStanding(TimestampedModel):
    """
    Tracks standings for a participant in a group.
    
    Supports game-specific statistics for all 9 games.
    Uses JSONB for flexible game-specific data.
    """
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='standings',
        verbose_name=_('Group')
    )
    
    # Either user OR team (XOR constraint)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='group_standings',
        verbose_name=_('User')
    )
    
    team_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        db_column='team_id',
        verbose_name=_('Team ID')
    )
    
    # Universal standings fields (all games)
    rank = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Rank'),
        help_text=_('Current rank in group (1 = first place)')
    )
    
    matches_played = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Matches Played')
    )
    
    matches_won = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Matches Won')
    )
    
    matches_drawn = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Matches Drawn')
    )
    
    matches_lost = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Matches Lost')
    )
    
    points = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Points'),
        help_text=_('Total points according to points system')
    )
    
    # Goals-based games (eFootball, FC Mobile, FIFA)
    goals_for = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Goals For'),
        help_text=_('Total goals scored (eFootball, FC Mobile, FIFA)')
    )
    
    goals_against = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Goals Against'),
        help_text=_('Total goals conceded (eFootball, FC Mobile, FIFA)')
    )
    
    goal_difference = models.IntegerField(
        default=0,
        verbose_name=_('Goal Difference'),
        help_text=_('Goals For - Goals Against')
    )
    
    # Rounds-based games (Valorant, CS2)
    rounds_won = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Rounds Won'),
        help_text=_('Total rounds won (Valorant, CS2)')
    )
    
    rounds_lost = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Rounds Lost'),
        help_text=_('Total rounds lost (Valorant, CS2)')
    )
    
    round_difference = models.IntegerField(
        default=0,
        verbose_name=_('Round Difference'),
        help_text=_('Rounds Won - Rounds Lost')
    )
    
    # Battle Royale games (PUBG Mobile, Free Fire)
    total_kills = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Kills'),
        help_text=_('Total kills (PUBG Mobile, Free Fire, Mobile Legends, COD Mobile)')
    )
    
    total_deaths = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Deaths'),
        help_text=_('Total deaths (Mobile Legends, COD Mobile)')
    )
    
    placement_points = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Placement Points'),
        help_text=_('Points from match placements (PUBG Mobile, Free Fire)')
    )
    
    average_placement = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Average Placement'),
        help_text=_('Average finishing position (PUBG Mobile, Free Fire)')
    )
    
    # MOBA-specific (Mobile Legends)
    total_assists = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Assists'),
        help_text=_('Total assists (Mobile Legends)')
    )
    
    kda_ratio = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('KDA Ratio'),
        help_text=_('(Kills + Assists) / Deaths (Mobile Legends)')
    )
    
    # FPS-specific (COD Mobile)
    total_score = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Score'),
        help_text=_('Total match score (COD Mobile)')
    )
    
    # Game-specific extended stats (JSONB for flexibility)
    game_stats = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Game-Specific Stats'),
        help_text=_('Additional game-specific statistics')
    )
    
    # Example game_stats:
    # {
    #     "survival_time_seconds": 1800,  # PUBG/Free Fire
    #     "headshot_percentage": 42.5,    # CS2/Valorant/COD
    #     "mvp_count": 3,                 # Mobile Legends
    #     "multi_kill_count": 5,          # Any game
    #     "damage_dealt": 125000          # Any game
    # }
    
    # Advancement status
    is_advancing = models.BooleanField(
        default=False,
        verbose_name=_('Is Advancing'),
        help_text=_('Whether this participant advances to next phase')
    )
    
    is_eliminated = models.BooleanField(
        default=False,
        verbose_name=_('Is Eliminated'),
        help_text=_('Whether this participant is eliminated')
    )
    
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('Is Deleted')
    )
    
    class Meta:
        db_table = 'tournament_group_standings'
        verbose_name = _('Group Standing')
        verbose_name_plural = _('Group Standings')
        ordering = ['group', 'rank', '-points', '-goal_difference', '-goals_for']
        indexes = [
            models.Index(fields=['group', 'is_deleted']),
            models.Index(fields=['group', 'rank']),
            models.Index(fields=['group', '-points', '-goal_difference']),
            models.Index(fields=['user', 'is_deleted']),
            models.Index(fields=['team_id', 'is_deleted']),
        ]
        constraints = [
            CheckConstraint(
                check=(Q(user__isnull=False) & Q(team_id__isnull=True)) | 
                      (Q(user__isnull=True) & Q(team_id__isnull=False)),
                name='group_standing_user_or_team_xor'
            ),
        ]
    
    def __str__(self):
        participant = self.team.name if self.team else self.user.username
        return f"{self.group.name} - {participant} (Rank {self.rank})"
    
    @property
    def participant_name(self):
        """Get participant display name."""
        return self.team.name if self.team else self.user.username
    
    @property
    def win_percentage(self):
        """Calculate win percentage."""
        if self.matches_played == 0:
            return Decimal('0.00')
        return Decimal(self.matches_won) / Decimal(self.matches_played) * Decimal('100.00')
    
    def calculate_kda(self):
        """Calculate KDA ratio (for MOBA games)."""
        if self.total_deaths == 0:
            return Decimal(self.total_kills + self.total_assists)
        return Decimal(self.total_kills + self.total_assists) / Decimal(self.total_deaths)
    
    def update_rank(self, new_rank):
        """Update rank position."""
        self.rank = new_rank
        
        # Determine advancement status based on rank
        if new_rank <= self.group.advancement_count:
            self.is_advancing = True
            self.is_eliminated = False
        else:
            self.is_advancing = False
            # Only mark eliminated if group stage is complete
            if self.matches_played == self.group.max_participants - 1:  # Round robin complete
                self.is_eliminated = True


class GroupStage(TimestampedModel):
    """
    Represents a complete group stage phase in a tournament.
    
    A GroupStage contains multiple Group instances and manages the overall
    group stage configuration, state, and advancement rules.
    
    Epic 3.2: Group Stage Editor & Manager
    """
    
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='group_stages',
        verbose_name=_('Tournament'),
        help_text=_('Tournament this group stage belongs to')
    )
    
    name = models.CharField(
        max_length=100,
        default='Group Stage',
        verbose_name=_('Stage Name'),
        help_text=_('Name of this group stage phase')
    )
    
    num_groups = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_('Number of Groups'),
        help_text=_('Total number of groups in this stage')
    )
    
    group_size = models.PositiveIntegerField(
        validators=[MinValueValidator(2)],
        verbose_name=_('Group Size'),
        help_text=_('Number of participants per group')
    )
    
    format = models.CharField(
        max_length=20,
        choices=[
            ('round_robin', 'Round Robin'),
            ('double_round_robin', 'Double Round Robin'),
        ],
        default='round_robin',
        verbose_name=_('Format'),
        help_text=_('Match format within groups')
    )
    
    state = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('active', 'Active'),
            ('completed', 'Completed'),
        ],
        default='pending',
        verbose_name=_('State'),
        help_text=_('Current state of the group stage')
    )
    
    # Advancement configuration
    advancement_count_per_group = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(1)],
        verbose_name=_('Teams Advancing Per Group'),
        help_text=_('Number of teams that advance from each group')
    )
    
    # Configuration
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Configuration'),
        help_text=_('JSON config: points_system, tiebreaker_rules, seeding_method')
    )
    # Example config:
    # {
    #     "points_system": {"win": 3, "draw": 1, "loss": 0},
    #     "tiebreaker_rules": ["points", "wins", "head_to_head", "goal_difference", "goals_for"],
    #     "seeding_method": "snake",  # or "round_robin", "manual"
    #     "auto_advance": True  # Automatically advance top N teams
    # }
    
    class Meta:
        db_table = 'tournament_group_stages'
        verbose_name = _('Group Stage')
        verbose_name_plural = _('Group Stages')
        ordering = ['tournament', '-created_at']
        indexes = [
            models.Index(fields=['tournament', 'state']),
        ]
        constraints = [
            CheckConstraint(
                check=Q(num_groups__gte=1),
                name='groupstage_min_groups'
            ),
            CheckConstraint(
                check=Q(group_size__gte=2),
                name='groupstage_min_group_size'
            ),
            CheckConstraint(
                check=Q(advancement_count_per_group__gte=1),
                name='groupstage_min_advancement'
            ),
        ]
    
    def __str__(self):
        return f"{self.tournament.name} - {self.name}"
    
    @property
    def total_participants(self):
        """Calculate total participant capacity."""
        return self.num_groups * self.group_size
    
    @property
    def total_advancing(self):
        """Calculate total number of participants advancing."""
        return self.num_groups * self.advancement_count_per_group
    
    def validate_configuration(self):
        """Validate group stage configuration."""
        if self.advancement_count_per_group >= self.group_size:
            raise ValidationError(
                "Advancement count must be less than group size"
            )
        
        # Ensure we have enough groups created
        if self.pk and self.groups.count() != self.num_groups:
            raise ValidationError(
                f"Expected {self.num_groups} groups, found {self.groups.count()}"
            )

