# apps/tournaments/models/tournament.py
from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django_ckeditor_5.fields import CKEditor5Field

from .paths import tournament_banner_path  # rules_pdf_path kept for compat if used anywhere
from .state_machine import TournamentStateMachine


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
    status = models.CharField(
        max_length=16, 
        choices=Status.choices, 
        default=Status.DRAFT,
        help_text="Tournament lifecycle status. DRAFT=hidden, PUBLISHED=visible, RUNNING=active, COMPLETED=finished"
    )
    banner = models.ImageField(upload_to=tournament_banner_path, blank=True, null=True)

    # ----- Professional Fields (Phase 2 Enhancement) -----
    tournament_type = models.CharField(
        max_length=32,
        choices=[
            ('SOLO', 'Solo'),
            ('TEAM', 'Team'),
            ('MIXED', 'Mixed (Solo & Team)'),
        ],
        default='TEAM',
        help_text="Type of tournament: Solo, Team, or Mixed"
    )
    
    format = models.CharField(
        max_length=32,
        choices=[
            ('SINGLE_ELIM', 'Single Elimination'),
            ('DOUBLE_ELIM', 'Double Elimination'),
            ('ROUND_ROBIN', 'Round Robin'),
            ('SWISS', 'Swiss System'),
            ('GROUP_STAGE', 'Group Stage'),
            ('HYBRID', 'Hybrid (Groups + Bracket)'),
        ],
        blank=True,
        default='',
        help_text="Tournament format/structure"
    )
    
    platform = models.CharField(
        max_length=32,
        choices=[
            ('ONLINE', 'Online'),
            ('OFFLINE', 'Offline/LAN'),
            ('HYBRID', 'Hybrid'),
        ],
        default='ONLINE',
        help_text="Where the tournament takes place"
    )
    
    region = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Geographic region (e.g., 'Bangladesh', 'South Asia', 'Global')"
    )
    
    language = models.CharField(
        max_length=8,
        choices=[
            ('en', 'English'),
            ('bn', 'বাংলা (Bengali)'),
            ('hi', 'हिन्दी (Hindi)'),
            ('multi', 'Multilingual'),
        ],
        default='en',
        help_text="Primary language for tournament communication"
    )
    
    organizer = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='organized_tournaments',
        help_text="User or organization running this tournament"
    )
    
    description = CKEditor5Field(
        "Full Description",
        config_name="extends",
        blank=True,
        null=True,
        help_text="Detailed tournament description (supports rich text)"
    )

    # ----- DEPRECATED FIELDS (use Phase 1 models instead) -----
    # These fields are kept for backward compatibility but will be removed in v2.0
    # Use the corresponding Phase 1 models instead:
    #   - slot_size → TournamentCapacity.max_teams
    #   - reg_open_at, reg_close_at, start_at, end_at → TournamentSchedule
    #   - entry_fee_bdt, prize_pool_bdt → TournamentFinance
    
    slot_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="⚠️ DEPRECATED: Use TournamentCapacity.max_teams instead. "
                  "This field is kept for backward compatibility but will be removed in v2.0."
    )
    
    reg_open_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="⚠️ DEPRECATED: Use TournamentSchedule.registration_start instead. "
                  "This field is kept for backward compatibility but will be removed in v2.0."
    )
    
    reg_close_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="⚠️ DEPRECATED: Use TournamentSchedule.registration_end instead. "
                  "This field is kept for backward compatibility but will be removed in v2.0."
    )
    
    start_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="⚠️ DEPRECATED: Use TournamentSchedule.tournament_start instead. "
                  "This field is kept for backward compatibility but will be removed in v2.0."
    )
    
    end_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="⚠️ DEPRECATED: Use TournamentSchedule.tournament_end instead. "
                  "This field is kept for backward compatibility but will be removed in v2.0."
    )
    
    entry_fee_bdt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="⚠️ DEPRECATED: Use TournamentFinance.entry_fee + currency instead. "
                  "This field is kept for backward compatibility but will be removed in v2.0."
    )
    
    prize_pool_bdt = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="⚠️ DEPRECATED: Use TournamentFinance.prize_pool + prize_currency instead. "
                  "This field is kept for backward compatibility but will be removed in v2.0."
    )

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

    def clean(self):
        """Validate tournament fields before saving."""
        from django.core.exceptions import ValidationError
        
        # Validate schedule dates
        if self.reg_open_at and self.reg_close_at:
            if self.reg_open_at >= self.reg_close_at:
                raise ValidationError({
                    'reg_close_at': 'Registration close time must be after open time.'
                })
        
        if self.start_at and self.end_at:
            if self.start_at >= self.end_at:
                raise ValidationError({
                    'end_at': 'Tournament end time must be after start time.'
                })
        
        if self.reg_close_at and self.start_at:
            if self.reg_close_at > self.start_at:
                raise ValidationError({
                    'reg_close_at': 'Registration must close before tournament starts.'
                })
        
        # Validate slot_size
        if self.slot_size is not None and self.slot_size < 2:
            raise ValidationError({
                'slot_size': 'Slot size must be at least 2 participants.'
            })

    # -----------------
    # State Machine
    # -----------------
    @property
    def state(self) -> TournamentStateMachine:
        """
        Access centralized state machine.
        Use: tournament.state.registration_state, tournament.state.can_register(), etc.
        """
        return TournamentStateMachine(self)

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
        """
        Entry fee in BDT (prefers Phase 1 model).
        Returns Decimal or None.
        """
        # Prefer Phase 1 TournamentFinance model
        try:
            if hasattr(self, 'finance') and self.finance:
                return self.finance.entry_fee
        except Exception:
            pass
        
        # Fallback to deprecated field
        if self.entry_fee_bdt is not None:
            return self.entry_fee_bdt
        
        return None

    @property
    def prize_pool(self):
        """
        Prize pool in BDT (prefers Phase 1 model).
        Returns Decimal or None.
        """
        # Prefer Phase 1 TournamentFinance model
        try:
            if hasattr(self, 'finance') and self.finance:
                return self.finance.prize_pool
        except Exception:
            pass
        
        # Fallback to deprecated field
        if self.prize_pool_bdt is not None:
            return self.prize_pool_bdt
        
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
        """Check if registration is currently open (prefers Phase 1 model)"""
        from django.utils import timezone
        now = timezone.now()
        
        # Prefer Phase 1 TournamentSchedule model
        try:
            if hasattr(self, 'schedule') and self.schedule:
                return self.schedule.is_registration_open()
        except Exception:
            pass
        
        # Fallback to deprecated fields for backward compatibility
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
        """Check if tournament is currently running (prefers Phase 1 model)"""
        from django.utils import timezone
        now = timezone.now()
        
        # Prefer Phase 1 TournamentSchedule model
        try:
            if hasattr(self, 'schedule') and self.schedule:
                return self.schedule.is_in_progress()
        except Exception:
            pass
        
        # Fallback to deprecated fields
        try:
            start = getattr(self, "start_at", None)
            end = getattr(self, "end_at", None)
            if start and end:
                return start <= now <= end
        except Exception:
            pass
        
        return False

    @property
    def slots_total(self):
        """Total number of slots/teams (prefers Phase 1 model)"""
        # Prefer Phase 1 TournamentCapacity model
        try:
            if hasattr(self, 'capacity') and self.capacity:
                return self.capacity.max_teams
        except Exception:
            pass
        
        # Fallback to deprecated field
        return getattr(self, "slot_size", None)

    @property
    def slots_taken(self):
        """Number of slots/teams currently filled (prefers Phase 1 model)"""
        # Prefer Phase 1 TournamentCapacity model (live count)
        try:
            if hasattr(self, 'capacity') and self.capacity:
                return self.capacity.current_teams
        except Exception:
            pass
        
        # Fallback to registration count
        try:
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
    
    # ==========================================
    # V7 Production Enhancements
    # ==========================================
    
    @property
    def registration_progress_percentage(self) -> float:
        """Calculate registration progress for progress bar"""
        try:
            if hasattr(self, 'capacity') and self.capacity:
                if self.capacity.max_teams > 0:
                    return (self.capacity.current_registrations / self.capacity.max_teams) * 100
        except Exception:
            pass
        return 0.0
    
    @property
    def registration_status_badge(self) -> dict:
        """Return color-coded status badge for registration"""
        if self.registration_open:
            # Check if closing soon
            try:
                if hasattr(self, 'schedule') and self.schedule:
                    if self.schedule.is_registration_closing_soon:
                        return {
                            'text': 'Closing Soon',
                            'color': 'warning',
                            'icon': '🟡',
                            'class': 'badge-warning pulse'
                        }
            except Exception:
                pass
            
            return {
                'text': 'Open',
                'color': 'success',
                'icon': '🟢',
                'class': 'badge-success'
            }
        
        return {
            'text': 'Closed',
            'color': 'danger',
            'icon': '🔴',
            'class': 'badge-danger'
        }
    
    @property
    def status_badge(self) -> dict:
        """Return color-coded tournament status badge"""
        status_map = {
            'DRAFT': {'text': 'Draft', 'color': 'secondary', 'icon': '📝', 'class': 'badge-secondary'},
            'PUBLISHED': {'text': 'Published', 'color': 'info', 'icon': '📢', 'class': 'badge-info'},
            'RUNNING': {'text': 'Live', 'color': 'success', 'icon': '🎮', 'class': 'badge-success pulse'},
            'COMPLETED': {'text': 'Completed', 'color': 'dark', 'icon': '🏁', 'class': 'badge-dark'},
        }
        return status_map.get(self.status, {'text': 'Unknown', 'color': 'secondary', 'icon': '❓', 'class': 'badge-secondary'})
    
    @property
    def is_full(self) -> bool:
        """Check if tournament reached capacity"""
        try:
            if hasattr(self, 'capacity') and self.capacity:
                return self.capacity.is_full
        except Exception:
            pass
        return False
    
    @property
    def has_available_slots(self) -> bool:
        """Check if tournament has available slots"""
        return not self.is_full
    
    @property
    def seo_meta(self) -> dict:
        """Generate SEO meta tags for social sharing and search engines"""
        try:
            description = ''
            if self.short_description:
                # Strip HTML tags for meta description
                from django.utils.html import strip_tags
                description = strip_tags(self.short_description)[:160]
            elif self.description:
                from django.utils.html import strip_tags
                description = strip_tags(self.description)[:160]
            
            # Get banner URL
            banner_url = '/static/images/tournament-default.jpg'
            try:
                if hasattr(self, 'media') and self.media and self.media.banner:
                    banner_url = self.media.banner.url
                elif self.banner:
                    banner_url = self.banner.url
            except Exception:
                pass
            
            # Generate keywords
            keywords = [
                self.game,
                'tournament',
                'esports',
                'gaming'
            ]
            if self.region:
                keywords.append(self.region.lower())
            if self.format:
                keywords.append(self.get_format_display().lower())
            
            return {
                'title': f"{self.name} - {self.game_name} Tournament",
                'description': description,
                'keywords': ', '.join(keywords),
                'og_image': banner_url,
                'og_type': 'website',
            }
        except Exception:
            return {
                'title': self.name,
                'description': '',
                'keywords': '',
                'og_image': '/static/images/tournament-default.jpg',
                'og_type': 'website',
            }
