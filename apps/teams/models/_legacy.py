# apps/teams/models/_legacy.py
"""
Legacy-compatible implementations of Team domain models.

We keep class names and key fields your project already uses:
- Team(name, tag, logo, captain, created_at)
- TeamMembership(team, profile, role, status, joined_at)
- TeamInvite(team, invited_user/invited_email, inviter, role, token, status, expires_at, created_at)

Notes:
- Uses UserProfile (apps.user_profile) for people references.
- Ensures exactly one ACTIVE captain per team (DB constraint + demotion on promote).
- TEAM_MAX_ROSTER cap enforced in TeamInvite.clean(): you cannot create a *new* PENDING
  invite when there's only ONE slot left, and capacity reserved by existing pending invites
  is also respected to avoid overbooking.
"""
from __future__ import annotations

import uuid
from typing import Optional

# Import get_choices from Game Registry for unified game configuration
from apps.common.game_registry import get_choices as get_game_choices

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

# Global roster ceiling (captain + players + subs)
TEAM_MAX_ROSTER = 8


def team_logo_path(instance, filename):
    # Keep a stable folder structure; id may be None on first save
    pk = getattr(instance, "id", None) or "new"
    return f"team_logos/{pk}/{filename}"


class Team(models.Model):
    # Basics
    name = models.CharField(max_length=100, unique=True, help_text="Team name must be unique")
    tag = models.CharField(max_length=10, unique=True, help_text="Team tag/abbreviation (2-10 characters)")
    description = models.TextField(max_length=500, blank=True, help_text="Brief team description")
    
    # Logo field
    logo = models.ImageField(upload_to=team_logo_path, blank=True, null=True, help_text="Team logo image")

    name_ci = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    tag_ci = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    # Core
    captain = models.ForeignKey(
        "user_profile.UserProfile",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="captain_teams",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Game association (Part A) - uses Game Registry for choices
    game = models.CharField(
        max_length=20,
        choices=get_game_choices,  # Callable from Game Registry
        blank=True,
        default="",
        help_text="Which game this team competes in (blank for legacy teams).",
    )

    # --- Media & Socials (Part B) ---
    banner_image = models.ImageField(upload_to="teams/banners/", blank=True, null=True)
    roster_image = models.ImageField(upload_to="teams/rosters/", blank=True, null=True)
    region = models.CharField(max_length=48, blank=True, default="")

    # Social links (optional)
    twitter = models.URLField(blank=True, default="")
    instagram = models.URLField(blank=True, default="")
    discord = models.URLField(blank=True, default="")
    youtube = models.URLField(blank=True, default="")
    twitch = models.URLField(blank=True, default="")
    linktree = models.URLField(blank=True, default="")

    # Slug per game (optional but recommended)
    slug = models.SlugField(max_length=64, blank=True, default="", help_text="Unique per game")
    
    # Social engagement fields
    followers_count = models.PositiveIntegerField(default=0, help_text="Number of followers")
    posts_count = models.PositiveIntegerField(default=0, help_text="Number of posts")
    is_verified = models.BooleanField(default=False, help_text="Verified team badge")
    is_featured = models.BooleanField(default=False, help_text="Featured team status")
    
    # Team page settings
    allow_posts = models.BooleanField(default=True, help_text="Allow team members to post")
    allow_followers = models.BooleanField(default=True, help_text="Allow users to follow this team")
    posts_require_approval = models.BooleanField(default=False, help_text="Posts need captain approval")
    
    # Privacy and management settings
    is_active = models.BooleanField(default=True, help_text="Team is active and visible")
    is_public = models.BooleanField(default=True, help_text="Team profile is public")
    allow_join_requests = models.BooleanField(default=True, help_text="Allow users to request to join")
    show_statistics = models.BooleanField(default=True, help_text="Show team statistics publicly")
    primary_game = models.CharField(max_length=20, blank=True, default="", help_text="Primary game for team")
    banner = models.ImageField(upload_to="teams/banners/", blank=True, null=True, help_text="Team banner image")
    
    # Team Achievement Points System
    total_points = models.PositiveIntegerField(
        default=0, 
        help_text="Total ranking points earned by this team (read-only, calculated automatically)"
    )
    adjust_points = models.IntegerField(
        default=0, 
        help_text="Manual points adjustment (can be positive or negative)"
    )
    
    # Appearance & Branding (Phase 3)
    HERO_TEMPLATE_CHOICES = [
        ('default', 'Classic'),
        ('centered', 'Centered Focus'),
        ('split', 'Split Screen'),
        ('minimal', 'Minimal Modern'),
        ('championship', 'Championship'),
    ]
    hero_template = models.CharField(
        max_length=20,
        choices=HERO_TEMPLATE_CHOICES,
        default='default',
        help_text="Hero section template style"
    )
    tagline = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Team tagline or motto"
    )
    is_recruiting = models.BooleanField(
        default=False,
        help_text="Display recruiting badge"
    )
    
    # Enhanced Privacy Settings (Phase 4)
    show_roster_publicly = models.BooleanField(
        default=True,
        help_text="Allow non-members to view team roster"
    )
    show_statistics_publicly = models.BooleanField(
        default=True,
        help_text="Display team statistics to public"
    )
    show_tournaments_publicly = models.BooleanField(
        default=True,
        help_text="Show tournament history publicly"
    )
    show_achievements_publicly = models.BooleanField(
        default=True,
        help_text="Display achievements publicly"
    )
    
    # Member Permissions
    members_can_post = models.BooleanField(
        default=True,
        help_text="Allow team members to create posts"
    )
    require_post_approval = models.BooleanField(
        default=False,
        help_text="Captain must approve member posts"
    )
    members_can_invite = models.BooleanField(
        default=False,
        help_text="Allow members to send team invites"
    )
    
    # Join Settings
    auto_accept_join_requests = models.BooleanField(
        default=False,
        help_text="Automatically accept join requests"
    )
    require_application_message = models.BooleanField(
        default=True,
        help_text="Require message with join requests"
    )
    min_rank_requirement = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="Minimum rank/level required to join"
    )
    
    # Display Settings
    hide_member_stats = models.BooleanField(
        default=False,
        help_text="Hide individual member statistics"
    )
    hide_social_links = models.BooleanField(
        default=False,
        help_text="Hide social media links from public"
    )
    show_captain_only = models.BooleanField(
        default=False,
        help_text="Only show captain, hide other members"
    )

    class Meta:
        db_table = "teams_team"
        ordering = ("name",)
        indexes = [
            models.Index(fields=['-total_points', 'name'], name='teams_leaderboard_idx'),
            models.Index(fields=['game', '-total_points'], name='teams_game_leader_idx'),
            models.Index(fields=['-created_at'], name='teams_recent_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["game", "slug"],
                name="uniq_team_slug_per_game",
                condition=~Q(slug=""),
            ),
        ]

    def __str__(self) -> str:
        try:
            return f"{self.name} ({self.tag})"
        except Exception:
            return self.name

    @property
    def members_count(self) -> int:
        return self.memberships.filter(status=TeamMembership.Status.ACTIVE).count()

    def has_member(self, profile) -> bool:
        return self.memberships.filter(
            profile=profile, status=TeamMembership.Status.ACTIVE
        ).exists()

    def ensure_captain_membership(self):
        """Ensure team creator has OWNER membership (replaces old CAPTAIN role)."""
        if self.captain:
            membership, created = TeamMembership.objects.get_or_create(
                team=self,
                profile=self.captain,
                defaults={
                    "role": TeamMembership.Role.OWNER,
                    "status": TeamMembership.Status.ACTIVE,
                },
            )
            # Update permission cache for owner
            if created or membership.role != TeamMembership.Role.OWNER:
                membership.role = TeamMembership.Role.OWNER
                membership.update_permission_cache()
                membership.save()
    
    @property
    def logo_url(self):
        """Get team logo URL or return default"""
        if self.logo:
            return self.logo.url
        return None
    
    @property
    def active_members(self):
        """Get all active team members"""
        return self.memberships.filter(status=TeamMembership.Status.ACTIVE).select_related('profile__user')
    
    @property
    def can_accept_members(self):
        """Check if team can accept more members based on game-specific limits"""
        return self.members_count < self.max_roster_size
    
    @property
    def max_roster_size(self):
        """Get maximum roster size based on game specification"""
        if not self.game:
            return TEAM_MAX_ROSTER  # Fallback to legacy limit
        
        try:
            from apps.common.game_registry.loaders import ROSTER_CONFIGS
            config = ROSTER_CONFIGS.get(self.game, {})
            return config.get('total_max_roster', TEAM_MAX_ROSTER)
        except Exception:
            return TEAM_MAX_ROSTER
    
    @property
    def min_roster_size(self):
        """Get minimum roster size required for tournament registration"""
        if not self.game:
            return 5  # Default minimum
        
        try:
            from apps.common.game_registry.loaders import ROSTER_CONFIGS
            config = ROSTER_CONFIGS.get(self.game, {})
            return config.get('min_starters', 5)
        except Exception:
            return 5
    
    @property
    def roster_limits(self):
        """Get detailed roster limits for this team's game"""
        if not self.game:
            return {
                'max_starters': 5,
                'max_substitutes': 2,
                'max_coach': 1,
                'max_analyst': 0,
                'total_max': TEAM_MAX_ROSTER
            }
        
        try:
            from apps.common.game_registry.loaders import ROSTER_CONFIGS
            config = ROSTER_CONFIGS.get(self.game, {})
            return {
                'max_starters': config.get('max_starters', 5),
                'max_substitutes': config.get('max_substitutes', 2),
                'max_coach': config.get('max_coach', 1),
                'max_analyst': config.get('max_analyst', 0),
                'total_max': config.get('total_max_roster', TEAM_MAX_ROSTER)
            }
        except Exception:
            return {
                'max_starters': 5,
                'max_substitutes': 2,
                'max_coach': 1,
                'max_analyst': 0,
                'total_max': TEAM_MAX_ROSTER
            }
    
    @property
    def display_name(self):
        """Get display name with tag if available"""
        if self.tag and self.name:
            return f"{self.name} ({self.tag})"
        return self.name or f"Team #{self.pk}"
    
    @property
    def members(self):
        """Get all team members (for template compatibility)"""
        from .membership import TeamMembership
        return self.memberships.filter(status=TeamMembership.Status.ACTIVE).select_related('profile__user')
    
    @property
    def captains(self):
        """Get team captains (for template compatibility)"""
        from .membership import TeamMembership
        captain_memberships = self.memberships.filter(
            status=TeamMembership.Status.ACTIVE,
            role=TeamMembership.Role.CAPTAIN
        ).select_related('profile__user')
        return [membership.profile for membership in captain_memberships]
    
    @property
    def effective_captain(self):
        """Get the effective captain - returns captain field if set, otherwise the team owner"""
        if self.captain:
            return self.captain
        
        # If no captain set, default to the owner
        try:
            owner_membership = self.memberships.filter(
                status=TeamMembership.Status.ACTIVE,
                role=TeamMembership.Role.OWNER
            ).first()
            return owner_membership.profile if owner_membership else None
        except:
            return None
    
    def get_absolute_url(self):
        """Get team detail URL"""
        return f"/teams/{self.slug}/" if self.slug else f"/teams/{self.pk}/"
    
    def get_game_display(self):
        """Get canonical game display name from Game Registry"""
        if not self.game:
            return ""
        try:
            from apps.common.game_registry import get_game
            game = get_game(self.game)
            return game.display_name
        except (KeyError, Exception):
            # Fallback to title case
            return self.game.replace('_', ' ').replace('-', ' ').title()
    
    def is_captain(self, profile):
        """Check if profile is team captain (uses effective captain logic)"""
        return self.effective_captain == profile
    
    def is_member(self, profile):
        """Check if profile is an active team member"""
        return self.has_member(profile)
    
    # Social features methods
    def can_user_post(self, user_profile):
        """Check if a user can post to this team."""
        if not self.allow_posts:
            return False
        # Team members can always post
        if self.has_member(user_profile):
            return True
        # Captain can always post
        if self.is_captain(user_profile):
            return True
        return False
    
    def get_follower_count(self):
        """Get the number of followers for this team."""
        return getattr(self, 'followers', None) and self.followers.count() or 0
    
    def is_followed_by(self, user_profile):
        """Check if a user is following this team."""
        return hasattr(self, 'followers') and self.followers.filter(follower=user_profile).exists()
    
    def get_recent_posts(self, limit=5):
        """Get recent published posts."""
        if hasattr(self, 'posts'):
            return self.posts.filter(
                published_at__isnull=False,
                visibility__in=['public', 'followers']
            ).select_related('author__user').prefetch_related('media')[:limit]
        return []
    
    def get_activity_feed(self, limit=10):
        """Get recent activity for this team."""
        if hasattr(self, 'activities'):
            return self.activities.filter(is_public=True)[:limit]
        return []
    
    @property
    def banner_url(self):
        """Get banner image URL or default."""
        if self.banner_image:
            return self.banner_image.url
        return None

    def clean(self):
        # Validate name
        if self.name:
            self.name = self.name.strip()
            if len(self.name) < 3:
                raise ValidationError({"name": "Team name must be at least 3 characters long"})
            if len(self.name) > 50:
                raise ValidationError({"name": "Team name cannot exceed 50 characters"})
        
        # Validate tag
        if self.tag:
            self.tag = self.tag.strip().upper()
            if len(self.tag) < 2:
                raise ValidationError({"tag": "Team tag must be at least 2 characters long"})
            if len(self.tag) > 10:
                raise ValidationError({"tag": "Team tag cannot exceed 10 characters"})
            # Only allow alphanumeric characters for tag
            import re
            if not re.match(r'^[A-Z0-9]+$', self.tag):
                raise ValidationError({"tag": "Team tag can only contain letters and numbers"})
        
        # Auto-slug per game if blank
        try:
            if not getattr(self, "slug", "") and getattr(self, "name", ""):
                base = slugify(self.name)[:60]
                self.slug = base
        except Exception:
            # Fail-soft
            pass
        
        # Update case-insensitive fields
        if self.name:
            self.name_ci = self.name.lower()
        if self.tag:
            self.tag_ci = self.tag.lower()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Guarantee captain is a member; avoid crashing if memberships aren't ready yet
        try:
            self.ensure_captain_membership()
        except Exception:
            pass


class TeamMembership(models.Model):
    class Role(models.TextChoices):
        OWNER = "OWNER", "Team Owner"
        MANAGER = "MANAGER", "Manager"
        COACH = "COACH", "Coach"
        PLAYER = "PLAYER", "Player"
        SUBSTITUTE = "SUBSTITUTE", "Substitute"
        # Legacy support for migration
        CAPTAIN = "CAPTAIN", "Captain (Legacy)"
        SUB = "SUB", "Substitute (Legacy)"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PENDING = "PENDING", "Pending"
        REMOVED = "REMOVED", "Removed"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    profile = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    # Team membership role (organizational)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PLAYER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(default=timezone.now)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ROSTER SLOT SYSTEM: Separate from organizational role
    # Defines the member's position in the active roster (game-specific)
    # ═══════════════════════════════════════════════════════════════════════
    class RosterSlot(models.TextChoices):
        STARTER = "STARTER", "Starting Player"
        SUBSTITUTE = "SUBSTITUTE", "Substitute Player"
        COACH = "COACH", "Coach"
        ANALYST = "ANALYST", "Analyst"
    
    roster_slot = models.CharField(
        max_length=16,
        choices=RosterSlot.choices,
        blank=True,
        null=True,
        help_text="Roster position for tournaments (STARTER, SUBSTITUTE, COACH, ANALYST). Enforces game-specific limits.",
        verbose_name="Roster Slot"
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # DUAL-ROLE SYSTEM: In-Game Role (game-specific tactical role)
    # ═══════════════════════════════════════════════════════════════════════
    player_role = models.CharField(
        max_length=50,
        blank=True,
        default='',
        help_text="In-game tactical role (e.g., Duelist, IGL, AWPer). Game-specific.",
        verbose_name="In-Game Role"
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # NEW: CAPTAIN TITLE SYSTEM
    # ═══════════════════════════════════════════════════════════════════════
    is_captain = models.BooleanField(
        default=False,
        help_text="Team captain for administrative duties (Ban/Pick, check-in). Can be OWNER, MANAGER, PLAYER, or SUBSTITUTE.",
        verbose_name="Captain Title"
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # GRANULAR PERMISSION SYSTEM
    # Owner has all permissions automatically. Managers/Captains can be granted specific permissions.
    # ═══════════════════════════════════════════════════════════════════════
    
    # Tournament & Competition Permissions
    can_register_tournaments = models.BooleanField(
        default=False,
        help_text="Can register team for tournaments and competitions"
    )
    can_withdraw_tournaments = models.BooleanField(
        default=False,
        help_text="Can withdraw team from tournaments"
    )
    can_submit_match_results = models.BooleanField(
        default=False,
        help_text="Can submit match results and scores"
    )
    
    # Roster Management Permissions
    can_invite_members = models.BooleanField(
        default=False,
        help_text="Can send invitations to new members"
    )
    can_remove_members = models.BooleanField(
        default=False,
        help_text="Can remove/kick members from team"
    )
    can_manage_roles = models.BooleanField(
        default=False,
        help_text="Can change member roles (except Owner)"
    )
    can_manage_permissions = models.BooleanField(
        default=False,
        help_text="Can grant/revoke permissions to other members"
    )
    
    # Team Profile & Settings Permissions
    can_edit_team_profile = models.BooleanField(
        default=False,
        help_text="Can edit team name, description, logo, etc."
    )
    can_edit_team_settings = models.BooleanField(
        default=False,
        help_text="Can modify team privacy and settings"
    )
    can_manage_social_links = models.BooleanField(
        default=False,
        help_text="Can update team social media links"
    )
    
    # Content & Community Permissions
    can_create_posts = models.BooleanField(
        default=False,
        help_text="Can create posts on team page"
    )
    can_manage_posts = models.BooleanField(
        default=False,
        help_text="Can edit/delete team posts (including others' posts)"
    )
    can_manage_announcements = models.BooleanField(
        default=False,
        help_text="Can create and manage team announcements"
    )
    
    # Financial Permissions
    can_manage_finances = models.BooleanField(
        default=False,
        help_text="Can manage team finances and entry fees"
    )
    can_view_financial_reports = models.BooleanField(
        default=False,
        help_text="Can view team financial reports and transactions"
    )
    
    # Schedule & Practice Permissions
    can_schedule_practice = models.BooleanField(
        default=False,
        help_text="Can schedule team practice sessions"
    )
    can_manage_schedule = models.BooleanField(
        default=False,
        help_text="Can manage team schedule and calendar"
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # TOURNAMENT ROSTER LOCK SYSTEM (Esports Industry Standard)
    # ═══════════════════════════════════════════════════════════════════════
    locked_for_tournament_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Tournament ID this member is locked for (prevents team changes)"
    )
    locked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the member was locked for tournament"
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the lock expires (tournament end date)"
    )

    class Meta:
        ordering = ("team", "role", "-joined_at")
        unique_together = (("team", "profile"),)
        indexes = [
            models.Index(fields=['team', 'status'], name='teams_member_lookup_idx'),
            models.Index(fields=['profile', 'status'], name='teams_user_teams_idx'),
            models.Index(fields=['team', 'role'], name='teams_role_lookup_idx'),
            models.Index(fields=['locked_for_tournament_id', 'locked_until'], name='teams_tournament_lock_idx'),
        ]
        constraints = [
            # Only one OWNER per team
            models.UniqueConstraint(
                fields=("team",),
                condition=Q(role="OWNER", status="ACTIVE"),
                name="uq_one_active_owner_per_team",
            ),
            # Only one is_captain=True per team (across all roles)
            models.UniqueConstraint(
                fields=("team",),
                condition=Q(is_captain=True, status="ACTIVE"),
                name="uq_one_captain_title_per_team",
            ),
            # Legacy: At most one ACTIVE CAPTAIN per team (for backward compatibility during migration)
            models.UniqueConstraint(
                fields=("team",),
                condition=Q(role="CAPTAIN", status="ACTIVE"),
                name="uq_one_active_captain_per_team",
            ),
        ]

    def __str__(self) -> str:
        captain_badge = "⭐" if self.is_captain else ""
        return f"{captain_badge}{self.profile} @ {self.team} ({self.get_role_display()})"
    
    def is_locked_for_tournament(self) -> bool:
        """Check if member is currently locked for a tournament."""
        if not self.locked_for_tournament_id or not self.locked_until:
            return False
        return timezone.now() < self.locked_until
    
    def lock_for_tournament(self, tournament_id: int, tournament_end_date) -> None:
        """Lock this member for a specific tournament."""
        self.locked_for_tournament_id = tournament_id
        self.locked_at = timezone.now()
        self.locked_until = tournament_end_date
        self.save(update_fields=['locked_for_tournament_id', 'locked_at', 'locked_until'])
    
    def unlock_from_tournament(self) -> None:
        """Remove tournament lock from this member."""
        self.locked_for_tournament_id = None
        self.locked_at = None
        self.locked_until = None
        self.save(update_fields=['locked_for_tournament_id', 'locked_at', 'locked_until'])
    
    def update_permission_cache(self):
        """
        Update permissions based on role.
        OWNER: All permissions automatically
        MANAGER/CAPTAIN: Permissions can be granted individually
        COACH/PLAYER/SUBSTITUTE: No permissions by default (can be granted individually)
        """
        if self.role == self.Role.OWNER:
            # Owner has ALL permissions automatically
            self.can_register_tournaments = True
            self.can_withdraw_tournaments = True
            self.can_submit_match_results = True
            self.can_invite_members = True
            self.can_remove_members = True
            self.can_manage_roles = True
            self.can_manage_permissions = True
            self.can_edit_team_profile = True
            self.can_edit_team_settings = True
            self.can_manage_social_links = True
            self.can_create_posts = True
            self.can_manage_posts = True
            self.can_manage_announcements = True
            self.can_manage_finances = True
            self.can_view_financial_reports = True
            self.can_schedule_practice = True
            self.can_manage_schedule = True
        elif self.role in [self.Role.MANAGER, self.Role.CAPTAIN]:
            # Managers and Captains: Keep existing permissions (can be customized)
            # Default to some basic permissions if this is a new member
            if not self.pk:  # New member
                self.can_create_posts = True
                self.can_schedule_practice = True
                self.can_view_financial_reports = True
        else:
            # COACH, PLAYER, SUBSTITUTE: No default permissions
            # Keep any explicitly granted permissions
            pass
    
    def has_permission(self, permission_name: str) -> bool:
        """
        Check if member has a specific permission.
        Owner always returns True for any permission.
        
        Args:
            permission_name: Name of the permission field (e.g., 'can_register_tournaments')
        
        Returns:
            bool: True if member has permission
        """
        # Owner has all permissions
        if self.role == self.Role.OWNER:
            return True
        
        # Check if the permission field exists and is True
        return getattr(self, permission_name, False)
    
    def grant_permission(self, permission_name: str, save: bool = True):
        """Grant a specific permission to this member."""
        if self.role == self.Role.OWNER:
            return  # Owner already has all permissions
        
        if hasattr(self, permission_name):
            setattr(self, permission_name, True)
            if save:
                self.save(update_fields=[permission_name])
    
    def revoke_permission(self, permission_name: str, save: bool = True):
        """Revoke a specific permission from this member."""
        if self.role == self.Role.OWNER:
            return  # Cannot revoke permissions from Owner
        
        if hasattr(self, permission_name):
            setattr(self, permission_name, False)
            if save:
                self.save(update_fields=[permission_name])
    
    def get_all_permissions(self) -> dict:
        """Get dictionary of all permissions and their status."""
        permission_fields = [
            'can_register_tournaments', 'can_withdraw_tournaments', 'can_submit_match_results',
            'can_invite_members', 'can_remove_members', 'can_manage_roles', 'can_manage_permissions',
            'can_edit_team_profile', 'can_edit_team_settings', 'can_manage_social_links',
            'can_create_posts', 'can_manage_posts', 'can_manage_announcements',
            'can_manage_finances', 'can_view_financial_reports',
            'can_schedule_practice', 'can_manage_schedule'
        ]
        
        return {perm: self.has_permission(perm) for perm in permission_fields}
    
    @property
    def permission_summary(self) -> str:
        """Get a human-readable summary of permissions."""
        if self.role == self.Role.OWNER:
            return "Full Access (Owner)"
        
        granted = [k.replace('can_', '').replace('_', ' ').title() 
                   for k, v in self.get_all_permissions().items() if v]
        
        if not granted:
            return "No special permissions"
        
        return f"{len(granted)} permission(s): {', '.join(granted[:3])}{'...' if len(granted) > 3 else ''}"

    def clean(self):
        # Owner/Captain membership must be ACTIVE
        if self.role in [self.Role.OWNER, self.Role.CAPTAIN] and self.status != self.Status.ACTIVE:
            raise ValidationError({"status": f"{self.get_role_display()} membership must be ACTIVE."})
        
        # is_captain can be True for OWNER, MANAGER, PLAYER, or SUBSTITUTE
        # Removed restriction - OWNER can now be team captain
        if self.is_captain and self.role not in [self.Role.OWNER, self.Role.MANAGER, self.Role.PLAYER, self.Role.SUBSTITUTE]:
            raise ValidationError({
                "is_captain": "Captain title can only be assigned to Owner, Manager, Players, or Substitutes."
            })

        # Enforce: one ACTIVE team per GAME per profile (Part A)
        try:
            team = getattr(self, "team", None)
            prof = getattr(self, "profile", None)
            status = getattr(self, "status", None)
            if team and getattr(team, "game", "") and status == self.Status.ACTIVE and prof:
                conflict = (
                    TeamMembership.objects.filter(
                        profile=prof, status=self.Status.ACTIVE, team__game=team.game
                    )
                    .exclude(team_id=getattr(team, "id", None))
                    .first()
                )
                if conflict:
                    raise ValidationError(
                        {
                            "team": f"You already have an active team for '{team.game}'. "
                                    f"Only one active team per game is allowed."
                        }
                    )
        except ValidationError:
            raise
        except Exception:
            # Fail-soft on unexpected issues
            pass
        
        # ═══════════════════════════════════════════════════════════════════
        # ROSTER SLOT VALIDATION: Enforce game-specific limits
        # ═══════════════════════════════════════════════════════════════════
        if self.roster_slot and self.status == self.Status.ACTIVE and self.team:
            from apps.common.game_registry.loaders import ROSTER_CONFIGS
            
            # Get game-specific limits
            game_config = ROSTER_CONFIGS.get(self.team.game, {})
            
            # Count existing members in this roster slot (exclude self if updating)
            existing_count = TeamMembership.objects.filter(
                team=self.team,
                roster_slot=self.roster_slot,
                status=self.Status.ACTIVE
            ).exclude(pk=self.pk if self.pk else None).count()
            
            # Check against game-specific limits
            limit_exceeded = False
            limit_value = 0
            
            if self.roster_slot == self.RosterSlot.STARTER:
                limit_value = game_config.get('max_starters', 5)
                limit_exceeded = existing_count >= limit_value
            elif self.roster_slot == self.RosterSlot.SUBSTITUTE:
                limit_value = game_config.get('max_substitutes', 2)
                limit_exceeded = existing_count >= limit_value
            elif self.roster_slot == self.RosterSlot.COACH:
                limit_value = game_config.get('max_coach', 1)
                limit_exceeded = existing_count >= limit_value
            elif self.roster_slot == self.RosterSlot.ANALYST:
                limit_value = game_config.get('max_analyst', 0)
                limit_exceeded = existing_count >= limit_value
            
            if limit_exceeded:
                raise ValidationError({
                    "roster_slot": f"Team already has maximum {self.get_roster_slot_display()}s "
                                   f"({limit_value}) for {self.team.game}."
                })
    
    def save(self, *args, **kwargs):
        # Update permission cache before saving
        self.update_permission_cache()
        super().save(*args, **kwargs)

    def promote_to_captain(self):
        """
        Promote this member to captain, demoting any existing active captain,
        and reflect the change on Team.captain.
        """
        with transaction.atomic():
            # Demote any other active captain (prevents unique constraint conflict)
            TeamMembership.objects.filter(
                team=self.team, role=self.Role.CAPTAIN, status=self.Status.ACTIVE
            ).exclude(pk=self.pk).update(role=self.Role.PLAYER)

            # Promote self
            self.role = self.Role.CAPTAIN
            self.status = self.Status.ACTIVE
            self.save(update_fields=["role", "status"])

            # Update team
            self.team.captain = self.profile
            self.team.save(update_fields=["captain"])
    
    # ═══════════════════════════════════════════════════════════════════════
    # DUAL-ROLE SYSTEM: Helper Methods
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_player_role_display(self):
        """
        Get display name for the in-game role.
        Returns the role itself if set, otherwise empty string.
        """
        return self.player_role if self.player_role else ""
    
    def set_player_role(self, role: str):
        """
        Set the in-game role for this member.
        Validates the role is valid for the team's game.
        
        Args:
            role: In-game role name (e.g., 'Duelist', 'IGL')
            
        Raises:
            ValidationError: If role is invalid for the team's game
        """
        from ..game_config import validate_role_for_game, get_game_config
        
        if not role:
            self.player_role = ''
            return
            
        if self.team and self.team.game:
            if not validate_role_for_game(self.team.game, role):
                game_config = get_game_config(self.team.game)
                available_roles = ', '.join(game_config.roles)
                raise ValidationError(
                    f"'{role}' is not a valid role for {game_config.name}. "
                    f"Available roles: {available_roles}"
                )
        
        self.player_role = role
    
    def get_available_player_roles(self):
        """
        Get list of available in-game roles for this member's team.
        Returns empty list if team has no game set.
        
        Returns:
            List of available role names
        """
        from ..game_config import get_available_roles
        
        if not self.team or not self.team.game:
            return []
        
        try:
            return get_available_roles(self.team.game)
        except KeyError:
            return []
    
    def get_role_description(self):
        """
        Get description for this member's in-game role.
        
        Returns:
            Role description string or empty if not set
        """
        from ..game_config import get_role_description
        
        if not self.player_role or not self.team or not self.team.game:
            return ""
        
        try:
            return get_role_description(self.team.game, self.player_role)
        except KeyError:
            return ""
    
    @property
    def is_player_or_sub(self):
        """Check if this member is a player or substitute (can have in-game roles)."""
        return self.role in [self.Role.PLAYER, self.Role.SUB]
    
    @property
    def display_full_role(self):
        """
        Get full role display combining membership role and player role.
        E.g., "Player (Duelist)" or "Substitute (AWPer)" or "Coach"
        """
        base_role = self.get_role_display()
        
        if self.player_role and self.is_player_or_sub:
            return f"{base_role} ({self.player_role})"
        
        return base_role


class TeamInvite(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invites")
    inviter = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.PROTECT,
        related_name="sent_team_invites",
        null=True,
        blank=True,
    )

    # Preferred binding when user already exists
    invited_user = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_invites",
    )
    # Fallback when inviting by email (pre-registration)
    invited_email = models.EmailField(blank=True)

    role = models.CharField(
        max_length=16,
        choices=TeamMembership.Role.choices,
        default=TeamMembership.Role.PLAYER,
    )

    token = models.CharField(
        max_length=36,
        unique=True,
        default=uuid.uuid4,  # serializable callable (avoid lambda)
        editable=False,
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")

    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=['team', 'status'], name='teams_invite_lookup_idx'),
            models.Index(fields=['status', 'expires_at'], name='teams_invite_expire_idx'),
        ]

    def __str__(self) -> str:
        who = self.invited_user or self.invited_email or "unknown"
        return f"Invite({who}) -> {self.team} [{self.status}]"

    # ---- helpers ----
    def is_expired(self) -> bool:
        return bool(self.expires_at and timezone.now() > self.expires_at)

    def mark_expired_if_needed(self):
        if self.status == "PENDING" and self.is_expired():
            self.status = "EXPIRED"
            self.save(update_fields=["status"])

    def clean(self):
        """
        Roster capacity rule:
        - Block creating a *pending* invite when there's only ONE slot left.
        - Also block when active + existing pending already consumes the roster.
        This prevents overbooking while still allowing the final slot to be
        filled by a direct membership (or by accepting an *existing* invite).
        """
        if self.status != "PENDING":
            return

        # Active members currently on the roster
        active = self.team.memberships.filter(
            status=TeamMembership.Status.ACTIVE
        ).count()

        # Other pending invites (exclude self in case we're already saved)
        pending = self.team.invites.filter(status="PENDING").exclude(pk=self.pk).count()

        # 1) If there is exactly one slot left, do NOT allow creating a new pending invite.
        max_roster = self.team.max_roster_size
        if active >= max_roster - 1:
            raise ValidationError(f"Roster has only one slot left; cannot create a new invite (max {max_roster} for {self.team.game}).")

        # 2) If active + pending already fills or exceeds capacity, block too.
        if active + pending >= max_roster:
            raise ValidationError(f"Roster capacity already reserved by existing invites (max {max_roster} for {self.team.game}).")

    def accept(self, profile=None):
        """
        Accept the invite and create/activate a membership.
        If `profile` is not provided, we require `invited_user` to be set.
        """
        if self.status != "PENDING":
            raise ValidationError("Only pending invites can be accepted.")
        self.mark_expired_if_needed()
        if self.status == "EXPIRED":
            raise ValidationError("Invite expired.")

        target = profile or self.invited_user
        if not target:
            raise ValidationError("A user profile is required to accept this invite.")

        with transaction.atomic():
            mem, created = TeamMembership.objects.get_or_create(
                team=self.team,
                profile=target,
                defaults={"role": self.role, "status": TeamMembership.Status.ACTIVE},
            )
            if not created:
                # Reactivate and align role
                mem.status = TeamMembership.Status.ACTIVE
                mem.role = self.role
                mem.save(update_fields=["status", "role"])

            self.invited_user = target
            self.status = "ACCEPTED"
            self.save(update_fields=["invited_user", "status"])

    def decline(self):
        if self.status == "PENDING":
            self.status = "DECLINED"
            self.save(update_fields=["status"])

    def cancel(self):
        if self.status in ("PENDING", "DECLINED"):
            self.status = "CANCELLED"
            self.save(update_fields=["status"])

