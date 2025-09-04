# apps/tournaments/models/tournament_settings.py
from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class TournamentSettings(models.Model):
    """
    Per-tournament core settings shared across games.
    Includes registration window, schedule, entry/prize, media/links,
    advanced toggles, and manual-payment receiving numbers (bKash/Nagad/Rocket).
    """

    # ---------- enums ----------
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

    class GatewayType(models.TextChoices):
        PERSONAL = "personal", _("Personal")
        MERCHANT = "merchant", _("Merchant")
        AGENT = "agent", _("Agent")

    # ---------- relations ----------
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="settings",
    )

    # ---------- basics ----------
    tournament_type = models.CharField(
        max_length=2, choices=TournamentType.choices, default=TournamentType.SINGLE_ELIM
    )
    description = models.TextField(blank=True)

    # ---------- schedule ----------
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    reg_open_at = models.DateTimeField(null=True, blank=True)
    reg_close_at = models.DateTimeField(null=True, blank=True)

    # ---------- team size & entry ----------
    min_team_size = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    max_team_size = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1)])
    entry_fee_bdt = models.PositiveIntegerField(null=True, blank=True)

    # ---------- prize ----------
    prize_pool_bdt = models.PositiveIntegerField(null=True, blank=True)
    prize_distribution_text = models.TextField(blank=True)
    prize_type = models.CharField(
        max_length=16, choices=PrizeType.choices, default=PrizeType.CASH
    )

    # ---------- media & docs ----------
    banner = models.ImageField(upload_to="tournaments/banners/", null=True, blank=True)
    rules_pdf = models.FileField(upload_to="tournaments/rules/", null=True, blank=True)

    # ---------- streams & comms ----------
    stream_facebook_url = models.URLField(blank=True)
    stream_youtube_url = models.URLField(blank=True)
    discord_url = models.URLField(blank=True)

    # ---------- advanced toggles ----------
    invite_only = models.BooleanField(default=False)
    auto_check_in = models.BooleanField(default=False)
    bracket_visibility = models.CharField(
        max_length=16, choices=BracketVisibility.choices, default=BracketVisibility.PUBLIC
    )
    auto_schedule = models.BooleanField(default=False)
    custom_format_json = models.JSONField(null=True, blank=True)
    payment_gateway_enabled = models.BooleanField(
        default=False,
        help_text="Leave OFF for manual verification (bKash/Nagad/Rocket).",
    )
    region_lock = models.BooleanField(default=False)

    # Optional check-in window relative to start time (minutes)
    check_in_open_mins = models.PositiveIntegerField(
        null=True, blank=True, help_text="Minutes before start when check-in opens (e.g., 60)."
    )
    check_in_close_mins = models.PositiveIntegerField(
        null=True, blank=True, help_text="Minutes before start when check-in closes (e.g., 15)."
    )

    # ---------- manual payment receiving numbers (organizer) ----------
    bkash_receive_type = models.CharField(
        max_length=16, choices=GatewayType.choices, default=GatewayType.PERSONAL, blank=True
    )
    bkash_receive_number = models.CharField(
        max_length=32, blank=True, help_text="Organizer’s bKash account number to receive fees."
    )

    nagad_receive_type = models.CharField(
        max_length=16, choices=GatewayType.choices, default=GatewayType.PERSONAL, blank=True
    )
    nagad_receive_number = models.CharField(
        max_length=32, blank=True, help_text="Organizer’s Nagad account number to receive fees."
    )

    rocket_receive_type = models.CharField(
        max_length=16, choices=GatewayType.choices, default=GatewayType.AGENT, blank=True
    )
    rocket_receive_number = models.CharField(
        max_length=32, blank=True, help_text="Organizer’s Rocket account number to receive fees."
    )

    bank_instructions = models.TextField(
        blank=True,
        help_text="Optional bank transfer instructions (bank name, branch, account title & number).",
    )

    # ---------- meta ----------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---------- helpers ----------
    def clean(self):
        from django.core.exceptions import ValidationError

        # min <= max
        if self.min_team_size and self.max_team_size:
            if self.min_team_size > self.max_team_size:
                raise ValidationError({"max_team_size": _("Max team size must be ≥ min team size.")})

    def __str__(self) -> str:
        return f"Settings for {getattr(self.tournament, 'name', self.tournament_id)}"

    class Meta:
        verbose_name = "Tournament Settings"
        verbose_name_plural = "Tournament Settings"
