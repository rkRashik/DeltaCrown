"""
Team model for competitive esports squads.

A Team represents the competitive unit that registers for tournaments
and plays matches. Teams can be Independent (user-owned) or part of
an Organization (professional entity).
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.db.models import Q

from ..choices import TeamStatus

User = get_user_model()


class Team(models.Model):
    """
    Competitive unit that registers for tournaments and plays matches.
    
    Types:
    1. Organization Team: Owned by an Organization, managed by appointed Manager
    2. Independent Team: Owned by a single User (Captain/Owner)
    
    Constraints:
    - One User can own max 1 Independent Team per game title
    - One Organization can own unlimited Teams per game
    - Team names must be unique globally (slug uniqueness)
    - Must have EITHER organization OR owner (not both, not neither)
    
    Database Table: organizations_team
    """
    
    # Identity fields
    name = models.CharField(
        max_length=100,
        help_text="Team display name (e.g., 'Protocol V', 'Syntax FC')"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="URL-safe identifier (auto-generated from name)"
    )
    tag = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        db_index=True,
        help_text="Team tag/abbreviation (e.g., 'PRTCL', 'SYN') - max 5 chars, unique per game"
    )
    tagline = models.CharField(
        max_length=100,
        blank=True,
        help_text="Short team motto/slogan (e.g., 'Victory Through Strategy')"
    )
    
    # Ownership (Team can be independent OR org-owned)
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.SET_NULL,
        related_name='teams',
        null=True,
        blank=True,
        db_index=True,
        help_text="Owning organization (NULL for independent teams)"
    )
    # Creator/Owner - User who created/owns the team
    # For independent teams: this is the owner
    # For org teams: this is who created it (audit trail)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='created_teams',
        null=True,
        blank=True,
        db_index=True,
        help_text="User who created/owns this team"
    )
    
    # Game context
    game_id = models.IntegerField(
        db_index=True,
        help_text="Game title ID (FK to games.Game - avoiding direct FK for now)"
    )
    region = models.CharField(
        max_length=50,
        help_text="Home region (e.g., 'Bangladesh', 'India') - identity, not server"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=TeamStatus.choices,
        default=TeamStatus.ACTIVE,
        db_index=True,
        help_text="Team lifecycle status"
    )
    
    # Privacy
    visibility = models.CharField(
        max_length=20,
        choices=[
            ('PUBLIC', 'Public'),
            ('PRIVATE', 'Private'),
            ('UNLISTED', 'Unlisted'),
        ],
        default='PUBLIC',
        db_index=True,
        help_text='Team visibility setting'
    )
    
    # Branding assets
    logo = models.ImageField(
        upload_to='teams/logos/',
        null=True,
        blank=True,
        help_text="Team logo (or inherits from organization if enforce_brand=True)"
    )
    banner = models.ImageField(
        upload_to='teams/banners/',
        null=True,
        blank=True,
        help_text="Profile page header banner"
    )
    
    # Team Colors
    primary_color = models.CharField(
        max_length=7,
        blank=True,
        default='#3B82F6',
        help_text="Primary team color (hex format, e.g., #3B82F6)"
    )
    accent_color = models.CharField(
        max_length=7,
        blank=True,
        default='#10B981',
        help_text="Accent team color (hex format, e.g., #10B981)"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Team bio/description"
    )
    
    # Tournament Operations Center (TOC) settings
    preferred_server = models.CharField(
        max_length=50,
        blank=True,
        help_text="TOC: Preferred game server (e.g., 'Singapore', 'Mumbai')"
    )
    emergency_contact_discord = models.CharField(
        max_length=50,
        blank=True,
        help_text="TOC: Discord handle for tournament emergencies"
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="TOC: Phone number for tournament emergencies"
    )
    
    # Social Media Links (Gate 5)
    twitter_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team Twitter/X profile URL'
    )
    instagram_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team Instagram profile URL'
    )
    youtube_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team YouTube channel URL'
    )
    twitch_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team Twitch channel URL'
    )
    facebook_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team Facebook page URL'
    )
    tiktok_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team TikTok profile URL'
    )
    discord_webhook_url = models.URLField(
        blank=True,
        max_length=300,
        help_text='Discord webhook URL for team notifications'
    )
    discord_url = models.URLField(
        blank=True,
        max_length=300,
        help_text='Discord server invite link (discord.gg/...)'
    )

    # ── Discord Bot Integration ──────────────────────────────────────
    # These IDs are Discord "snowflakes" (up to 20 digits).
    discord_guild_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Discord server (guild) ID — required for bot integration',
    )
    discord_announcement_channel_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Channel ID for bi-directional announcements',
    )
    discord_chat_channel_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Channel ID for real-time chat sync ("Lobby")',
    )
    discord_voice_channel_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Voice channel ID for one-click voice join',
    )
    discord_bot_active = models.BooleanField(
        default=False,
        help_text='True when the platform bot is verified present in this guild',
    )
    discord_captain_role_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Discord role ID to assign/remove when a member becomes Captain (OWNER)',
    )
    discord_manager_role_id = models.CharField(
        max_length=20,
        blank=True,
        help_text='Discord role ID to assign/remove when a member becomes Manager',
    )
    website_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Custom team website URL'
    )
    whatsapp_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team WhatsApp group invite URL'
    )
    messenger_url = models.URLField(
        blank=True,
        max_length=200,
        help_text='Team Messenger group URL'
    )
    
    # Roster management
    roster_locked = models.BooleanField(
        default=False,
        help_text="Manual roster lock — prevents all roster changes when True"
    )
    is_recruiting = models.BooleanField(
        default=True,
        help_text="Whether the team is actively recruiting new members"
    )
    tagline = models.CharField(
        max_length=140,
        blank=True,
        help_text="Short one-liner shown on team cards and detail hero"
    )
    
    # Invite link
    invite_code = models.CharField(
        max_length=32,
        blank=True,
        db_index=True,
        help_text="Shareable invite code for joining the team"
    )
    
    # Change tracking (for change restriction rules)
    name_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time team name was changed (30-day cooldown)"
    )
    tag_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time team tag was changed (30-day cooldown)"
    )
    region_changed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time team region was changed (30-day cooldown)"
    )
    
    # Platform
    platform = models.CharField(
        max_length=30,
        blank=True,
        default='PC',
        help_text="Primary platform: PC, Console, Mobile, Cross-Platform"
    )

    # Identity Tags (game-specific play identity)
    playstyle = models.CharField(
        max_length=50,
        blank=True,
        help_text="Team play style tag (e.g., 'Aggressive', 'Methodical', 'Adaptive')"
    )
    playpace = models.CharField(
        max_length=50,
        blank=True,
        help_text="Team pace tag (e.g., 'Fast Execute', 'Slow Default', 'Mixed')"
    )
    playfocus = models.CharField(
        max_length=50,
        blank=True,
        help_text="Team focus tag (e.g., 'Aim-Heavy', 'Strategy-First', 'Utility-Rich')"
    )

    # Metadata
    is_temporary = models.BooleanField(
        default=False,
        help_text="Created during tournament registration (clean up after tournament)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Team creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp"
    )
    
    class Meta:
        db_table = 'organizations_team'  # vNext Team uses its own table
        ordering = ['-created_at']
        
        constraints = [
            # Tag uniqueness per game (case-sensitive at DB level, case-insensitive enforced in app)
            # Allows NULL tags (teams can exist without tags)
            models.UniqueConstraint(
                fields=['game_id', 'tag'],
                condition=Q(tag__isnull=False),
                name='unique_tag_per_game'
            ),
        ]
        
        indexes = [
            models.Index(fields=['slug'], name='team_slug_idx'),
            models.Index(fields=['game_id', 'region'], name='team_game_region_idx'),
            models.Index(fields=['organization'], name='team_org_idx'),
            models.Index(fields=['status'], name='team_status_idx'),
            models.Index(fields=['game_id', 'tag'], name='team_game_tag_idx'),
            models.Index(fields=['created_by'], name='team_created_by_idx'),
        ]
        
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
    
    def __str__(self):
        """Return team name for admin display."""
        if self.organization:
            return f"{self.organization.name} - {self.name}"
        return f"{self.name} (Independent)"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            
            # Ensure slug uniqueness
            while Team.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """
        Return canonical URL for team detail page.
        
        Canonical URLs:
        - Organization team: /orgs/<org_slug>/teams/<team_slug>/
        - Independent team: /teams/<team_slug>/
        
        Returns:
            str: Absolute URL path
        """
        from django.urls import reverse
        
        if self.organization:
            # Organization team - use org-scoped URL
            return reverse('organizations:org_team_detail', 
                         kwargs={'org_slug': self.organization.slug, 'team_slug': self.slug})
        else:
            # Independent team - use simple /teams/<slug>/ route
            return reverse('organizations:team_detail', kwargs={'team_slug': self.slug})
    
    def is_organization_team(self):
        """
        Check if team is owned by an organization.
        
        Returns:
            bool: True if organization-owned, False if independent
        """
        return self.organization is not None
    
    def get_effective_logo_url(self):
        """
        Return logo URL (team logo or inherited org logo).
        
        If organization enforces branding, returns organization logo.
        Otherwise returns team logo or default placeholder.
        
        Returns:
            str: Logo URL path
        """
        if self.organization and self.organization.enforce_brand:
            if self.organization.logo:
                return self.organization.logo.url
        
        if self.logo:
            return self.logo.url
        
        return '/static/images/default_team_logo.png'
    
    def can_user_manage(self, user):
        """
        Check if user has management permissions for this team.
        
        Permission hierarchy:
        - Independent team: created_by user is owner (full control)
        - Organization team: Org CEO → Org Manager → Team Manager/Coach
        
        Args:
            user: User instance to check permissions for
            
        Returns:
            bool: True if user can manage team settings
        """
        if self.organization:
            # Organization team
            # Check if user is Organization CEO
            if user == self.organization.ceo:
                return True
            
            # Check if user is Organization Manager
            from apps.organizations.models import OrganizationMembership
            if OrganizationMembership.objects.filter(
                organization=self.organization,
                user=user,
                role__in=['MANAGER', 'ADMIN'],
                status='ACTIVE'
            ).exists():
                return True
            
            # Check if user is Team Manager or Coach
            return self.memberships.filter(
                user=user,
                status='ACTIVE',
                role__in=['MANAGER', 'COACH']
            ).exists()
        else:
            # Independent team - only creator/owner can manage
            return user == self.created_by

    # ─── Legacy Compatibility Properties ──────────────────────────────
    # These properties bridge the API gap between legacy teams.Team and
    # organizations.Team so that code migrated from apps/teams continues
    # to work without query-level changes.

    @property
    def game(self):
        """Legacy compat: resolve integer game_id → slug string.
        
        Legacy code expected ``team.game`` to return a slug like
        ``'valorant'``.  The vNext model stores ``game_id`` (int FK to
        games.Game) so this property does the lookup transparently.
        """
        if not hasattr(self, '_game_slug_cache'):
            try:
                from apps.games.models import Game
                self._game_slug_cache = (
                    Game.objects.values_list('slug', flat=True)
                    .get(pk=self.game_id)
                )
            except Exception:
                self._game_slug_cache = ''
        return self._game_slug_cache

    @property
    def game_obj(self):
        """Convenience: full Game model instance for this team."""
        if not hasattr(self, '_game_obj_cache'):
            try:
                from apps.games.models import Game
                self._game_obj_cache = Game.objects.get(pk=self.game_id)
            except Exception:
                self._game_obj_cache = None
        return self._game_obj_cache

    def get_game_display(self):
        """Legacy compat: return human-readable game name."""
        obj = self.game_obj
        return obj.display_name if obj else self.game

    @property
    def is_active(self):
        """Legacy compat: True when status == ACTIVE."""
        return self.status == TeamStatus.ACTIVE

    @property
    def is_public(self):
        """Legacy compat: True when visibility == PUBLIC."""
        return self.visibility == 'PUBLIC'

    @property
    def memberships(self):
        """Alias for the vnext_memberships reverse relation.

        The vNext TeamMembership FK uses ``related_name='vnext_memberships'``
        to avoid clashing with the legacy model during the transition.  This
        property lets code reference ``team.memberships`` transparently.
        """
        return self.vnext_memberships

    # Social link aliases (legacy used ``twitter``, vNext uses ``twitter_url``)
    @property
    def twitter(self):
        return self.twitter_url

    @property
    def instagram(self):
        return self.instagram_url

    @property
    def youtube(self):
        return self.youtube_url

    @property
    def twitch(self):
        return self.twitch_url

    @property
    def discord(self):
        return self.discord_url or self.discord_webhook_url
