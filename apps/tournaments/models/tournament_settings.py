# apps/tournaments/models/tournament_settings.py
from __future__ import annotations

from typing import Optional

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class TournamentSettings(models.Model):
    """Per-tournament configuration shared across games."""

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

    # ----- Core relationship -----
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="settings",
    )

    # ----- Overview -----
    tournament_type = models.CharField(
        max_length=2,
        choices=TournamentType.choices,
        default=TournamentType.SINGLE_ELIM,
        null=True,
        blank=True,
        help_text="Bracket format to use if no custom format is supplied.",
    )
    description = models.TextField(blank=True, null=True)

    # ----- Schedule -----
    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)
    reg_open_at = models.DateTimeField(null=True, blank=True)
    reg_close_at = models.DateTimeField(null=True, blank=True)

    round_duration_mins = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Target round duration in minutes for auto scheduling.",
    )
    round_gap_mins = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Gap between rounds in minutes for auto scheduling.",
    )
    # ----- Teams & Entry -----
    min_team_size = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Minimum players per team (optional).",
    )
    max_team_size = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Maximum players per team (optional).",
    )
    allow_substitutes = models.BooleanField(
        null=True,
        blank=True,
        help_text="Allow teams to register substitute players.",
    )
    entry_fee_bdt = models.PositiveIntegerField(null=True, blank=True)

    # ----- Prizing -----
    prize_pool_bdt = models.PositiveIntegerField(null=True, blank=True)
    prize_distribution_text = models.TextField(blank=True, null=True)
    prize_type = models.CharField(
        max_length=16,
        choices=PrizeType.choices,
        null=True,
        blank=True,
        help_text="Type of prize being offered.",
    )

    # ----- Media -----
    banner = models.ImageField(upload_to="tournaments/banners/", null=True, blank=True)
    rules_pdf = models.FileField(upload_to="tournaments/rules/", null=True, blank=True)

    # ----- Streams & Communication -----
    stream_facebook_url = models.URLField(
        null=True,
        blank=True,
    )
    stream_youtube_url = models.URLField(
        null=True,
        blank=True,
    )
    discord_url = models.URLField(
        null=True,
        blank=True,
    )

    # ----- Toggles -----
    invite_only = models.BooleanField(null=True, blank=True)
    auto_check_in = models.BooleanField(null=True, blank=True)
    bracket_visibility = models.CharField(
        max_length=16,
        choices=BracketVisibility.choices,
        default=BracketVisibility.PUBLIC,
        null=True,
        blank=True,
    )
    automatic_scheduling_enabled = models.BooleanField(
        null=True,
        blank=True,
        help_text="Automate match scheduling based on start time and durations.",
    )
    custom_format_enabled = models.BooleanField(
        null=True,
        blank=True,
        help_text="Enable custom format JSON to override bracket settings.",
    )
    custom_format_json = models.JSONField(null=True, blank=True)
    payment_gateway_enabled = models.BooleanField(
        null=True,
        blank=True,
        help_text="Leave OFF for manual verification (bKash/Nagad/Rocket).",
    )
    region_lock = models.BooleanField(null=True, blank=True)

    check_in_open_mins = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minutes before start when check-in opens (e.g., 60).",
    )
    check_in_close_mins = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minutes before start when check-in closes (e.g., 15).",
    )

    # ----- Manual payment receiving numbers -----
    bkash_receive_type = models.CharField(
        max_length=16,
        choices=GatewayType.choices,
        null=True,
        blank=True,
    )
    bkash_receive_number = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Organizer's bKash account number to receive fees.",
    )

    nagad_receive_type = models.CharField(
        max_length=16,
        choices=GatewayType.choices,
        null=True,
        blank=True,
    )
    nagad_receive_number = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Organizer's Nagad account number to receive fees.",
    )

    rocket_receive_type = models.CharField(
        max_length=16,
        choices=GatewayType.choices,
        null=True,
        blank=True,
    )
    rocket_receive_number = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        help_text="Organizer's Rocket account number to receive fees.",
    )

    bank_instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Optional bank transfer instructions (bank name, branch, account title & number).",
    )

    # ----- Meta -----
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def auto_schedule(self) -> Optional[bool]:
        """Backward compatibility alias for legacy templates/admin."""
        return self.automatic_scheduling_enabled

    @auto_schedule.setter
    def auto_schedule(self, value: Optional[bool]) -> None:
        self.automatic_scheduling_enabled = value

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.min_team_size and self.max_team_size:
            if self.min_team_size > self.max_team_size:
                raise ValidationError({"max_team_size": _("Max team size must be at least the minimum team size.")})

    def __str__(self) -> str:
        return f"Settings for {getattr(self.tournament, 'name', self.tournament_id)}"

    class Meta:
        verbose_name = "Tournament Settings"
        verbose_name_plural = "Tournament Settings"

