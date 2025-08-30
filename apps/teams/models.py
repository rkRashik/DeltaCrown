# apps/teams/models.py
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError

def team_logo_path(instance, filename):
    return f"team_logos/{instance.id}/{filename}"

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tag = models.CharField(max_length=10, unique=True)
    logo = models.ImageField(upload_to="team_logos/", blank=True, null=True)
    captain = models.ForeignKey('user_profile.UserProfile', on_delete=models.CASCADE, related_name="captain_of")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def __str__(self):
        return f"{self.tag} — {self.name}"


class TeamMembership(models.Model):
    ROLE_CHOICES = [("captain", "Captain"), ("player", "Player"), ("substitute", "Substitute")]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey('user_profile.UserProfile', on_delete=models.CASCADE, related_name="team_memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="player")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "user")
        indexes = [
            models.Index(fields=["team", "role"]),
        ]

    def __str__(self):
        return f"{self.user.display_name} - {self.role} of {self.team.name}"


# Global roster limits (tweakable; per-game rules come later during tournament registration)
TEAM_MAX_ROSTER = 8  # captain + players + subs

class TeamInvite(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]

    team = models.ForeignKey("Team", on_delete=models.CASCADE, related_name="invites")
    invited_user = models.ForeignKey('user_profile.UserProfile', on_delete=models.CASCADE, related_name="team_invites")
    invited_by = models.ForeignKey('user_profile.UserProfile', on_delete=models.CASCADE, related_name="sent_team_invites")
    message = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")
    token = models.CharField(max_length=36, unique=True)  # uuid4 string
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)  # optional

    class Meta:
        unique_together = [("team", "invited_user")]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["invited_user", "status"]),
        ]

    def clean(self):
        # Captain can't invite beyond max roster
        current_size = self.team.memberships.count()
        if self.status == "PENDING" and current_size >= TEAM_MAX_ROSTER:
            raise ValidationError("Roster is full; cannot invite more members.")

    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at

    def mark_expired_if_needed(self):
        if self.status == "PENDING" and self.is_expired():
            self.status = "EXPIRED"
            self.save(update_fields=["status"])