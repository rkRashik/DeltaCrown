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

# Import GAME_CHOICES from game_config
from ..game_config import GAME_CHOICES

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

    # Game association (Part A)
    game = models.CharField(
        max_length=20,
        choices=GAME_CHOICES,
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
        if self.captain:
            TeamMembership.objects.get_or_create(
                team=self,
                profile=self.captain,
                defaults={
                    "role": TeamMembership.Role.CAPTAIN,
                    "status": TeamMembership.Status.ACTIVE,
                },
            )
    
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
        """Check if team can accept more members"""
        return self.members_count < TEAM_MAX_ROSTER
    
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
    
    def get_absolute_url(self):
        """Get team detail URL"""
        return f"/teams/{self.slug}/" if self.slug else f"/teams/{self.pk}/"
    
    def is_captain(self, profile):
        """Check if profile is team captain"""
        return self.captain == profile
    
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
        CAPTAIN = "CAPTAIN", "Captain"
        MANAGER = "MANAGER", "Manager"
        PLAYER = "PLAYER", "Player"
        SUB = "SUB", "Substitute"

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
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PLAYER)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("team", "role", "-joined_at")
        unique_together = (("team", "profile"),)
        indexes = [
            models.Index(fields=['team', 'status'], name='teams_member_lookup_idx'),
            models.Index(fields=['profile', 'status'], name='teams_user_teams_idx'),
        ]
        constraints = [
            # At most one ACTIVE CAPTAIN per team
            models.UniqueConstraint(
                fields=("team",),
                condition=Q(role="CAPTAIN", status="ACTIVE"),
                name="uq_one_active_captain_per_team",
            )
        ]

    def __str__(self) -> str:
        return f"{self.profile} @ {self.team} ({self.role})"

    def clean(self):
        # Captain membership must be ACTIVE
        if self.role == self.Role.CAPTAIN and self.status != self.Status.ACTIVE:
            raise ValidationError({"status": "Captain membership must be ACTIVE."})

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
        if active >= TEAM_MAX_ROSTER - 1:
            raise ValidationError("Roster has only one slot left; cannot create a new invite.")

        # 2) If active + pending already fills or exceeds capacity, block too.
        if active + pending >= TEAM_MAX_ROSTER:
            raise ValidationError("Roster capacity already reserved by existing invites.")

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

