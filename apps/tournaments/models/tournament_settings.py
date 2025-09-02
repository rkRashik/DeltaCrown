# apps/tournaments/models/tournament_settings.py
from django.db import models
from .paths import rules_upload_path
from .enums import BracketVisibility

class TournamentSettings(models.Model):
    tournament = models.OneToOneField("Tournament", on_delete=models.CASCADE, related_name="settings")

    # Core toggles
    invite_only = models.BooleanField(default=False)
    auto_check_in = models.BooleanField(default=True)
    allow_substitutes = models.BooleanField(default=False)
    custom_format_enabled = models.BooleanField(default=False)
    automatic_scheduling_enabled = models.BooleanField(default=False)

    # Visibility & region
    bracket_visibility = models.CharField(
        max_length=16, choices=BracketVisibility.choices, default=BracketVisibility.PUBLIC
    )
    region_lock = models.CharField(max_length=32, blank=True, default="")  # free-form scope label

    # Check-in window (mins) — defaults expected by tests
    check_in_open_mins = models.PositiveIntegerField(default=60)
    check_in_close_mins = models.PositiveIntegerField(default=15)

    # Scheduling defaults (mins) — used by auto scheduling tests/helpers
    round_duration_mins = models.PositiveIntegerField(default=40)
    round_gap_mins = models.PositiveIntegerField(default=5)

    # Rules & media
    rules_pdf = models.FileField(upload_to=rules_upload_path, blank=True, null=True)
    facebook_stream_url = models.URLField(blank=True, default="")
    youtube_stream_url = models.URLField(blank=True, default="")
    discord_link = models.URLField(blank=True, default="")

    # Payments (manual)
    bkash_receive_number = models.CharField(max_length=32, blank=True, default="")
    nagad_receive_number = models.CharField(max_length=32, blank=True, default="")
    rocket_receive_number = models.CharField(max_length=32, blank=True, default="")
    bank_instructions = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["tournament_id"]

    def __str__(self):
        return f"Settings for {getattr(self.tournament, 'name', '')}"
