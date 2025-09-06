# apps/tournaments/models/tournament.py
from django.db import models
from django.utils.text import slugify

from .paths import tournament_banner_path, rules_pdf_path  # rules_pdf_path kept for compat if used anywhere


# Module-level enum to avoid indentation bleed inside the model class
class TournamentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"


class Tournament(models.Model):
    class Game(models.TextChoices):
        VALORANT = "valorant", "Valorant"
        EFOOTBALL = "efootball", "eFootball Mobile"

    # Back-compat alias so code can keep using Tournament.Status
    Status = TournamentStatus

    # Identity
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    short_description = models.CharField(max_length=255, blank=True, default="")

    # Core config
    game = models.CharField(max_length=20, choices=Game.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    banner = models.ImageField(upload_to=tournament_banner_path, blank=True, null=True)

    # Scheduling/registration windows
    slot_size = models.PositiveIntegerField(null=True, blank=True)
    reg_open_at = models.DateTimeField(blank=True, null=True)
    reg_close_at = models.DateTimeField(blank=True, null=True)
    start_at = models.DateTimeField(blank=True, null=True)
    end_at = models.DateTimeField(blank=True, null=True)

    # Money
    entry_fee_bdt = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prize_pool_bdt = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    groups_published = models.BooleanField(
        default=False,
        help_text="Show bracket groups on public page when enabled."
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["status"]),
            models.Index(fields=["game"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
