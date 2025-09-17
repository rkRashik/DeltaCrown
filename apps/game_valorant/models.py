# apps/game_valorant/models.py
from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

try:
    from django.contrib.postgres.fields import ArrayField as _ArrayField
except Exception:  # pragma: no cover
    _ArrayField = None


def _using_postgres() -> bool:
    try:
        return "postgresql" in settings.DATABASES["default"]["ENGINE"]
    except Exception:
        return False


VALORANT_BO = [
    ("BO1", "Best of 1"),
    ("BO2", "Best of 2"),
    ("BO3", "Best of 3"),
    ("BO5", "Best of 5"),
]

DEFAULT_MAP_POOL = [
    "Ascent", "Bind", "Haven", "Lotus", "Split", "Sunset", "Icebox", "Abyss", "Breeze",
]


class ValorantConfig(models.Model):
    """Per-tournament Valorant configuration with optional knobs."""

    # ----- Relationship -----
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="valorant_config",
    )

    # ----- Match rules -----
    best_of = models.CharField(
        max_length=3,
        choices=VALORANT_BO,
        null=True,
        blank=True,
    )
    rounds_per_match = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(11), MaxValueValidator(16)],
    )

    if _ArrayField and _using_postgres():
        map_pool = _ArrayField(models.CharField(max_length=30), default=list, blank=True, null=True)
    else:
        map_pool = models.JSONField(default=list, blank=True, null=True, help_text="List of selected maps")

    match_duration_limit = models.DurationField(null=True, blank=True)
    overtime_rules = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        help_text="e.g. MR3 OT, win by 2",
    )

    # ----- Narrative / Content -----
    additional_rules_richtext = CKEditor5Field("Additional rules", config_name="default", blank=True, null=True)

    # ----- Advanced toggles -----
    regional_lock = models.BooleanField(null=True, blank=True)
    live_scoreboard = models.BooleanField(null=True, blank=True)
    sponsor_integration = models.BooleanField(null=True, blank=True)
    community_voting = models.BooleanField(null=True, blank=True)
    livestream_customization = models.BooleanField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.map_pool:
            self.map_pool = list(DEFAULT_MAP_POOL)
        super().save(*args, **kwargs)

    def clean(self):
        from django.core.exceptions import ValidationError

        econf = getattr(self.tournament, "efootball_config", None)
        if econf and getattr(econf, "pk", None):
            raise ValidationError("This tournament already has an eFootball config. Remove it first.")

    def __str__(self):
        name = getattr(self.tournament, "name", None)
        return f"Valorant Config for {name or self.tournament_id}"

    class Meta:
        verbose_name = "Valorant Config"
        verbose_name_plural = "Valorant Configs"
