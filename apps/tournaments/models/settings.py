# apps/tournaments/models/settings.py
from __future__ import annotations
from django.db import models
from django.utils.translation import gettext_lazy as _

class TournamentSettings(models.Model):
    class TournamentType(models.TextChoices):
        SINGLE_ELIM = "SE", _("Single Elimination")
        DOUBLE_ELIM = "DE", _("Double Elimination")
        ROUND_ROBIN = "RR", _("Round Robin")
        SWISS = "SW", _("Swiss")
        CUSTOM = "CU", _("Custom Format")

    class PrizeType(models.TextChoices):
        CASH = "cash", _("Cash Prize")
        GIFT_CARDS = "gift_cards", _("Gift Cards")
        GEAR = "gear", _("Gaming Gear")
        SPONSORED = "sponsored", _("Sponsored Prizes")

    class BracketVisibility(models.TextChoices):
        PUBLIC = "public", _("Public")
        CAPTAINS = "captains", _("Team Captains Only")

    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="settings",
    )

    # Basics
    tournament_type = models.CharField(
        max_length=2, choices=TournamentType.choices, default=TournamentType.SINGLE_ELIM
    )
    description = models.TextField(blank=True)

    # Schedule
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    reg_open_at = models.DateTimeField(null=True, blank=True)
    reg_close_at = models.DateTimeField(null=True, blank=True)

    # Team size & entry
    min_team_size = models.PositiveSmallIntegerField(default=1)
    max_team_size = models.PositiveSmallIntegerField(default=1)
    entry_fee_bdt = models.PositiveIntegerField(null=True, blank=True)

    # Prize
    prize_pool_bdt = models.PositiveIntegerField(null=True, blank=True)
    prize_distribution_text = models.TextField(blank=True)
    prize_type = models.CharField(
        max_length=16, choices=PrizeType.choices, default=PrizeType.CASH
    )

    # Media & docs
    banner = models.ImageField(upload_to="tournaments/banners/", null=True, blank=True)
    rules_pdf = models.FileField(upload_to="tournaments/rules/", null=True, blank=True)

    # Streams & comms
    stream_facebook_url = models.URLField(blank=True)
    stream_youtube_url = models.URLField(blank=True)
    discord_url = models.URLField(blank=True)

    # Advanced toggles
    invite_only = models.BooleanField(default=False)
    auto_check_in = models.BooleanField(default=False)
    bracket_visibility = models.CharField(
        max_length=16, choices=BracketVisibility.choices, default=BracketVisibility.PUBLIC
    )
    auto_schedule = models.BooleanField(default=False)
    custom_format_json = models.JSONField(null=True, blank=True)
    payment_gateway_enabled = models.BooleanField(default=False)

    # Meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Settings for {self.tournament}"
