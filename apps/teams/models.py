from django.db import models
from apps.user_profile.models import UserProfile

def team_logo_path(instance, filename):
    return f"team_logos/{instance.id}/{filename}"

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tag  = models.CharField(max_length=10, unique=True)
    logo = models.ImageField(upload_to=team_logo_path, blank=True, null=True)
    captain = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="captain_of")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["name"]), models.Index(fields=["tag"])]

    def __str__(self):
        return f"{self.tag} — {self.name}"

class TeamMembership(models.Model):
    ROLE_CHOICES = [("captain", "Captain"), ("player", "Player"), ("sub", "Substitute")]

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="team_memberships")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="player")
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("team", "user")
        indexes = [models.Index(fields=["team", "role"])]
