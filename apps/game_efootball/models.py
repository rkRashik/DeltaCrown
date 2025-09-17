# apps/game_efootball/models.py
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field


class EfootballConfig(models.Model):
    """Per-tournament eFootball configuration. All fields are optional."""

    class MatchFormat(models.TextChoices):
        BO1 = "BO1", _("Best of 1")
        BO2 = "BO2", _("Best of 2")
        BO3 = "BO3", _("Best of 3")
        BO5 = "BO5", _("Best of 5")

    # ----- Relationship -----
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="efootball_config",
    )

    # ----- Match format -----
    format_type = models.CharField(
        max_length=3,
        choices=MatchFormat.choices,
        null=True,
        blank=True,
        help_text="Override the default match format (e.g., BO1, BO3).",
    )
    match_duration_min = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Approximate duration per match in minutes.",
    )
    match_time_limit = models.DurationField(null=True, blank=True)
    team_strength_cap = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional cap on overall team strength (e.g., 2700).",
    )

    # ----- Rules -----
    allow_extra_time = models.BooleanField(null=True, blank=True)
    allow_penalties = models.BooleanField(null=True, blank=True)
    additional_rules_richtext = CKEditor5Field("Additional rules", config_name="default", blank=True, null=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        vconf = getattr(self.tournament, "valorant_config", None)
        if vconf and getattr(vconf, "pk", None):
            raise ValidationError("This tournament already has a Valorant config. Remove it first.")

    def __str__(self):
        name = getattr(self.tournament, "name", None)
        return f"eFootball Config for {name or self.tournament_id}"

    class Meta:
        verbose_name = "eFootball Config"
        verbose_name_plural = "eFootball Configs"
