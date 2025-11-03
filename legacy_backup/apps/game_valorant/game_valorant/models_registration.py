# apps/game_valorant/models_registration.py
from __future__ import annotations
from django.db import models


class ValorantTeamInfo(models.Model):
    """
    Team-level info captured at registration time.
    Linked 1:1 to tournaments.Registration.
    """
    registration = models.OneToOneField(
        "tournaments.Registration",
        on_delete=models.CASCADE,
        related_name="valorant_team_info",
    )

    team_name = models.CharField(max_length=80)
    team_tag = models.CharField(max_length=5)
    team_logo = models.ImageField(upload_to="valorant/team_logos/", blank=True, null=True)
    region = models.CharField(max_length=40)  # APAC, EU, NA, LATAM, etc.

    # Agreements
    agree_captain_consent = models.BooleanField(default=False)
    agree_rules = models.BooleanField(default=False)
    agree_no_cheat = models.BooleanField(default=False)
    agree_enforcement = models.BooleanField(default=False)

    # Payment capture (manual verification later)
    payment_method = models.CharField(max_length=32)
    payment_reference = models.CharField(max_length=128)
    amount_bdt = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_proof = models.ImageField(upload_to="valorant/payment_proofs/", blank=True, null=True)

    class Meta:
        verbose_name = "Valorant Team Registration Info"
        verbose_name_plural = "Valorant Team Registration Info"


class ValorantPlayer(models.Model):
    """
    Roster entries captured at registration (snapshot).
    """
    ROLE_CHOICES = (
        ("starter", "Starter"),
        ("sub", "Substitute"),
    )

    team_info = models.ForeignKey(ValorantTeamInfo, on_delete=models.CASCADE, related_name="players")
    full_name = models.CharField(max_length=120)
    riot_id = models.CharField(max_length=32)         # without tagline (e.g., DeltaCrownPro)
    riot_tagline = models.CharField(max_length=16)    # e.g., APAC/NA1 tag
    discord = models.CharField(max_length=64)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
