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

    # ── Legacy compat aliases ──────────────────────────────────────
    # So ``TeamMembership.Status.ACTIVE`` and ``TeamMembership.Role.OWNER``
    # keep working across the entire codebase without touching 100+ files.

    class Status:
        """Compat bridge to MembershipStatus values."""
        ACTIVE = 'ACTIVE'
        INACTIVE = 'INACTIVE'
        INVITED = 'INVITED'
        SUSPENDED = 'SUSPENDED'
        REMOVED = 'REMOVED'
        PENDING = 'INVITED'  # Legacy alias → INVITED

    class Role:
        """Compat bridge to MembershipRole values."""
        OWNER = 'OWNER'
        MANAGER = 'MANAGER'
        COACH = 'COACH'
        PLAYER = 'PLAYER'
        SUBSTITUTE = 'SUBSTITUTE'
        ANALYST = 'ANALYST'
        SCOUT = 'SCOUT'
        # Legacy aliases
        CAPTAIN = 'OWNER'            # Legacy captain → OWNER
        SUB = 'SUBSTITUTE'           # Legacy sub → SUBSTITUTE
        MEMBER = 'PLAYER'            # Legacy member → PLAYER
        GENERAL_MANAGER = 'MANAGER'  # Legacy org role → MANAGER
        TEAM_MANAGER = 'MANAGER'     # Legacy org role → MANAGER
    
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
    
    # Denormalized fields for constraint enforcement
    # Automatically set from team on save
    game_id = models.IntegerField(
        db_index=True,
        default=1,  # Temporary default for migration, will be auto-populated from team
        help_text="Game ID (denormalized from team for constraint: one team per game per user)"
    )
    organization_id = models.IntegerField(
        db_index=True,
        null=True,
        blank=True,
        help_text="Organization ID (denormalized from team for constraint: distinguish org vs independent teams)"
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
    
    # Roster identity (dedicated team profile overrides)
    display_name = models.CharField(
        max_length=80,
        blank=True,
        help_text="Custom display name for this team (overrides global display_name)"
    )
    roster_image = models.ImageField(
        upload_to='roster_photos/',
        blank=True,
        null=True,
        help_text="Dedicated roster photo for this team membership"
    )
    
    # Tournament captain designation
    is_tournament_captain = models.BooleanField(
        default=False,
        help_text="Designated captain for tournament admin duties (max 1 per team)"
    )
    
    # Privacy settings
    hide_ownership = models.BooleanField(
        default=False,
        help_text="Owner can hide ownership status from public team display"
    )
    
    # Granular permission overrides
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Custom permission overrides per-member. Keys are permission strings, "
            "values are booleans. True grants, False revokes. Merges with role defaults."
        )
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
            # ONE INDEPENDENT TEAM PER GAME PER USER (core platform rule)
            # Only applies to independent teams (organization_id IS NULL)
            # Organization teams can have multiple members for same game
            models.UniqueConstraint(
                fields=['user', 'game_id'],
                condition=Q(status=MembershipStatus.ACTIVE, organization_id__isnull=True),
                name='one_active_independent_team_per_game_per_user'
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
    
    # ── All available granular permissions ──
    ALL_PERMISSIONS = [
        'register_tournaments',
        'edit_roster',
        'edit_team',
        'schedule_scrims',
        'edit_toc',
        'view_analytics',
        'view_dashboard',
        'view_player_stats',
        'manage_bounties',
        'manage_economy',
        'manage_media',
        'send_announcements',
        'manage_discord',
    ]
    
    def get_permission_list(self):
        """
        Return list of permission strings for this membership.
        
        Merges role-based defaults with per-member overrides from
        the ``permissions`` JSONField. Override ``True`` grants,
        ``False`` revokes, absent keys fall back to role defaults.
        
        Returns:
            list[str]: Active permission strings
        """
        role_defaults = {
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
        base = set(role_defaults.get(self.role, []))
        
        # Owners always have ALL — overrides don't apply
        if 'ALL' in base:
            return ['ALL']
        
        overrides = self.permissions or {}
        for perm, granted in overrides.items():
            if perm not in self.ALL_PERMISSIONS:
                continue
            if granted:
                base.add(perm)
            else:
                base.discard(perm)
        
        return sorted(base)
    
    def has_permission(self, perm):
        """Check if this member has a specific permission."""
        perms = self.get_permission_list()
        return 'ALL' in perms or perm in perms
    
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
        Override save to auto-populate denormalized fields from team.
        
        - game_id: Enables one-independent-team-per-game constraint
        - organization_id: Distinguishes independent vs org teams
        """
        if self.team_id:
            # Auto-populate game_id and organization_id from team
            if not self.game_id:
                self.game_id = self.team.game_id
            # Always sync organization_id (could change if team transferred)
            self.organization_id = self.team.organization_id
        super().save(*args, **kwargs)

    # ─── Legacy Compatibility Properties ──────────────────────────────
    # These bridge the API gap between legacy teams.TeamMembership (FK to
    # UserProfile) and organizations.TeamMembership (FK to User).

    @property
    def profile(self):
        """Legacy compat: return user's UserProfile.

        Legacy code did ``membership.profile`` (FK → UserProfile).
        vNext stores ``membership.user`` (FK → User).  This property
        returns ``user.profile`` so migrated queries keep working.
        """
        try:
            return self.user.profile
        except Exception:
            return None

    @property
    def is_captain(self):
        """Legacy compat: alias for is_tournament_captain."""
        return self.is_tournament_captain

    @is_captain.setter
    def is_captain(self, value):
        self.is_tournament_captain = value
