from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField  # PostgreSQL
from django_ckeditor_5.fields import CKEditor5Field
from apps.tournaments.models import Tournament

VALORANT_BO = [("BO1", "Best of 1"), ("BO3", "Best of 3"), ("BO5", "Best of 5")]

DEFAULT_MAP_POOL = [
    "Ascent", "Bind", "Haven", "Lotus", "Split", "Sunset", "Icebox"
]

class ValorantConfig(models.Model):
    tournament = models.OneToOneField(
        Tournament, on_delete=models.CASCADE, related_name="valorant_config"
    )
    best_of = models.CharField(max_length=3, choices=VALORANT_BO, default="BO3")
    rounds_per_match = models.PositiveIntegerField(
        default=13, validators=[MinValueValidator(11), MaxValueValidator(16)]
    )

    # Using Postgres ArrayField (portable to JSONField if DB changes)
    map_pool = ArrayField(models.CharField(max_length=30), default=list, blank=True)

    overtime_rules = models.CharField(
        max_length=120, blank=True, help_text="Short text like ‘MR3 OT, win by 2’"
    )

    # CKEditor-5 (replacement for classic ckeditor)
    additional_rules_richtext = CKEditor5Field("Additional rules", config_name="default", blank=True)

    def save(self, *args, **kwargs):
        # Default a sane pool if none set
        if not self.map_pool:
            self.map_pool = DEFAULT_MAP_POOL
        super().save(*args, **kwargs)

    def clean(self):
        # Enforce single game config per tournament (ahead of Part 4 inline validation)
        from django.core.exceptions import ValidationError
        econf = getattr(self.tournament, "efootball_config", None)
        if econf and econf.pk:
            raise ValidationError("This tournament already has an eFootball config. Remove it first.")

    def __str__(self):
        return f"Valorant Config for {self.tournament.name}"
