"""
Team membership model for roster management.

TeamMembership represents a user's role on a team roster, including
their organizational role, roster slot, and tournament captain status.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q

from ..choices import MembershipStatus, MembershipRole, RosterSlot

User = get_user_model()


class TeamMembership(models.Model):
    """
    Represents a user's role on a team roster.
    
    Role Categories (4 Orthogonal Systems):
    1. Organizational Role: OWNER, MANAGER, COACH, PLAYER, SUBSTITUTE, ANALYST, SCOUT
    2. Tournament Captain Flag: is_tournament_captain (Boolean, max 1 per team)
    3. Roster Slot: STARTER, SUBSTITUTE, COACH, ANALYST
    4. In-Game Tactical Role: Game-specific (Duelist, IGL, AWPer, etc.)
    
    Game Passport Requirement:
    - Required for: PLAYER/SUBSTITUTE roles in STARTER/SUBSTITUTE slots
    - Not required for: OWNER, MANAGER, COACH, ANALYST roles
    - Validated at: Team join, roster slot change, tournament registration
    
    Database Table: organizations_membership
    """
    
    # Relationships
    team = models.ForeignKey(
        'organizations.Team',  # vNext Team model
        on_delete=models.CASCADE,
        related_name='vnext_memberships',
        help_text="Team this membership belongs to"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='team_memberships',
        help_text="User on the roster"
    )
    
    # Game (denormalized for constraint enforcement)
    # Automatically set from team.game_id on save
    game_id = models.IntegerField(
        db_index=True,
        default=1,  # Temporary default for migration, will be auto-populated from team
        help_text="Game ID (denormalized from team for constraint: one team per game per user)"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=MembershipStatus.choices,
        default=MembershipStatus.INVITED,
        db_index=True,
        help_text="Membership status (ACTIVE, INACTIVE, INVITED, SUSPENDED)"
    )
    
    # Role system
    role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        help_text="Organizational role (determines permissions)"
    )
    roster_slot = models.CharField(
        max_length=20,
        choices=RosterSlot.choices,
        null=True,
        blank=True,
        help_text="Physical roster slot (STARTER, SUBSTITUTE, COACH, ANALYST)"
    )
    player_role = models.CharField(
        max_length=50,
        blank=True,
        help_text="Game-specific tactical role (e.g., 'Duelist', 'IGL', 'AWPer')"
    )
    
    # Tournament captain designation
    is_tournament_captain = models.BooleanField(
        default=False,
        help_text="Designated captain for tournament admin duties (max 1 per team)"
    )
    
    # Timestamps
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date user joined team roster"
    )
    left_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date user left team (if status=INACTIVE)"
    )
    left_reason = models.CharField(
        max_length=100,
        blank=True,
        help_text="Reason for leaving (Resignation, Kicked, Transfer, etc.)"
    )
    
    class Meta:
        db_table = 'organizations_membership'
        ordering = ['-joined_at']
        
        constraints = [
            # One active membership per user per team
            models.UniqueConstraint(
                fields=['team', 'user'],
                condition=Q(status=MembershipStatus.ACTIVE),
                name='one_active_membership_per_user_team'
            ),
            # ONE TEAM PER GAME PER USER (core platform rule)
            models.UniqueConstraint(
                fields=['user', 'game_id'],
                condition=Q(status=MembershipStatus.ACTIVE),
                name='one_active_team_per_game_per_user'
            ),
            # Only one tournament captain per team
            models.UniqueConstraint(
                fields=['team'],
                condition=Q(is_tournament_captain=True, status=MembershipStatus.ACTIVE),
                name='one_tournament_captain_per_team'
            ),
        ]
        
        indexes = [
            models.Index(fields=['team', 'status'], name='membership_team_status_idx'),
            models.Index(fields=['user', 'status'], name='membership_user_status_idx'),
            models.Index(fields=['user', 'game_id'], name='membership_user_game_idx'),
            models.Index(fields=['role'], name='membership_role_idx'),
            models.Index(fields=['is_tournament_captain'], name='membership_captain_idx'),
        ]
        
        verbose_name = 'Team Membership'
        verbose_name_plural = 'Team Memberships'
    
    def __str__(self):
        """Return human-readable membership representation."""
        captain_badge = ' [C]' if self.is_tournament_captain else ''
        return f"{self.user.username} - {self.role} on {self.team.name}{captain_badge}"
    
    def get_permission_list(self):
        """
        Return list of permission strings for this membership.
        
        Permissions are role-based and determine what actions
        the user can perform on the team.
        
        Returns:
            list[str]: Permission strings (e.g., ['register_tournaments', 'edit_roster'])
        """
        permissions = {
            MembershipRole.OWNER: ['ALL'],
            MembershipRole.MANAGER: [
                'register_tournaments',
                'edit_roster',
                'edit_team',
                'schedule_scrims',
                'edit_toc'
            ],
            MembershipRole.COACH: [
                'edit_toc',
                'schedule_scrims',
                'view_analytics'
            ],
            MembershipRole.PLAYER: ['view_dashboard'],
            MembershipRole.SUBSTITUTE: ['view_dashboard'],
            MembershipRole.ANALYST: ['view_analytics'],
            MembershipRole.SCOUT: ['view_player_stats'],
        }
        return permissions.get(self.role, [])
    
    def can_manage_roster(self):
        """
        Check if this member can invite/kick other members.
        
        Returns:
            bool: True if member has roster management permissions
        """
        return (
            self.role in [MembershipRole.OWNER, MembershipRole.MANAGER] and
            self.status == MembershipStatus.ACTIVE
        )
    
    def requires_game_passport(self):
        """
        Check if this role requires a Game Passport.
        
        Game Passports (verified Game IDs) are required for:
        - PLAYER or SUBSTITUTE roles
        - In STARTER or SUBSTITUTE roster slots
        
        Non-playing roles (Owner, Manager, Coach, Analyst) do not
        require Game Passports.
        
        Returns:
            bool: True if Game Passport required for tournament eligibility
        """
        is_playing_role = self.role in [MembershipRole.PLAYER, MembershipRole.SUBSTITUTE]
        is_playing_slot = self.roster_slot in [RosterSlot.STARTER, RosterSlot.SUBSTITUTE]
        return is_playing_role and is_playing_slot
    
    def can_check_in_tournaments(self):
        """
        Check if this member can perform tournament check-ins.
        
        Tournament captains, owners, and managers can check in teams
        for tournament matches.
        
        Returns:
            bool: True if member can check in team for tournaments
        """
        return (
            (self.is_tournament_captain or 
             self.role in [MembershipRole.OWNER, MembershipRole.MANAGER]) and
            self.status == MembershipStatus.ACTIVE
        )
    
    def save(self, *args, **kwargs):
        """
        Override save to auto-populate game_id from team.
        
        This enables the one-team-per-game constraint.
        """
        if self.team_id and not self.game_id:
            # Auto-populate game_id from team
            self.game_id = self.team.game_id
        super().save(*args, **kwargs)
