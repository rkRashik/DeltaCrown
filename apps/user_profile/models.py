from django.db import models
from django.contrib.auth.models import User

REGION_CHOICES = [
    ("BD", "Bangladesh"),
    ("SA", "South Asia"),
    ("AS", "Asia (Other)"),
    ("EU", "Europe"),
    ("NA", "North America"),
]

def user_avatar_path(instance, filename):
    return f"user_avatars/{instance.user_id}/{filename}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80)
    region = models.CharField(max_length=2, choices=REGION_CHOICES, default="BD")
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)

    # Social / game IDs (nullable)
    discord_id = models.CharField(max_length=64, blank=True)
    riot_id = models.CharField(max_length=100, blank=True)        # Valorant (later)
    efootball_id = models.CharField(max_length=100, blank=True)   # eFootball (later)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["region"])]
        verbose_name = "User Profile"

    def __str__(self):
        return self.display_name or self.user.username
