# apps/game_efootball/models_registration.py
from __future__ import annotations
from django.db import models


class EfootballSoloInfo(models.Model):
    """
    Extra details captured for eFootball Solo 1v1 registration.
    Linked 1:1 to tournaments.Registration.
    """
    registration = models.OneToOneField(
        "tournaments.Registration",
        on_delete=models.CASCADE,
        related_name="efootball_solo_info",
    )

    # Section 1: Player Information
    full_name = models.CharField(max_length=120)
    ign = models.CharField("In-Game Name", max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40)

    # Section 2: Game & Team Details
    personal_team_name = models.CharField(max_length=120)
    team_strength = models.PositiveIntegerField()
    team_logo = models.ImageField(upload_to="efootball/team_logos/", blank=True, null=True)

    # Section 3: Tournament Agreement
    agree_rules = models.BooleanField(default=False)
    agree_no_tools = models.BooleanField(default=False)
    agree_no_double = models.BooleanField(default=False)

    # Section 4: Payment (captured only; verified manually later)
    payment_method = models.CharField(max_length=32, blank=True)
    payment_reference = models.CharField(max_length=128, blank=True)
    amount_bdt = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = "eFootball Solo Info"
        verbose_name_plural = "eFootball Solo Info"


class EfootballDuoInfo(models.Model):
    """
    Extra details captured for eFootball 2v2 registration (captain + teammate).
    Linked 1:1 to tournaments.Registration.
    """
    registration = models.OneToOneField(
        "tournaments.Registration",
        on_delete=models.CASCADE,
        related_name="efootball_duo_info",
    )

    # Team details
    team_name = models.CharField(max_length=120)
    team_logo = models.ImageField(upload_to="efootball/duo_team_logos/", blank=True, null=True)

    # Captain
    captain_full_name = models.CharField(max_length=120)
    captain_ign = models.CharField(max_length=120)
    captain_email = models.EmailField()
    captain_phone = models.CharField(max_length=40)

    # Teammate
    mate_full_name = models.CharField(max_length=120)
    mate_ign = models.CharField(max_length=120)
    mate_email = models.EmailField()
    mate_phone = models.CharField(max_length=40)

    # Agreements
    agree_consent = models.BooleanField(default=False)
    agree_rules = models.BooleanField(default=False)
    agree_no_tools = models.BooleanField(default=False)
    agree_no_multi_team = models.BooleanField(default=False)

    # Payment (captured; manual verify by admin)
    payment_method = models.CharField(max_length=32)
    payment_reference = models.CharField(max_length=128)
    amount_bdt = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    payment_proof = models.ImageField(upload_to="efootball/duo_payment_proofs/")

    class Meta:
        verbose_name = "eFootball Duo Info"
        verbose_name_plural = "eFootball Duo Info"
