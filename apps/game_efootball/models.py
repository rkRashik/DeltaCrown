from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from apps.tournaments.models import Tournament

EFOOTBALL_FORMAT = [
    ("BO1", "Best of 1"),
    ("BO3", "Best of 3"),
    ("BO5", "Best of 5"),
]

class EfootballConfig(models.Model):
    tournament = models.OneToOneField(
        Tournament, on_delete=models.CASCADE, related_name="efootball_config"
    )
    format_type = models.CharField(max_length=3, choices=EFOOTBALL_FORMAT, default="BO1")
    match_duration_min = models.PositiveIntegerField(default=10)  # typical 8–12 mins
    team_strength_cap = models.PositiveIntegerField(null=True, blank=True)  # e.g., 2700
    allow_extra_time = models.BooleanField(default=False)
    allow_penalties = models.BooleanField(default=True)

    # CKEditor-5 (replacement for classic ckeditor)
    additional_rules_richtext = CKEditor5Field("Additional rules", config_name="default", blank=True)

    def clean(self):
        # Enforce single game config per tournament (ahead of Part 4 inline validation)
        from django.core.exceptions import ValidationError
        vconf = getattr(self.tournament, "valorant_config", None)
        if vconf and vconf.pk:
            raise ValidationError("This tournament already has a Valorant config. Remove it first.")

    def __str__(self):
        return f"eFootball Config for {self.tournament.name}"

    class Meta:
        verbose_name = "eFootball Config"
        verbose_name_plural = "eFootball Configs"
