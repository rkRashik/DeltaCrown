
# apps/teams/models/presets.py
from __future__ import annotations
from django.db import models

class EfootballTeamPreset(models.Model):
    profile = models.ForeignKey("user_profile.UserProfile", on_delete=models.CASCADE, related_name="efootball_presets")
    name = models.CharField(max_length=120)
    team_name = models.CharField(max_length=120, blank=True, default="")
    team_logo = models.ImageField(upload_to="presets/efootball/team_logos/", blank=True, null=True)

    # Duo snapshot
    captain_name = models.CharField(max_length=120, blank=True, default="")
    captain_ign = models.CharField(max_length=120, blank=True, default="")
    mate_name = models.CharField(max_length=120, blank=True, default="")
    mate_ign = models.CharField(max_length=120, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "eFootball Team Preset"
        verbose_name_plural = "eFootball Team Presets"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} (eFootball)"


class ValorantTeamPreset(models.Model):
    profile = models.ForeignKey("user_profile.UserProfile", on_delete=models.CASCADE, related_name="valorant_presets")
    name = models.CharField(max_length=120)
    team_name = models.CharField(max_length=120, blank=True, default="")
    team_tag = models.CharField(max_length=10, blank=True, default="")
    team_logo = models.ImageField(upload_to="presets/valorant/team_logos/", blank=True, null=True)
    banner_image = models.ImageField(upload_to="presets/valorant/banners/", blank=True, null=True)
    region = models.CharField(max_length=48, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Valorant Team Preset"
        verbose_name_plural = "Valorant Team Presets"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} (Valorant)"


class ValorantPlayerPreset(models.Model):
    preset = models.ForeignKey("teams.ValorantTeamPreset", on_delete=models.CASCADE, related_name="players")
    in_game_name = models.CharField(max_length=120, blank=True, default="")
    riot_id = models.CharField(max_length=120, blank=True, default="", help_text="Riot ID#Tagline")
    discord = models.CharField(max_length=120, blank=True, default="")
    role = models.CharField(max_length=24, blank=True, default="PLAYER", help_text="CAPTAIN/PLAYER/SUB")

    class Meta:
        verbose_name = "Valorant Player Preset"
        verbose_name_plural = "Valorant Player Presets"

    def __str__(self) -> str:
        return f"{self.in_game_name or self.riot_id or 'player'}"
