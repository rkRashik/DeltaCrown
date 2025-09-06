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

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q, UniqueConstraint
from django.utils import timezone


# Global roster ceiling (captain + players + subs)
TEAM_MAX_ROSTER = 8


def team_logo_path(instance, filename):
    # Keep a stable folder structure; id may be None on first save
    pk = getattr(instance, "id", None) or "new"
    return f"team_logos/{pk}/{filename}"


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tag = models.CharField(max_length=10, unique=True)
    logo = models.ImageField(upload_to=team_logo_path, blank=True, null=True)
    # Game association (Part A)
    GAME_CHOICES = (
        ('efootball', 'eFootball'),
        ('valorant', 'Valorant'),
    )
    game = models.CharField(
        max_length=20, choices=GAME_CHOICES, blank=True, default='',
        help_text='Which game this team competes in (blank for legacy teams).'
    )

    # Use your existing UserProfile
    captain = models.ForeignKey(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="captain_of",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        try:
            return f"{self.name} ({self.tag})"
        except Exception:
            return self.name

    # ---- convenience ----
    @property
    def members_count(self) -> int:
        return self.memberships.filter(status=TeamMembership.Status.ACTIVE).count()

    def has_member(self, profile) -> bool:
        return self.memberships.filter(profile=profile, status=TeamMembership.Status.ACTIVE).exists()

    def ensure_captain_membership(self):
        TeamMembership.objects.get_or_create(
            team=self,
            profile=self.captain,
            defaults={"role": TeamMembership.Role.CAPTAIN, "status": TeamMembership.Status.ACTIVE},
        )

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
        constraints = [
            # At most one ACTIVE CAPTAIN per team
            UniqueConstraint(
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
            team = getattr(self, 'team', None)
            prof = getattr(self, 'profile', None)
            status = getattr(self, 'status', None)
            if team and getattr(team, 'game', '') and status == self.Status.ACTIVE and prof:
                conflict = (
                    TeamMembership.objects
                    .filter(profile=prof, status=self.Status.ACTIVE, team__game=team.game)
                    .exclude(team_id=getattr(team, 'id', None))
                    .first()
                )
                if conflict:
                    from django.core.exceptions import ValidationError as _VE
                    raise _VE({'team': f"You already have an active team for '{team.game}'. Only one active team per game is allowed."})
        except Exception:
            # Fail-soft
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

    role = models.CharField(max_length=16, choices=TeamMembership.Role.choices, default=TeamMembership.Role.PLAYER)

    token = models.CharField(
        max_length=36,
        unique=True,
        default=uuid.uuid4,   # serializable callable (avoid lambda)
        editable=False,
    )
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")

    expires_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

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

    def accept(self, profile: Optional["user_profile.UserProfile"] = None):
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
