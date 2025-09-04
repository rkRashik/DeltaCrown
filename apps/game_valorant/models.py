# apps/game_valorant/models.py
from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

# Prefer Postgres ArrayField when available; fall back to JSONField otherwise
try:
    from django.contrib.postgres.fields import ArrayField as _ArrayField  # available even if DB != PG
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
    """
    Per-tournament Valorant rules.
    Uses ArrayField on PostgreSQL; JSON list elsewhere (MySQL-friendly).
    Mutually exclusive with eFootball config on the same tournament.
    """
    tournament = models.OneToOneField(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="valorant_config",
    )

    best_of = models.CharField(max_length=3, choices=VALORANT_BO, default="BO3")
    rounds_per_match = models.PositiveIntegerField(
        default=13, validators=[MinValueValidator(11), MaxValueValidator(16)]
    )

    # Map pool (PG ArrayField if available + PG engine; else JSON list)
    if _ArrayField and _using_postgres():
        map_pool = _ArrayField(models.CharField(max_length=30), default=list, blank=True)
    else:
        map_pool = models.JSONField(default=list, blank=True, help_text="List of selected maps")

    # Optional controls
    match_duration_limit = models.DurationField(null=True, blank=True)
    overtime_rules = models.CharField(
        max_length=120, blank=True, help_text="e.g. ‘MR3 OT, win by 2’"
    )

    # Long-form extras (rules/veto/policies)
    additional_rules_richtext = CKEditor5Field("Additional rules", config_name="default", blank=True)

    # Advanced toggles (future-proof; all default off)
    regional_lock = models.BooleanField(default=False)
    live_scoreboard = models.BooleanField(default=False)
    sponsor_integration = models.BooleanField(default=False)
    community_voting = models.BooleanField(default=False)
    livestream_customization = models.BooleanField(default=False)

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
