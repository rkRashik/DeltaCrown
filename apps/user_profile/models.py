from django.db import models
from django.conf import settings

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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=80)
    region = models.CharField(max_length=2, choices=REGION_CHOICES, default="BD")
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)
    bio = models.TextField(blank=True)

    youtube_link = models.URLField(blank=True)
    twitch_link = models.URLField(blank=True)
    preferred_games = models.JSONField(default=list, blank=True, null=True)
    discord_id = models.CharField(max_length=64, blank=True)
    riot_id = models.CharField(max_length=100, blank=True)
    efootball_id = models.CharField(max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    is_private = models.BooleanField(default=False, help_text="Hide entire profile from public.")
    show_email = models.BooleanField(default=False, help_text="Allow showing my email on public profile.")
    show_phone = models.BooleanField(default=False, help_text="Allow showing my phone on public profile.")
    show_socials = models.BooleanField(default=True, help_text="Allow showing my social links/IDs on public profile.")

    class Meta:
        indexes = [models.Index(fields=["region"])]
        verbose_name = "User Profile"

    def __str__(self):
        return self.display_name or getattr(self.user, "username", str(self.user_id))
