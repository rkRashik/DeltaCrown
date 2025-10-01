# apps/tournaments/models/tournament.py
from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field

from .paths import tournament_banner_path  # rules_pdf_path kept for compat if used anywhere


# Module-level enum to avoid indentation bleed inside the model class
class TournamentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    RUNNING = "RUNNING", "Running"
    COMPLETED = "COMPLETED", "Completed"


class Tournament(models.Model):
    """Primary tournament model with basics, schedule, prizes, and helpers."""

    class Game(models.TextChoices):
        VALORANT = "valorant", "Valorant"
        EFOOTBALL = "efootball", "eFootball Mobile"

    # Back-compat alias so code can keep using Tournament.Status
    Status = TournamentStatus

    # ----- Basics -----
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255)
    short_description = CKEditor5Field("Short description", config_name="default", blank=True, null=True)

    # ----- Core Configuration -----
    game = models.CharField(max_length=20, choices=Game.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    banner = models.ImageField(upload_to=tournament_banner_path, blank=True, null=True)

    # ----- Schedule -----
    slot_size = models.PositiveIntegerField(null=True, blank=True)
    reg_open_at = models.DateTimeField(blank=True, null=True)
    reg_close_at = models.DateTimeField(blank=True, null=True)
    start_at = models.DateTimeField(blank=True, null=True)
    end_at = models.DateTimeField(blank=True, null=True)

    # ----- Finance -----
    entry_fee_bdt = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    prize_pool_bdt = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # ----- Metadata -----
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ----- Publishing toggles -----
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

    # -----------------
    # Computed helpers
    # -----------------
    @property
    def game_name(self) -> str:
        try:
            return self.get_game_display()
        except Exception:
            return getattr(self, "game", "") or ""

    @property
    def banner_url(self) -> str | None:
        try:
            if getattr(self, "banner", None) and getattr(self.banner, "url", None):
                return self.banner.url
        except Exception:
            pass
        try:
            settings = getattr(self, "settings", None)
            if settings and getattr(settings, "banner", None) and getattr(settings.banner, "url", None):
                return settings.banner.url
        except Exception:
            pass
        return None

    @property
    def entry_fee(self):
        """Numeric value for templates expecting `entry_fee`."""
        try:
            val = getattr(self, "entry_fee_bdt", None)
            if val not in (None, ""):
                return val
        except Exception:
            pass
        try:
            settings = getattr(self, "settings", None)
            val = getattr(settings, "entry_fee_bdt", None) if settings else None
            if val not in (None, ""):
                return val
        except Exception:
            pass
        return None

    @property
    def prize_pool(self):
        try:
            val = getattr(self, "prize_pool_bdt", None)
            if val not in (None, ""):
                return val
        except Exception:
            pass
        try:
            settings = getattr(self, "settings", None)
            val = getattr(settings, "prize_pool_bdt", None) if settings else None
            if val not in (None, ""):
                return val
        except Exception:
            pass
        return None

    @property
    def detail_url(self) -> str | None:
        if getattr(self, "slug", None):
            return f"/tournaments/{self.slug}/"
        return None

    def get_absolute_url(self) -> str:
        try:
            return reverse("tournaments:detail", args=[self.slug])
        except Exception:
            return self.detail_url or "/tournaments/"

    @property
    def register_url(self) -> str | None:
        if getattr(self, "slug", None):
            # Use the helper function for consistent URL generation
            try:
                from apps.tournaments.views.helpers import register_url
                return register_url(self)
            except Exception:
                # Fallback to enhanced registration path
                return f"/tournaments/register-enhanced/{self.slug}/"
        return None

    @property
    def bracket_url(self) -> str | None:
        if getattr(self, "slug", None):
            return f"/tournaments/brackets/{self.slug}/"
        return None

    @property
    def registration_open(self) -> bool:
        from django.utils import timezone
        now = timezone.now()
        # Prefer settings window if available, else model fields
        try:
            settings = getattr(self, "settings", None)
            open_at = getattr(settings, "reg_open_at", None) if settings else None
            close_at = getattr(settings, "reg_close_at", None) if settings else None
            if open_at and close_at:
                return open_at <= now <= close_at
        except Exception:
            pass
        try:
            open_at = getattr(self, "reg_open_at", None)
            close_at = getattr(self, "reg_close_at", None)
            if open_at and close_at:
                return open_at <= now <= close_at
        except Exception:
            pass
        return False

    @property
    def is_live(self) -> bool:
        from django.utils import timezone
        now = timezone.now()
        try:
            start = getattr(self, "start_at", None)
            end = getattr(self, "end_at", None)
            if start and end:
                return start <= now <= end
        except Exception:
            pass
        try:
            settings = getattr(self, "settings", None)
            start = getattr(settings, "start_at", None) if settings else None
            end = getattr(settings, "end_at", None) if settings else None
            if start and end:
                return start <= now <= end
        except Exception:
            pass
        return False

    @property
    def slots_total(self):
        return getattr(self, "slot_size", None)

    @property
    def slots_taken(self):
        try:
            # Prefer confirmed registrations if status exists
            regs = getattr(self, "registrations", None)
            if regs is None:
                return None
            try:
                return regs.filter(status="CONFIRMED").count()
            except Exception:
                return regs.count()
        except Exception:
            return None

    @property
    def slots_text(self) -> str | None:
        try:
            total = self.slots_total
            if total:
                taken = self.slots_taken or 0
                return f"{taken}/{total} slots"
        except Exception:
            pass
        return None

    # NOTE: Avoid shadowing DB fields (start_at, end_at, reg_open_at, reg_close_at)
    # with @property of the same name â€” it breaks ORM assignments. Use explicit
    # fallbacks in templates/views instead, e.g. tournament.start_at|default:tournament.settings.start_at.

    @property
    def checkin_window(self) -> str | None:
        try:
            settings = getattr(self, "settings", None)
            if not settings:
                return None
            open_m = getattr(settings, "check_in_open_mins", None)
            close_m = getattr(settings, "check_in_close_mins", None)
            if open_m or close_m:
                open_txt = f"{open_m}m" if open_m else "?"
                close_txt = f"{close_m}m" if close_m else "?"
                return f"Opens {open_txt} â€¢ Closes {close_txt} before"
        except Exception:
            pass
        return None

    @property
    def game_slug(self) -> str:
        return getattr(self, "game", "") or ""

    @property
    def status_simple(self) -> str:
        """Map internal Status to public labels used by UI."""
        s = (getattr(self, "status", "") or "").upper()
        if s in {"RUNNING"}:
            return "ongoing"
        if s in {"PUBLISHED", "OPEN"}:
            return "open"
        if s in {"COMPLETED", "FINISHED"}:
            return "finished"
        return ""
