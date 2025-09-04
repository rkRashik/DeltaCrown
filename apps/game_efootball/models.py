# apps/game_efootball/models.py
from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_ckeditor_5.fields import CKEditor5Field


class EfootballConfig(models.Model):
    """
    eFootball tournament rules.
    Mutually exclusive with Valorant config on the same tournament.
    """
    class MatchFormat(models.TextChoices):
        BO1 = "BO1", _("Best of 1")
        BO2 = "BO2", _("Best of 2")
        BO3 = "BO3", _("Best of 3")
        BO5 = "BO5", _("Best of 5")  # keep for flexibility

    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="efootball_config",
    )

    format_type = models.CharField(max_length=3, choices=MatchFormat.choices, default=MatchFormat.BO1)
    match_duration_min = models.PositiveIntegerField(default=10, help_text="Per match, e.g., 10 minutes")
    match_time_limit = models.DurationField(null=True, blank=True)
    team_strength_cap = models.PositiveIntegerField(null=True, blank=True, help_text="e.g., 2700–3000")

    allow_extra_time = models.BooleanField(default=False)
    allow_penalties = models.BooleanField(default=True)

    additional_rules_richtext = CKEditor5Field("Additional rules", config_name="default", blank=True)

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
