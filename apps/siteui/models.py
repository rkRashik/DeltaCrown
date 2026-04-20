"""
Community and User Social Models
"""
from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.user_profile.models import UserProfile
from apps.common.validators import validate_image_upload
from .utils.embeds import detect_platform
from .utils.media_parser import parse_media_url

User = get_user_model()


class HomePageContent(models.Model):
    """
    Single-row singleton model for homepage content management.
    
    This model stores all editable content for the homepage, including hero section,
    CTAs, section toggles, and data for various sections. It enforces a singleton
    pattern to ensure only one homepage configuration exists at any time.
    
    Usage:
        content = HomePageContent.get_instance()
        content.hero_title = "New Title"
        content.save()
    """
    
    # === HERO SECTION ===
    hero_badge_text = models.CharField(
        max_length=100,
        default="Bangladesh's #1 Esports Platform",
        help_text="Badge text above hero title"
    )
    hero_title = models.CharField(
        max_length=200,
        default="From the Delta to the Crown",
        help_text="Main hero headline"
    )
    hero_subtitle = models.CharField(
        max_length=200,
        default="Where Champions Rise",
        help_text="Hero subtitle/tagline"
    )
    hero_description = models.TextField(
        default=(
            "Building a world where geography does not define destiny—where a gamer in "
            "Bangladesh has the same trusted path to global glory as a pro on the main stage."
        ),
        help_text="Hero description paragraph"
    )
    
    # Hero CTAs
    primary_cta_text = models.CharField(max_length=50, default="Join Tournament")
    primary_cta_url = models.CharField(max_length=200, default="/tournaments/")
    primary_cta_icon = models.CharField(max_length=10, default="🏆", blank=True)
    
    secondary_cta_text = models.CharField(max_length=50, default="Explore Teams")
    secondary_cta_url = models.CharField(max_length=200, default="/teams/")
    secondary_cta_icon = models.CharField(max_length=10, default="👥", blank=True)
    
    # Hero highlights/stats (JSON array of objects)
    hero_highlights = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Array of stat highlights: [{"label": "Active Players", "value": "12,500+", '
            '"icon": "👥", "source": "DB_COUNT"}]. source can be "DB_COUNT" or "STATIC"'
        )
    )
    
    # === PROBLEM/OPPORTUNITY SECTION ===
    problem_section_enabled = models.BooleanField(default=True)
    problem_title = models.CharField(
        max_length=200,
        default="The Esports Gap",
        help_text="Problem section headline"
    )
    problem_subtitle = models.TextField(
        default="Most platforms solve one problem. DeltaCrown solves the entire esports lifecycle.",
        help_text="Problem section description"
    )
    comparison_table = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Comparison items: [{"traditional": "One-time tournaments", '
            '"deltacrown": "Persistent competitive history"}]'
        )
    )
    
    # === ECOSYSTEM PILLARS SECTION ===
    pillars_section_enabled = models.BooleanField(default=True)
    ecosystem_pillars_title = models.CharField(
        max_length=200,
        default="Complete Esports Ecosystem",
        help_text="Ecosystem section headline"
    )
    ecosystem_pillars_description = models.TextField(
        default="Eight interconnected domains, one unified platform",
        help_text="Ecosystem section description"
    )
    ecosystem_pillars = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Array of pillars: [{"icon": "🏆", "title": "Tournaments", '
            '"description": "...", "link": "/tournaments/"}]'
        )
    )
    
    # === GAMES SECTION ===
    games_section_enabled = models.BooleanField(default=True)
    games_section_title = models.CharField(
        max_length=200,
        default="11 Games, One Platform",
        help_text="Games section headline"
    )
    games_section_description = models.TextField(
        default="From mobile to PC, tactical shooters to sports—game-agnostic by design",
        help_text="Games section description"
    )
    games_data = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Array of games: [{"slug": "cod-mobile", "name": "Call of Duty®: Mobile", '
            '"tagline": "Tactical FPS", "platforms": ["Mobile"], "color": "#FF6B00"}]. '
            'Phase 1: JSON. Phase 2: Migrate to Game model FK.'
        )
    )
    
    # === TOURNAMENTS SECTION ===
    tournaments_section_enabled = models.BooleanField(default=True)
    tournaments_section_title = models.CharField(
        max_length=200,
        default="Active Tournaments",
        help_text="Tournaments section headline"
    )
    tournaments_section_description = models.TextField(
        default="Join verified competitions with real prizes",
        help_text="Tournaments section description"
    )
    
    # === TEAMS SECTION ===
    teams_section_enabled = models.BooleanField(default=True)
    teams_section_title = models.CharField(
        max_length=200,
        default="Top Teams",
        help_text="Teams section headline"
    )
    teams_section_description = models.TextField(
        default="Professional organizations competing for glory",
        help_text="Teams section description"
    )
    
    # === LOCAL PAYMENTS SECTION ===
    payments_section_enabled = models.BooleanField(default=True)
    payments_section_title = models.CharField(
        max_length=200,
        default="Local Payment Partners",
        help_text="Payments section headline"
    )
    payments_section_description = models.TextField(
        default="Bangladesh-first infrastructure—we support the payment methods you already trust",
        help_text="Payments section description"
    )
    payment_methods = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Array of payment methods: [{"name": "bKash", "icon": "💳", '
            '"color": "#E2136E", "description": "Mobile money leader"}]'
        )
    )
    payments_trust_message = models.TextField(
        default="No credit cards required. No barriers to entry. Built for South Asian markets.",
        help_text="Trust message for payment methods"
    )
    
    # === DELTACOIN ECONOMY SECTION ===
    deltacoin_section_enabled = models.BooleanField(default=True)
    deltacoin_section_title = models.CharField(
        max_length=200,
        default="DeltaCoin Economy",
        help_text="DeltaCoin section headline"
    )
    deltacoin_section_description = models.TextField(
        default="Earn by competing. Spend on upgrades. Build your legacy.",
        help_text="DeltaCoin section description"
    )
    deltacoin_earn_methods = models.JSONField(
        default=list,
        blank=True,
        help_text='Array of earn methods: ["Participating in tournaments", "Winning matches"]'
    )
    deltacoin_spend_options = models.JSONField(
        default=list,
        blank=True,
        help_text='Array of spend options: ["Store purchases", "Premium subscriptions"]'
    )
    
    # === COMMUNITY SECTION ===
    community_section_enabled = models.BooleanField(default=True)
    community_section_title = models.CharField(
        max_length=200,
        default="Join the Community",
        help_text="Community section headline"
    )
    community_section_description = models.TextField(
        default="Strategy guides, match highlights, esports news—all in one home",
        help_text="Community section description"
    )
    
    # === ROADMAP SECTION ===
    roadmap_section_enabled = models.BooleanField(default=True)
    roadmap_section_title = models.CharField(
        max_length=200,
        default="The Vision Ahead",
        help_text="Roadmap section headline"
    )
    roadmap_section_description = models.TextField(
        default="Evolving toward global scale while staying rooted in emerging markets",
        help_text="Roadmap section description"
    )
    roadmap_items = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Array of roadmap items: [{"status": "COMPLETED", "title": "...", '
            '"description": "..."}]. status: COMPLETED, IN_PROGRESS, PLANNED'
        )
    )
    
    # === FINAL CTA SECTION ===
    final_cta_section_enabled = models.BooleanField(default=True)
    final_cta_title = models.CharField(
        max_length=200,
        default="Ready to Compete?",
        help_text="Final CTA headline"
    )
    final_cta_description = models.TextField(
        default="Join thousands of gamers building their esports careers on DeltaCrown",
        help_text="Final CTA description"
    )
    final_cta_primary_text = models.CharField(max_length=50, default="Create Account")
    final_cta_primary_url = models.CharField(max_length=200, default="/account/register/")
    final_cta_secondary_text = models.CharField(max_length=50, default="Explore Platform")
    final_cta_secondary_url = models.CharField(max_length=200, default="/about/")
    
    # === PLATFORM INFO (for footer/about) ===
    platform_tagline = models.CharField(
        max_length=200,
        default="From the Delta to the Crown — Where Champions Rise.",
        help_text="Platform tagline for footer/about sections"
    )
    platform_founded_year = models.PositiveIntegerField(
        default=2025,
        help_text="Year DeltaCrown was founded"
    )
    platform_founder = models.CharField(
        max_length=100,
        default="Redwanul Rashik",
        help_text="Founder name"
    )
    
    # === META ===
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='homepage_updates',
        help_text="Last user who updated homepage content"
    )
    
    class Meta:
        verbose_name = "Homepage Content"
        verbose_name_plural = "Homepage Content"
        db_table = "siteui_homepage_content"
    
    def __str__(self):
        return f"Homepage Content (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        """Enforce singleton: only one instance allowed."""
        if not self.pk and HomePageContent.objects.exists():
            raise ValidationError(
                "Only one HomePageContent instance is allowed. "
                "Please edit the existing instance instead."
            )
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_instance(cls):
        """
        Get or create the singleton instance.
        
        Returns:
            HomePageContent: The singleton instance with default values.
        """
        obj, created = cls.objects.get_or_create(pk=1)
        if created:
            # Initialize with default content on first creation
            obj._initialize_default_content()
            obj.save()
        return obj
    
    def _initialize_default_content(self):
        """Initialize default content for all JSON fields."""
        # Hero highlights
        self.hero_highlights = [
            {
                "label": "Active Players",
                "value": "12,500+",
                "icon": "👥",
                "source": "DB_COUNT"
            },
            {
                "label": "Prize Pool",
                "value": "৳5,00,000+",
                "icon": "💰",
                "source": "STATIC"
            },
            {
                "label": "Tournaments",
                "value": "150+",
                "icon": "🏆",
                "source": "DB_COUNT"
            },
            {
                "label": "Games",
                "value": "11",
                "icon": "🎮",
                "source": "STATIC"
            }
        ]
        
        # Comparison table
        self.comparison_table = [
            {
                "traditional": "One-time tournaments",
                "deltacrown": "Persistent competitive history"
            },
            {
                "traditional": "Temporary teams",
                "deltacrown": "Professional organizations"
            },
            {
                "traditional": "No career progression",
                "deltacrown": "Player & team legacy"
            },
            {
                "traditional": "Fragmented tools",
                "deltacrown": "Unified ecosystem"
            },
            {
                "traditional": "No local payment support",
                "deltacrown": "Global + local payments"
            }
        ]
        
        # Ecosystem pillars
        self.ecosystem_pillars = [
            {
                "icon": "🏆",
                "title": "Tournaments",
                "description": "Smart registration, automated brackets, verified results",
                "link": "/tournaments/"
            },
            {
                "icon": "👥",
                "title": "Teams",
                "description": "Professional structures with coaches, managers, sponsors",
                "link": "/teams/"
            },
            {
                "icon": "🎯",
                "title": "Players",
                "description": "Career progression, stats tracking, achievement system",
                "link": "/players/"
            },
            {
                "icon": "💰",
                "title": "Economy",
                "description": "DeltaCoin rewards, local payments, prize distribution",
                "link": "/economy/"
            },
            {
                "icon": "🌐",
                "title": "Community",
                "description": "Content, highlights, strategy guides, esports news",
                "link": "/community/"
            },
            {
                "icon": "📊",
                "title": "Rankings",
                "description": "Real-time leaderboards, performance analytics",
                "link": "/leaderboards/"
            },
            {
                "icon": "🧠",
                "title": "Coaching",
                "description": "Mentorship, training systems, skill development",
                "link": "/coaching/"
            },
            {
                "icon": "🛒",
                "title": "Commerce",
                "description": "Team merch, gaming gear, digital products",
                "link": "/shop/"
            }
        ]
        
        # Games (11 official titles from README.md)
        self.games_data = [
            {
                "slug": "call-of-duty-mobile",
                "name": "Call of Duty®: Mobile",
                "tagline": "Tactical FPS",
                "platforms": ["Mobile"],
                "color": "#FF6B00"
            },
            {
                "slug": "counter-strike-2",
                "name": "Counter-Strike 2",
                "tagline": "Competitive FPS",
                "platforms": ["PC"],
                "color": "#FF9800"
            },
            {
                "slug": "dota-2",
                "name": "Dota 2",
                "tagline": "Strategic MOBA",
                "platforms": ["PC"],
                "color": "#D32F2F"
            },
            {
                "slug": "ea-sports-fc-26",
                "name": "EA SPORTS FC™ 26",
                "tagline": "Football Simulation",
                "platforms": ["PC", "Console"],
                "color": "#00D9FF"
            },
            {
                "slug": "free-fire",
                "name": "Free Fire",
                "tagline": "Battle Royale",
                "platforms": ["Mobile"],
                "color": "#FF5722"
            },
            {
                "slug": "mobile-legends",
                "name": "Mobile Legends: Bang Bang",
                "tagline": "Mobile MOBA",
                "platforms": ["Mobile"],
                "color": "#4A90E2"
            },
            {
                "slug": "pubg-mobile",
                "name": "PUBG MOBILE",
                "tagline": "Battle Royale",
                "platforms": ["Mobile"],
                "color": "#FFB300"
            },
            {
                "slug": "rocket-league",
                "name": "Rocket League",
                "tagline": "Vehicular Soccer",
                "platforms": ["PC", "Console"],
                "color": "#0076FF"
            },
            {
                "slug": "rainbow-six-siege",
                "name": "Tom Clancy's Rainbow Six® Siege",
                "tagline": "Tactical Shooter",
                "platforms": ["PC", "Console"],
                "color": "#FFC107"
            },
            {
                "slug": "valorant",
                "name": "VALORANT",
                "tagline": "Character-Based FPS",
                "platforms": ["PC"],
                "color": "#FF4655"
            },
            {
                "slug": "efootball-2026",
                "name": "eFootball™ 2026",
                "tagline": "Football Simulation",
                "platforms": ["PC", "Mobile", "Console"],
                "color": "#0066CC"
            }
        ]
        
        # Payment methods
        self.payment_methods = [
            {
                "name": "bKash",
                "icon": "💳",
                "color": "#E2136E",
                "description": "Mobile money leader"
            },
            {
                "name": "Nagad",
                "icon": "📱",
                "color": "#EE4023",
                "description": "Fast & reliable"
            },
            {
                "name": "Rocket",
                "icon": "⚡",
                "color": "#8142C6",
                "description": "Dutch-Bangla Bank"
            },
            {
                "name": "Bank Transfer",
                "icon": "🏦",
                "color": "#10B981",
                "description": "Traditional & secure"
            }
        ]
        
        # DeltaCoin economy
        self.deltacoin_earn_methods = [
            "Participating in tournaments",
            "Winning matches",
            "Achieving milestones",
            "Engaging with community"
        ]
        
        self.deltacoin_spend_options = [
            "Store purchases",
            "Premium subscriptions",
            "Platform services",
            "Team merchandise"
        ]
        
        # Roadmap
        self.roadmap_items = [
            {
                "status": "COMPLETED",
                "title": "Full Tournament Lifecycle",
                "description": "Brackets, registration, results, disputes"
            },
            {
                "status": "COMPLETED",
                "title": "Team & Player Systems",
                "description": "Professional structures, ranking, analytics"
            },
            {
                "status": "IN_PROGRESS",
                "title": "Payment Integration",
                "description": "Local payment methods + prize distribution"
            },
            {
                "status": "PLANNED",
                "title": "Mobile Apps",
                "description": "iOS & Android native apps"
            },
            {
                "status": "PLANNED",
                "title": "Sponsor Marketplace",
                "description": "Connect brands with teams"
            },
            {
                "status": "PLANNED",
                "title": "Streaming Integrations",
                "description": "YouTube, Twitch, Facebook Gaming"
            }
        ]


class ArenaGlobalWidget(models.Model):
    """Admin-managed global fan pulse widget for Arena."""

    badge_label = models.CharField(
        max_length=60,
        default="Fan Pulse",
        help_text="Small badge label shown at the top of the widget",
    )
    meta_label = models.CharField(
        max_length=60,
        default="Global Widget",
        help_text="Meta label on the top-right of the widget",
    )
    tournament_label = models.CharField(
        max_length=120,
        blank=True,
        default="",
        help_text="Tournament or context label above the question",
    )
    prompt_text = models.CharField(
        max_length=220,
        default="Who wins the Grand Final?",
        help_text="Primary prediction question shown to users",
    )
    option_a_label = models.CharField(max_length=120, default="Team A")
    option_a_percent = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Displayed percentage for option A",
    )
    option_b_label = models.CharField(max_length=120, default="Team B")
    option_b_percent = models.PositiveSmallIntegerField(
        default=50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Displayed percentage for option B",
    )
    vote_count = models.PositiveIntegerField(
        default=0,
        help_text="Signal/vote count displayed below options",
    )
    vote_count_label = models.CharField(
        max_length=80,
        default="Signals Intercepted",
        help_text="Suffix shown after vote count",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.IntegerField(default=0, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Arena Global Widget"
        verbose_name_plural = "Arena Global Widgets"
        ordering = ["display_order", "-updated_at", "id"]
        indexes = [
            models.Index(
                fields=["is_active", "display_order"],
                name="siteui_aren_is_acti_8368e8_idx",
            ),
            models.Index(
                fields=["starts_at", "ends_at"],
                name="siteui_aren_starts__1f194f_idx",
            ),
        ]

    def __str__(self):
        return f"{self.badge_label}: {self.prompt_text[:80]}"

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError("End time must be after start time.")
        if (self.option_a_percent + self.option_b_percent) != 100:
            raise ValidationError("Option percentages must add up to 100.")
        if self.option_a_label.strip().lower() == self.option_b_label.strip().lower():
            raise ValidationError("Option labels must be different.")

    def is_visible_now(self, now=None):
        now = now or timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True


class ArenaHighlight(models.Model):
    """Short-form highlight cards shown in the Arena sidebar/rail."""

    PROVIDER_YOUTUBE = "youtube"
    PROVIDER_TWITCH = "twitch"
    PROVIDER_FACEBOOK = "facebook"
    PROVIDER_OTHER = "other"

    PROVIDER_CHOICES = [
        (PROVIDER_YOUTUBE, "YouTube"),
        (PROVIDER_TWITCH, "Twitch"),
        (PROVIDER_FACEBOOK, "Facebook"),
        (PROVIDER_OTHER, "Other"),
    ]

    source_url = models.URLField(
        help_text="Primary media source URL (YouTube/Twitch/Facebook/other)",
    )
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.SET_NULL,
        related_name="arena_highlights",
        null=True,
        blank=True,
    )
    fetched_title = models.CharField(max_length=200, blank=True, default="")
    fetched_thumbnail_url = models.URLField(blank=True, default="")
    embed_url = models.URLField(blank=True, default="")
    provider = models.CharField(
        max_length=20,
        choices=PROVIDER_CHOICES,
        default=PROVIDER_OTHER,
        blank=True,
    )
    custom_title = models.CharField(max_length=200, blank=True, default="")
    custom_thumbnail = models.ImageField(
        upload_to="arena/highlights/%Y/%m/%d/",
        validators=[validate_image_upload],
        null=True,
        blank=True,
    )
    subtitle = models.CharField(max_length=180, blank=True, default="")
    duration_label = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Short duration label (e.g. 0:32)",
    )
    views_label = models.CharField(
        max_length=60,
        blank=True,
        default="",
        help_text="Short view counter text (e.g. 2.4k views)",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    display_order = models.IntegerField(default=0, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Arena Highlight"
        verbose_name_plural = "Arena Highlights"
        ordering = ["display_order", "-updated_at", "id"]
        indexes = [
            models.Index(
                fields=["is_active", "display_order"],
                name="siteui_aren_is_acti_08fd94_idx",
            )
        ]

    def __str__(self):
        return self.display_title or self.source_url

    def _source_url_has_changed(self) -> bool:
        if not self.pk:
            return True
        try:
            previous = type(self).objects.only("source_url").get(pk=self.pk)
        except type(self).DoesNotExist:
            return True
        return (previous.source_url or "").strip() != (self.source_url or "").strip()

    def save(self, *args, **kwargs):
        should_parse = self._source_url_has_changed()
        if should_parse:
            try:
                parsed = parse_media_url(self.source_url)
            except Exception:
                parsed = {}

            self.provider = (parsed.get("provider") or self.PROVIDER_OTHER).lower()
            self.fetched_title = (parsed.get("title") or "").strip()
            self.fetched_thumbnail_url = (parsed.get("thumbnail_url") or "").strip()
            self.embed_url = (parsed.get("embed_url") or "").strip()

        super().save(*args, **kwargs)

    @property
    def display_title(self):
        return (self.custom_title or "").strip() or (self.fetched_title or "").strip()

    @property
    def display_thumbnail(self):
        if self.custom_thumbnail:
            try:
                return self.custom_thumbnail.url
            except Exception:
                pass
        return (self.fetched_thumbnail_url or "").strip()

    @property
    def safe_embed_url(self):
        return (self.embed_url or "").strip()

    @property
    def resolved_thumbnail_url(self):
        return self.display_thumbnail

    # Backward-compatible aliases used by older code paths.
    @property
    def title(self):
        return self.display_title

    @property
    def video_url(self):
        return self.source_url

    @property
    def thumbnail_url(self):
        return self.display_thumbnail

    @property
    def thumbnail_image(self):
        return self.custom_thumbnail


class ArenaStream(models.Model):
    """Admin-managed streams surfaced in Arena top broadcasts."""

    PROVIDER_YOUTUBE = "youtube"
    PROVIDER_TWITCH = "twitch"
    PROVIDER_FACEBOOK = "facebook"
    PROVIDER_OTHER = "other"

    PROVIDER_CHOICES = [
        (PROVIDER_YOUTUBE, "YouTube"),
        (PROVIDER_TWITCH, "Twitch"),
        (PROVIDER_FACEBOOK, "Facebook"),
        (PROVIDER_OTHER, "Other"),
    ]

    source_url = models.URLField(help_text="Primary media source URL")
    fetched_title = models.CharField(max_length=200, blank=True, default="")
    fetched_thumbnail_url = models.URLField(blank=True, default="")
    embed_url = models.URLField(blank=True, default="")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_OTHER, blank=True)
    custom_title = models.CharField(max_length=200, blank=True, default="")
    custom_thumbnail = models.ImageField(
        upload_to="arena/streams/%Y/%m/%d/",
        validators=[validate_image_upload],
        null=True,
        blank=True,
    )
    subtitle = models.CharField(max_length=180, blank=True, default="")
    channel_name = models.CharField(max_length=120, blank=True, default="")
    game = models.ForeignKey(
        "games.Game",
        on_delete=models.SET_NULL,
        related_name="arena_streams",
        null=True,
        blank=True,
    )
    game_label = models.CharField(max_length=100, blank=True, default="")
    is_live = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)
    viewers_label = models.CharField(max_length=60, blank=True, default="")
    viewer_count = models.PositiveIntegerField(null=True, blank=True)
    display_order = models.IntegerField(default=0, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Arena Stream"
        verbose_name_plural = "Arena Streams"
        ordering = ["-featured", "display_order", "-updated_at", "id"]
        indexes = [
            models.Index(fields=["is_active", "is_live", "featured", "display_order"]),
            models.Index(fields=["starts_at", "ends_at"]),
        ]

    def __str__(self):
        return self.display_title or self.source_url

    def _source_url_has_changed(self) -> bool:
        if not self.pk:
            return True
        try:
            previous = type(self).objects.only("source_url").get(pk=self.pk)
        except type(self).DoesNotExist:
            return True
        return (previous.source_url or "").strip() != (self.source_url or "").strip()

    def save(self, *args, **kwargs):
        should_parse = self._source_url_has_changed()
        if should_parse:
            try:
                parsed = parse_media_url(self.source_url)
            except Exception:
                parsed = {}

            self.provider = (parsed.get("provider") or self.PROVIDER_OTHER).lower()
            self.fetched_title = (parsed.get("title") or "").strip()
            self.fetched_thumbnail_url = (parsed.get("thumbnail_url") or "").strip()
            self.embed_url = (parsed.get("embed_url") or "").strip()

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError("End time must be after start time.")

    @property
    def display_title(self):
        return (self.custom_title or "").strip() or (self.fetched_title or "").strip()

    @property
    def display_thumbnail(self):
        if self.custom_thumbnail:
            try:
                return self.custom_thumbnail.url
            except Exception:
                pass
        return (self.fetched_thumbnail_url or "").strip()

    @property
    def safe_embed_url(self):
        return (self.embed_url or "").strip()

    @property
    def effective_game_label(self):
        if self.game:
            return self.game.display_name or self.game.name
        return self.game_label

    @property
    def effective_thumbnail_url(self):
        return self.display_thumbnail

    @property
    def effective_platform(self):
        if self.provider and self.provider != self.PROVIDER_OTHER:
            return dict(self.PROVIDER_CHOICES).get(self.provider, "")
        detected = detect_platform(self.source_url)
        return detected or "Other"

    def is_currently_live(self, now=None):
        now = now or timezone.now()
        if not self.is_active or not self.is_live:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    # Backward-compatible aliases used by older code paths.
    @property
    def title(self):
        return self.display_title

    @property
    def stream_url(self):
        return self.source_url

    @property
    def thumbnail_url(self):
        return self.display_thumbnail

    @property
    def thumbnail_image(self):
        return self.custom_thumbnail

    @property
    def platform(self):
        return self.provider


class ArenaGlobalWidgetVote(models.Model):
    """Stored vote records for ArenaGlobalWidget prediction polls."""

    OPTION_A = "A"
    OPTION_B = "B"
    OPTION_CHOICES = [
        (OPTION_A, "Option A"),
        (OPTION_B, "Option B"),
    ]

    widget = models.ForeignKey(
        ArenaGlobalWidget,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arena_widget_votes",
    )
    voter_key = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="Anonymous/session voter fingerprint for one-vote enforcement",
    )
    selected_option = models.CharField(max_length=1, choices=OPTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Arena Vote"
        verbose_name_plural = "Arena Votes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["widget", "selected_option"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["widget", "user"],
                condition=Q(user__isnull=False),
                name="siteui_arena_vote_unique_user",
            ),
            models.UniqueConstraint(
                fields=["widget", "voter_key"],
                condition=Q(voter_key__gt=""),
                name="siteui_arena_vote_unique_key",
            ),
        ]

    def __str__(self):
        label = "Option A" if self.selected_option == self.OPTION_A else "Option B"
        return f"Widget {self.widget_id}: {label}"

    def clean(self):
        super().clean()
        if not self.user and not self.voter_key:
            raise ValidationError("Vote must include either a user or a voter key.")


class CommunityPost(models.Model):
    """
    Community posts that can be created by individual users or on behalf of a team.
    """
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]
    
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_posts')
    # Optional: post on behalf of a team (author must be OWNER/MANAGER on that team)
    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='community_posts',
        help_text="If set, this post is published on behalf of the team"
    )
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    
    # Game association (optional)
    game = models.CharField(max_length=100, blank=True, help_text="Game this post is related to")
    
    # Engagement
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['visibility', '-created_at']),
            models.Index(fields=['game', '-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.author.user.username}: {self.title or self.content[:50]}"
    
    def get_absolute_url(self):
        return reverse('siteui:community_post_detail', kwargs={'pk': self.pk})
    
    @property
    def excerpt(self):
        """Return a short excerpt of the content"""
        if self.title:
            return self.title
        return self.content[:100] + '...' if len(self.content) > 100 else self.content


class CommunityPostMedia(models.Model):
    """
    Media attachments for community posts
    """
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('gif', 'GIF'),
    ]
    
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default='image')
    file = models.FileField(upload_to='community/posts/%Y/%m/%d/')
    thumbnail = models.ImageField(upload_to='community/thumbnails/%Y/%m/%d/', blank=True, validators=[validate_image_upload])
    alt_text = models.CharField(max_length=200, blank=True)
    
    # File info
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Media for {self.post.author.user.username}'s post"


class CommunityPostComment(models.Model):
    """
    Comments on community posts
    """
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_comments')
    content = models.TextField()
    
    # Reply system
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.author.user.username} on {self.post}"
    
    @property
    def is_reply(self):
        return self.parent is not None


class CommunityPostLike(models.Model):
    """
    Likes on community posts
    """
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_likes')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['post', 'user']
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} likes {self.post}"


class CommunityPostShare(models.Model):
    """
    Shares/reposts of community posts
    """
    original_post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_shares')
    comment = models.TextField(blank=True, help_text="Optional comment when sharing")
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['original_post', 'shared_by']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shared_by.user.username} shared {self.original_post}"


# Signal handlers to update counters
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=CommunityPostLike)
def increment_like_count(sender, instance, created, **kwargs):
    if created:
        instance.post.likes_count = instance.post.likes.count()
        instance.post.save(update_fields=['likes_count'])

@receiver(post_delete, sender=CommunityPostLike)
def decrement_like_count(sender, instance, **kwargs):
    instance.post.likes_count = instance.post.likes.count()
    instance.post.save(update_fields=['likes_count'])

@receiver(post_save, sender=CommunityPostComment)
def increment_comment_count(sender, instance, created, **kwargs):
    if created:
        instance.post.comments_count = instance.post.comments.count()
        instance.post.save(update_fields=['comments_count'])

@receiver(post_delete, sender=CommunityPostComment)
def decrement_comment_count(sender, instance, **kwargs):
    instance.post.comments_count = instance.post.comments.count()
    instance.post.save(update_fields=['comments_count'])

@receiver(post_save, sender=CommunityPostShare)
def increment_share_count(sender, instance, created, **kwargs):
    if created:
        instance.original_post.shares_count = instance.original_post.shares.count()
        instance.original_post.save(update_fields=['shares_count'])

@receiver(post_delete, sender=CommunityPostShare)
def decrement_share_count(sender, instance, **kwargs):
    instance.original_post.shares_count = instance.original_post.shares.count()
    instance.original_post.save(update_fields=['shares_count'])


# ============================================================================
# PHASE 7, EPIC 7.6: HELP & ONBOARDING MODELS
# ============================================================================

class HelpContent(models.Model):
    """
    Help content/documentation that can be displayed to users contextually.
    Supports organizer onboarding, tooltips, and help overlays.
    """
    AUDIENCE_CHOICES = [
        ('organizer', 'Organizer'),
        ('referee', 'Referee'),
        ('player', 'Player'),
        ('global', 'Global/All Users'),
    ]
    
    # Identity
    key = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Unique identifier (e.g., 'results_inbox_intro')"
    )
    scope = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Context/page where this help applies (e.g., 'organizer_results_inbox')"
    )
    
    # Content
    title = models.CharField(max_length=200)
    body = models.TextField(help_text="Markdown or plain text content")
    html_body = models.TextField(
        blank=True,
        help_text="Pre-rendered HTML (optional, for performance)"
    )
    
    # Targeting
    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default='global',
        help_text="Who should see this help content"
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this content is currently shown"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order when multiple help items exist for same scope"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scope', 'display_order', 'title']
        indexes = [
            models.Index(fields=['scope', 'is_active']),
            models.Index(fields=['audience', 'is_active']),
        ]
        verbose_name = "Help Content"
        verbose_name_plural = "Help Content Items"
    
    def __str__(self):
        return f"{self.key} ({self.scope})"


class HelpOverlay(models.Model):
    """
    Defines a specific tooltip or overlay item that should be shown on a page.
    References HelpContent and specifies visual placement.
    """
    PLACEMENT_CHOICES = [
        ('top', 'Top'),
        ('top-right', 'Top Right'),
        ('right', 'Right'),
        ('bottom-right', 'Bottom Right'),
        ('bottom', 'Bottom'),
        ('bottom-left', 'Bottom Left'),
        ('left', 'Left'),
        ('top-left', 'Top Left'),
        ('center', 'Center'),
    ]
    
    # Reference to help content
    help_content = models.ForeignKey(
        HelpContent,
        on_delete=models.CASCADE,
        related_name='overlays'
    )
    
    # Page/context where this overlay appears
    page_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Page identifier (e.g., 'results_inbox', 'scheduling')"
    )
    
    # Visual placement
    placement = models.CharField(
        max_length=20,
        choices=PLACEMENT_CHOICES,
        default='top-right',
        help_text="Where the overlay should appear on screen"
    )
    
    # Advanced config (JSON)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Advanced configuration (trigger, animation, etc.)"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['page_id', 'display_order']
        indexes = [
            models.Index(fields=['page_id', 'is_active']),
        ]
        verbose_name = "Help Overlay"
        verbose_name_plural = "Help Overlays"
    
    def __str__(self):
        return f"{self.help_content.key} on {self.page_id}"


class OrganizerOnboardingState(models.Model):
    """
    Tracks onboarding wizard progress for organizers.
    Stores which steps have been completed or dismissed per user (and optionally per tournament).
    """
    # User being onboarded
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organizer_onboarding_states'
    )
    
    # Optional tournament scope (if onboarding is per-tournament)
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='onboarding_states',
        help_text="If set, onboarding is tournament-specific"
    )
    
    # Step identifier
    step_key = models.CharField(
        max_length=100,
        help_text="Onboarding step identifier (e.g., 'results_inbox_intro')"
    )
    
    # State
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user completed this step"
    )
    dismissed = models.BooleanField(
        default=False,
        help_text="Whether user dismissed/skipped this step"
    )
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user dismissed this step"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Unique constraint: one record per user+tournament+step
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'tournament', 'step_key'],
                name='unique_onboarding_state_per_user_tournament_step'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'tournament']),
            models.Index(fields=['user', 'step_key']),
        ]
        verbose_name = "Organizer Onboarding State"
        verbose_name_plural = "Organizer Onboarding States"
    
    def __str__(self):
        tournament_part = f" (Tournament {self.tournament_id})" if self.tournament_id else ""
        status = "completed" if self.completed_at else ("dismissed" if self.dismissed else "pending")
        return f"{self.user.username} - {self.step_key}{tournament_part} [{status}]"
    
    @property
    def is_complete(self):
        """Check if this step has been completed."""
        return self.completed_at is not None
    
    @property
    def is_pending(self):
        """Check if this step is still pending (not completed and not dismissed)."""
        return not self.is_complete and not self.dismissed