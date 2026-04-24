"""
Tournament core models - Game, Tournament, CustomField, TournamentVersion.

Source Documents:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md (Section 4.1: Core Models)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 3: Core Tournament Models)
- Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md (Indexes + Constraints)

Architecture Decisions:
- ADR-001: Service Layer Pattern - Business logic goes in services, not models
- ADR-003: Soft Delete Strategy - Tournament uses soft delete for audit trail
- ADR-004: PostgreSQL - Uses JSONB for flexible data, ArrayField for payment methods

Technical Standards:
- PEP 8 compliance with Black formatting (line length: 120)
- Type hints for all public methods
- Google-style docstrings
- Inherits from Module 1.1 base classes (SoftDeleteModel, TimestampedModel)

Assumptions:
- PostgreSQL 15+ with JSONB and ArrayField support
- organizer_id references accounts.User via ForeignKey
- Integration with apps.teams via IntegerField (team rankings for seeding)
- All monetary values use Decimal for precision
"""

from decimal import Decimal
from typing import Dict, List, Optional
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify
from apps.common.models import SoftDeleteModel, TimestampedModel
from apps.common.managers import SoftDeleteManager
from apps.common.validators import validate_document_upload, validate_image_upload


class Tournament(SoftDeleteModel, TimestampedModel):
    """
    Main tournament entity.
    
    Represents a competitive tournament with configuration, participants,
    prizes, and lifecycle management.
    
    Source: PART_3.1_DATABASE_DESIGN_ERD.md, Section 3.1
    ADR-003: Implements soft delete for audit trail
    """
    
    # Status choices (follows state machine from planning docs)
    DRAFT = 'draft'
    PENDING_APPROVAL = 'pending_approval'
    PUBLISHED = 'published'
    REGISTRATION_OPEN = 'registration_open'
    REGISTRATION_CLOSED = 'registration_closed'
    LIVE = 'live'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    ARCHIVED = 'archived'
    
    STATUS_CHOICES = [
        (DRAFT, 'Draft'),
        (PENDING_APPROVAL, 'Pending Approval'),
        (PUBLISHED, 'Published'),
        (REGISTRATION_OPEN, 'Registration Open'),
        (REGISTRATION_CLOSED, 'Registration Closed'),
        (LIVE, 'Live'),
        (COMPLETED, 'Completed'),
        (CANCELLED, 'Cancelled'),
        (ARCHIVED, 'Archived'),
    ]

    # Allowed state transitions — mirrors lifecycle_service.TRANSITIONS graph.
    ALLOWED_TRANSITIONS = {
        DRAFT: frozenset({PUBLISHED, PENDING_APPROVAL, REGISTRATION_OPEN, CANCELLED}),
        PENDING_APPROVAL: frozenset({PUBLISHED, CANCELLED}),
        PUBLISHED: frozenset({REGISTRATION_OPEN, CANCELLED}),
        REGISTRATION_OPEN: frozenset({REGISTRATION_CLOSED, CANCELLED}),
        REGISTRATION_CLOSED: frozenset({LIVE, CANCELLED}),
        LIVE: frozenset({COMPLETED, CANCELLED}),
        COMPLETED: frozenset({ARCHIVED}),
        CANCELLED: frozenset({ARCHIVED}),
        ARCHIVED: frozenset(),
    }
    
    # Format choices
    SINGLE_ELIM = 'single_elimination'
    DOUBLE_ELIM = 'double_elimination'
    ROUND_ROBIN = 'round_robin'
    SWISS = 'swiss'
    GROUP_PLAYOFF = 'group_playoff'
    
    FORMAT_CHOICES = [
        (SINGLE_ELIM, 'Single Elimination'),
        (DOUBLE_ELIM, 'Double Elimination'),
        (ROUND_ROBIN, 'Round Robin'),
        (SWISS, 'Swiss'),
        (GROUP_PLAYOFF, 'Group Stage + Playoff'),
    ]
    
    # Backward-compatible aliases (legacy test references)
    SINGLE_ELIMINATION = SINGLE_ELIM
    DOUBLE_ELIMINATION = DOUBLE_ELIM
    
    # Participation type choices
    TEAM = 'team'
    SOLO = 'solo'
    
    PARTICIPATION_TYPE_CHOICES = [
        (TEAM, 'Team'),
        (SOLO, 'Solo/Individual'),
    ]
    
    # Payment method choices (used in ArrayField)
    DELTACOIN = 'deltacoin'
    BKASH = 'bkash'
    NAGAD = 'nagad'
    ROCKET = 'rocket'
    BANK_TRANSFER = 'bank_transfer'
    
    PAYMENT_METHOD_CHOICES = [
        (DELTACOIN, 'DeltaCoin'),
        (BKASH, 'bKash'),
        (NAGAD, 'Nagad'),
        (ROCKET, 'Rocket'),
        (BANK_TRANSFER, 'Bank Transfer'),
    ]
    
    # Basic information
    name = models.CharField(max_length=200, help_text='Tournament name')
    slug = models.SlugField(max_length=250, unique=True, db_index=True)
    description = models.TextField(help_text='Tournament description and overview')
    
    # Organizer (ForeignKey to accounts.User)
    organizer = models.ForeignKey(
        'accounts.User',
        on_delete=models.PROTECT,
        related_name='organized_tournaments',
        help_text='User who created this tournament'
    )
    is_official = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this is an official DeltaCrown tournament'
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this tournament is featured on the homepage'
    )
    
    # Game (ForeignKey to games.Game — canonical source)
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.PROTECT,
        related_name='tournaments',
        help_text='Game being played in this tournament'
    )
    
    # Tournament format
    format = models.CharField(
        max_length=50,
        choices=FORMAT_CHOICES,
        default=SINGLE_ELIM,
        help_text='Bracket format for the tournament'
    )
    
    # Participation type
    participation_type = models.CharField(
        max_length=20,
        choices=PARTICIPATION_TYPE_CHOICES,
        default=TEAM,
        help_text='Whether teams or individuals participate'
    )
    
    # Platform choices
    PC = 'pc'
    MOBILE = 'mobile'
    PS5 = 'ps5'
    XBOX = 'xbox'
    SWITCH = 'switch'
    
    PLATFORM_CHOICES = [
        (PC, 'PC'),
        (MOBILE, 'Mobile'),
        (PS5, 'PlayStation 5'),
        (XBOX, 'Xbox Series X/S'),
        (SWITCH, 'Nintendo Switch'),
    ]
    
    # Mode choices
    ONLINE = 'online'
    LAN = 'lan'
    HYBRID = 'hybrid'
    
    MODE_CHOICES = [
        (ONLINE, 'Online'),
        (LAN, 'LAN'),
        (HYBRID, 'Hybrid (Online + LAN Finals)'),
    ]
    
    # Platform & Mode
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        default=PC,
        db_index=True,
        help_text='Gaming platform for this tournament'
    )
    mode = models.CharField(
        max_length=10,
        choices=MODE_CHOICES,
        default=ONLINE,
        db_index=True,
        help_text='Tournament mode - affects location requirements'
    )
    
    # Venue information (for LAN/Hybrid tournaments)
    venue_name = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Venue name for LAN tournaments'
    )
    venue_address = models.TextField(
        blank=True,
        default='',
        help_text='Complete venue address for LAN tournaments'
    )
    venue_city = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text='City where LAN event is held'
    )
    venue_map_url = models.URLField(
        blank=True,
        default='',
        help_text='Google Maps link to venue'
    )
    
    # Capacity
    max_participants = models.PositiveIntegerField(
        default=16,
        validators=[MinValueValidator(2), MaxValueValidator(256)],
        help_text='Maximum number of participants/teams'
    )
    min_participants = models.PositiveIntegerField(
        default=2,
        validators=[MinValueValidator(2)],
        help_text='Minimum participants needed to start'
    )
    
    # Dates
    registration_start = models.DateTimeField(help_text='When registration opens')
    registration_end = models.DateTimeField(help_text='When registration closes')
    registration_form_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text='Form configuration overrides for this tournament (JSONB)'
    )
    tournament_start = models.DateTimeField(help_text='When tournament begins')
    tournament_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When tournament ends (set automatically)'
    )
    timezone_name = models.CharField(
        max_length=64,
        default='Asia/Dhaka',
        blank=True,
        help_text='IANA timezone name for display (e.g. Asia/Dhaka, UTC). Does not affect stored UTC datetimes.'
    )

    # Prize pool
    prize_pool = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Total prize pool amount'
    )
    prize_currency = models.CharField(
        max_length=10,
        default='BDT',
        help_text='Currency for prize pool (BDT, USD, etc.)'
    )
    prize_deltacoin = models.PositiveIntegerField(
        default=0,
        help_text='Prize pool in DeltaCoins'
    )
    prize_distribution = models.JSONField(
        default=dict,
        blank=True,
        help_text='Prize distribution by placement (JSONB): {"1": "50%", "2": "30%", "3": "20%"}'
    )
    
    # Entry fee
    has_entry_fee = models.BooleanField(
        default=False,
        help_text='Whether tournament has an entry fee'
    )
    entry_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text='Entry fee amount'
    )
    entry_fee_currency = models.CharField(
        max_length=10,
        default='BDT',
        help_text='Currency for entry fee'
    )
    entry_fee_deltacoin = models.PositiveIntegerField(
        default=0,
        help_text='Entry fee in DeltaCoins'
    )
    
    # Payment deadline (P4-T02: Auto-expiry)
    payment_deadline_hours = models.PositiveIntegerField(
        default=48,
        help_text='Hours after registration to submit payment before auto-expiry (0 = no deadline)'
    )
    
    # Payment methods (PostgreSQL ArrayField)
    payment_methods = ArrayField(
        models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES),
        default=list,
        blank=True,
        help_text='Accepted payment methods'
    )
    
    # Refund policy
    REFUND_POLICY_CHOICES = [
        ('no_refund', 'No Refunds'),
        ('refund_until_checkin', 'Refund Until Check-In'),
        ('refund_until_bracket', 'Refund Until Bracket Generation'),
        ('full_refund', 'Full Refund Anytime'),
        ('custom', 'Custom Policy'),
    ]
    
    refund_policy = models.CharField(
        max_length=30,
        choices=REFUND_POLICY_CHOICES,
        default='no_refund',
        blank=True,
        help_text='Refund policy for entry fees'
    )
    
    refund_policy_text = models.TextField(
        blank=True,
        default='',
        help_text='Custom refund policy text (shown to registrants when policy is "custom")'
    )
    
    # Fee waiver
    enable_fee_waiver = models.BooleanField(
        default=False,
        help_text='Enable automatic fee waiver for top teams'
    )
    fee_waiver_top_n_teams = models.PositiveIntegerField(
        default=0,
        help_text='Number of top teams eligible for fee waiver'
    )
    
    # Media
    banner_image = models.ImageField(
        upload_to='tournaments/banners/',
        null=True,
        blank=True,
        help_text='Tournament banner image',
        validators=[validate_image_upload],
    )
    thumbnail_image = models.ImageField(
        upload_to='tournaments/thumbnails/',
        null=True,
        blank=True,
        help_text='Tournament thumbnail for listings',
        validators=[validate_image_upload],
    )
    rules_pdf = models.FileField(
        upload_to='tournaments/rules/',
        null=True,
        blank=True,
        help_text='Tournament rules PDF file',
        validators=[validate_document_upload],
    )
    promo_video_url = models.URLField(
        blank=True,
        help_text='YouTube/Vimeo promo video URL'
    )
    
    # Streaming
    stream_youtube_url = models.URLField(
        blank=True,
        help_text='Official YouTube stream URL'
    )
    stream_twitch_url = models.URLField(
        blank=True,
        help_text='Official Twitch stream URL'
    )
    
    # Social & Contact Links (Hub Resources Module)
    social_twitter = models.URLField(
        blank=True,
        default='',
        help_text='Organizer X (Twitter) profile URL'
    )
    social_instagram = models.URLField(
        blank=True,
        default='',
        help_text='Organizer Instagram URL'
    )
    social_youtube = models.URLField(
        blank=True,
        default='',
        help_text='Organizer YouTube channel URL'
    )
    social_website = models.URLField(
        blank=True,
        default='',
        help_text='Organizer website URL'
    )
    social_discord = models.URLField(
        blank=True,
        default='',
        help_text='Discord server invite URL'
    )
    discord_webhook_url = models.URLField(
        blank=True,
        default='',
        help_text='Discord webhook URL for automated tournament notifications'
    )
    contact_email = models.EmailField(
        blank=True,
        default='',
        help_text='Organizer contact email for participants'
    )
    contact_phone = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text='Organizer phone number for participants (WhatsApp-enabled)'
    )
    social_facebook = models.URLField(
        blank=True,
        default='',
        help_text='Organizer Facebook page/group URL'
    )
    social_tiktok = models.URLField(
        blank=True,
        default='',
        help_text='Organizer TikTok profile URL'
    )
    support_info = models.TextField(
        blank=True,
        default='',
        help_text='Custom support/dispute instructions for participants (shown in Hub)'
    )
    
    # Features (enable/disable various tournament features)
    enable_check_in = models.BooleanField(
        default=True,
        help_text='Require participants to check in before matches'
    )
    check_in_minutes_before = models.PositiveIntegerField(
        default=15,
        help_text='Check-in window duration in minutes'
    )
    check_in_closes_minutes_before = models.PositiveIntegerField(
        default=10,
        help_text='Check-in closes this many minutes before tournament start'
    )
    enable_dynamic_seeding = models.BooleanField(
        default=False,
        help_text='Use team rankings for seeding instead of registration order'
    )
    enable_live_updates = models.BooleanField(
        default=True,
        help_text='Enable WebSocket live updates for spectators'
    )
    enable_certificates = models.BooleanField(
        default=True,
        help_text='Generate certificates for winners'
    )
    enable_challenges = models.BooleanField(
        default=False,
        help_text='Enable bonus challenges during tournament'
    )
    enable_fan_voting = models.BooleanField(
        default=False,
        help_text='Enable spectator voting/predictions'
    )
    enable_no_show_timer = models.BooleanField(
        default=False,
        help_text='Automatically forfeit matches when both teams fail to start within the timeout window'
    )
    auto_forfeit_no_shows = models.BooleanField(
        default=False,
        help_text='Automatically issue no-show forfeits for non-started matches when organizer policy allows'
    )
    waitlist_auto_promote = models.BooleanField(
        default=False,
        help_text='Automatically promote waitlisted registrations when slots become available'
    )
    no_show_timeout_minutes = models.PositiveIntegerField(
        default=5,
        help_text='Minutes after scheduled start before a no-show forfeit is issued (requires enable_no_show_timer)'
    )
    max_waitlist_size = models.PositiveIntegerField(
        default=0,
        help_text='Maximum waitlist size (0 means unlimited)'
    )

    # Guest team settings (P2-T02)
    max_guest_teams = models.PositiveIntegerField(
        default=0,
        help_text='Maximum number of guest team registrations allowed (0 = disabled)'
    )
    
    # Display name override (P2-T06)
    allow_display_name_override = models.BooleanField(
        default=False,
        help_text='Allow participants to set a custom display name for brackets and match rooms'
    )
    
    # Rules
    rules_text = models.TextField(
        blank=True,
        help_text='Tournament rules in text format'
    )
    
    # Terms & Conditions (NEW - from improvement plan)
    terms_and_conditions = models.TextField(
        blank=True,
        help_text='Terms and conditions that all participants must agree to'
    )
    terms_pdf = models.FileField(
        upload_to='tournaments/terms/',
        null=True,
        blank=True,
        help_text='Terms & Conditions PDF document (optional)',
        validators=[validate_document_upload],
    )
    require_terms_acceptance = models.BooleanField(
        default=True,
        help_text='Require participants to explicitly accept terms during registration'
    )
    
    # Status
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=DRAFT,
        db_index=True,
        help_text='Current tournament status'
    )
    
    # Cancellation info surfaced on the unified public detail page.
    cancellation_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for tournament cancellation (shown to participants)'
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When tournament was cancelled'
    )
    
    # Published timestamp
    published_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When tournament was published'
    )
    
    # Denormalized stats (for performance)
    total_registrations = models.PositiveIntegerField(
        default=0,
        help_text='Total number of registrations'
    )
    total_matches = models.PositiveIntegerField(
        default=0,
        help_text='Total number of matches'
    )
    completed_matches = models.PositiveIntegerField(
        default=0,
        help_text='Number of completed matches'
    )
    
    # SEO
    meta_description = models.TextField(
        blank=True,
        help_text='Meta description for SEO'
    )
    meta_keywords = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
        help_text='SEO keywords'
    )
    
    # Advanced per-tournament configuration (JSONB)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Advanced tournament configuration and feature flags (JSONB)'
    )

    # Dynamic match configuration authored from TOC Rules & Info tab
    match_settings = models.JSONField(
        default=dict,
        blank=True,
        help_text='Game-specific match configuration rendered in match lobby rules (JSONB)'
    )
    
    # Managers
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        ordering = ['-tournament_start']
        verbose_name = 'Tournament'
        verbose_name_plural = 'Tournaments'
        indexes = [
            models.Index(fields=['status', 'tournament_start']),
            models.Index(fields=['game', 'status']),
            models.Index(fields=['organizer', 'status']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_official', 'tournament_start']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(min_participants__gte=2),
                name='min_participants_at_least_2'
            ),
            models.CheckConstraint(
                condition=models.Q(max_participants__gte=models.F('min_participants')),
                name='max_participants_gte_min_participants'
            ),
        ]
    
    # Platform & Mode Helper Methods
    def is_online(self) -> bool:
        """Check if tournament is online only."""
        return self.mode == self.ONLINE
    
    def is_lan(self) -> bool:
        """Check if tournament has LAN component."""
        return self.mode in [self.LAN, self.HYBRID]
    
    def requires_venue(self) -> bool:
        """Check if tournament requires venue information."""
        return self.is_lan()
    
    def get_platform_display_name(self) -> str:
        """Get human-readable platform name."""
        return dict(self.PLATFORM_CHOICES).get(self.platform, self.platform)
    
    def get_mode_display_name(self) -> str:
        """Get human-readable mode name."""
        return dict(self.MODE_CHOICES).get(self.mode, self.mode)
    
    def get_platform_icon(self) -> str:
        """Get FontAwesome icon class for platform."""
        icons = {
            self.PC: 'fa-desktop',
            self.MOBILE: 'fa-mobile-alt',
            self.PS5: 'fa-playstation',
            self.XBOX: 'fa-xbox',
            self.SWITCH: 'fa-gamepad',
        }
        return icons.get(self.platform, 'fa-gamepad')
    
    def get_mode_icon(self) -> str:
        """Get FontAwesome icon class for mode."""
        icons = {
            self.ONLINE: 'fa-wifi',
            self.LAN: 'fa-map-marker-alt',
            self.HYBRID: 'fa-globe',
        }
        return icons.get(self.mode, 'fa-globe')
    
    def __str__(self) -> str:
        return f"{self.name} ({self.game.name})"
    
    def save(self, *args, **kwargs):
        """
        Auto-generate slug from name if not provided.
        Auto-assign official organizer for official tournaments.
        Enforce state-machine transition rules on status changes.
        """
        # ── Status transition validation ────────────────────────────────
        update_fields = kwargs.get('update_fields')
        skip_status = getattr(self, '_skip_status_validation', False)

        if (
            not skip_status
            and self.pk
            and (update_fields is None or 'status' in update_fields)
        ):
            old_status = (
                Tournament.objects.filter(pk=self.pk)
                .values_list('status', flat=True)
                .first()
            )
            if old_status is not None and old_status != self.status:
                allowed = self.ALLOWED_TRANSITIONS.get(old_status, frozenset())
                if self.status not in allowed:
                    raise ValueError(
                        f"Invalid tournament status transition: "
                        f"'{old_status}' → '{self.status}'. "
                        f"Allowed from '{old_status}': {sorted(allowed)}"
                    )
                # T2-5: Invalidate detail page cache on status change
                try:
                    from django.core.cache import cache
                    cache.delete_many(
                        cache.keys(f"*detail_page*{self.slug}*")
                        if hasattr(cache, 'keys')
                        else []
                    )
                except Exception:
                    pass

        # ── Slug generation ─────────────────────────────────────────────
        if not self.slug:
            base_slug = slugify(self.name)
            unique_slug = base_slug
            counter = 1
            
            # Ensure slug is unique
            while Tournament.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = unique_slug
        
        # Auto-assign organizer for official tournaments
        if self.is_official and not self.organizer_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            # Get or create the official DeltaCrown account
            official_user, created = User.objects.get_or_create(
                username='deltacrown_official',
                defaults={
                    'email': 'official@deltacrown.gg',
                    'first_name': 'DeltaCrown',
                    'last_name': 'Official',
                    'is_staff': True,
                }
            )
            
            self.organizer = official_user
        
        super().save(*args, **kwargs)
    
    def clean(self):
        """
        Validate tournament data.
        
        Ensures:
        - LAN/Hybrid tournaments have venue information
        - Dates are in correct order
        - Min/max participants are valid
        """
        from django.core.exceptions import ValidationError
        errors = {}
        
        # Validate venue for LAN tournaments
        if self.requires_venue() and not self.venue_name:
            errors['venue_name'] = 'Venue name is required for LAN and Hybrid tournaments.'
        
        if self.requires_venue() and not self.venue_address:
            errors['venue_address'] = 'Venue address is required for LAN and Hybrid tournaments.'
        
        # Validate dates
        if self.registration_start and self.registration_end:
            if self.registration_end <= self.registration_start:
                errors['registration_end'] = 'Registration end must be after registration start.'
        
        if self.registration_end and self.tournament_start:
            if self.tournament_start < self.registration_end:
                errors['tournament_start'] = 'Tournament start must be after registration closes.'
        
        if errors:
            raise ValidationError(errors)
        
        super().clean()
    
    def is_registration_open(self) -> bool:
        """
        Check if registration is currently open.
        
        Returns:
            True if registration is open and within the time window
        """
        now = timezone.now()
        return (
            self.status == self.REGISTRATION_OPEN
            and self.registration_start <= now <= self.registration_end
        )
    
    def has_registration_started(self) -> bool:
        """
        Check if registration has started (past the start date).
        
        Returns:
            True if registration start date has passed
        """
        now = timezone.now()
        return now >= self.registration_start
    
    def spots_remaining(self) -> int:
        """
        Calculate number of spots remaining.
        
        Returns:
            Number of available spots (0 if full or over-subscribed)
        """
        return max(0, self.max_participants - self.active_registration_count())

    def active_registration_count(self) -> int:
        """Return live active registration count used for capacity checks."""
        from apps.tournaments.models.registration import Registration

        return Registration.objects.filter(
            tournament=self,
            status__in=[
                Registration.PENDING,
                Registration.PAYMENT_SUBMITTED,
                Registration.CONFIRMED,
            ],
            is_deleted=False,
        ).count()
    
    def is_full(self) -> bool:
        """Check if tournament has reached capacity."""
        if self.max_participants <= 0:
            return False
        return self.active_registration_count() >= self.max_participants
    
    # =========================================================================
    # STAGE TRACKING FOR MULTI-STAGE TOURNAMENTS (GROUP_PLAYOFF format)
    # =========================================================================
    
    STAGE_GROUP = "group_stage"
    STAGE_KNOCKOUT = "knockout_stage"

    def get_effective_status(self) -> str:
        """
        Return the effective operational status considering inner-stage state.

        Truth contract (single source of truth across TOC + HUB + Finalize):

          * A non-deleted `TournamentResult` is the strongest signal that the
            tournament is finished. If one exists with a winner, the surface
            status is **always** COMPLETED — even if `self.status` is still
            `live` (auto-finalize hasn't run yet) and even if stale
            `config.stages[].status == 'live'` would otherwise mask it.

          * If `status == COMPLETED` AND a TournamentResult exists, the
            persisted COMPLETED is also authoritative — same rationale.

          * For GROUP_PLAYOFF tournaments WITHOUT a TournamentResult: if the
            model-level status drifted to COMPLETED but the knockout stage is
            still marked live in config, surface LIVE so the UI keeps the
            operational controls visible.

          * Otherwise return the persisted status as-is.
        """
        status = self.status

        # Step 1: TournamentResult presence trumps everything else.
        result_with_winner = False
        try:
            cache = getattr(self, '_prefetched_objects_cache', None) or {}
            if 'result' in cache:
                cached_results = list(cache['result'])
                if cached_results and getattr(cached_results[0], 'winner_id', None):
                    result_with_winner = True
        except (AttributeError, TypeError):
            pass
        if not result_with_winner:
            try:
                from apps.tournaments.models.result import TournamentResult
                result_with_winner = TournamentResult.objects.filter(
                    tournament_id=self.pk, is_deleted=False,
                ).exclude(winner_id__isnull=True).exists()
            except Exception:
                # Defensive: never let this helper raise.
                result_with_winner = False

        if result_with_winner:
            return self.COMPLETED

        # Step 2: legacy COMPLETED override — only relevant for group_playoff
        # when a TournamentResult was never created and stale config still
        # marks knockout as live.
        if status == self.COMPLETED and self.format == self.GROUP_PLAYOFF:
            config = self.config or {}
            stage = config.get("current_stage")
            stages = config.get("stages", [])
            for s in stages:
                if s.get("name") == self.STAGE_KNOCKOUT and s.get("status") == "live":
                    return self.LIVE
            if stage == self.STAGE_KNOCKOUT:
                return self.LIVE

        return status

    def get_current_stage(self) -> Optional[str]:
        """
        Get current tournament stage for GROUP_PLAYOFF tournaments.
        
        Returns:
            - "group_stage": Currently in group stage
            - "knockout_stage": Currently in knockout/playoff stage
            - None: Not a multi-stage tournament
        
        Example:
            >>> tournament = Tournament.objects.get(format=Tournament.GROUP_PLAYOFF)
            >>> stage = tournament.get_current_stage()
            >>> print(stage)  # "group_stage" or "knockout_stage"
        """
        if self.format != self.GROUP_PLAYOFF:
            return None
        
        config = self.config or {}
        return config.get("current_stage", self.STAGE_GROUP)
    
    def set_current_stage(self, stage: str, save: bool = True) -> None:
        """
        Set the current tournament stage.
        
        Args:
            stage: Stage name (STAGE_GROUP or STAGE_KNOCKOUT)
            save: Whether to save to database immediately
        
        Example:
            >>> tournament.set_current_stage(Tournament.STAGE_KNOCKOUT)
        """
        if self.format != self.GROUP_PLAYOFF:
            return  # Ignore for single-phase formats
        
        config = self.config or {}
        config["current_stage"] = stage
        self.config = config
        if save:
            self.save(update_fields=["config"])
    
    def add_stage_history_entry(self, name: str, status: str, **extra) -> None:
        """
        Append a stage history entry to config["stages"].
        
        Args:
            name: Stage name (e.g., "group_stage", "knockout_stage")
            status: Stage status (e.g., "completed", "live", "pending")
            **extra: Additional fields (completed_at, started_at, etc.)
        
        Example:
            >>> tournament.add_stage_history_entry(
            ...     name="group_stage",
            ...     status="completed",
            ...     completed_at=timezone.now().isoformat()
            ... )
        """
        config = self.config or {}
        stages = config.get("stages", [])
        entry = {"name": name, "status": status}
        entry.update(extra)
        stages.append(entry)
        config["stages"] = stages
        self.config = config
        self.save(update_fields=["config"])


class CustomField(models.Model):
    """
    User-defined custom fields for tournaments.
    
    Allows organizers to add dynamic fields to tournaments for additional
    information (Discord server, special requirements, etc.).
    
    Source: PART_3.1_DATABASE_DESIGN_ERD.md, Section 3.3
    """
    
    # Field type choices
    TEXT = 'text'
    NUMBER = 'number'
    MEDIA = 'media'
    TOGGLE = 'toggle'
    DATE = 'date'
    URL = 'url'
    DROPDOWN = 'dropdown'
    
    FIELD_TYPE_CHOICES = [
        (TEXT, 'Text'),
        (NUMBER, 'Number'),
        (MEDIA, 'Media Upload'),
        (TOGGLE, 'Toggle (Yes/No)'),
        (DATE, 'Date'),
        (URL, 'URL'),
        (DROPDOWN, 'Dropdown'),
    ]
    
    # Fields
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='custom_fields',
        help_text='Tournament this field belongs to'
    )
    
    field_name = models.CharField(
        max_length=100,
        help_text='Display name of the field'
    )
    field_key = models.SlugField(
        max_length=120,
        help_text='Unique key for form field name'
    )
    
    field_type = models.CharField(
        max_length=20,
        choices=FIELD_TYPE_CHOICES,
        default=TEXT,
        help_text='Type of field (text, number, etc.)'
    )
    
    # Configuration (JSONB for flexibility)
    field_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Field configuration (min_length, max_length, options, etc.)'
    )
    
    # Value storage (JSONB)
    field_value = models.JSONField(
        default=dict,
        blank=True,
        help_text='Actual field value storage'
    )
    
    # Display options
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order (lower numbers first)'
    )
    is_required = models.BooleanField(
        default=False,
        help_text='Whether this field is required'
    )
    help_text = models.CharField(
        max_length=200,
        blank=True,
        help_text='Help text shown to users'
    )
    
    class Meta:
        ordering = ['order', 'field_name']
        verbose_name = 'Custom Field'
        verbose_name_plural = 'Custom Fields'
        unique_together = [['tournament', 'field_key']]
        indexes = [
            models.Index(fields=['tournament', 'order']),
        ]
    
    def __str__(self) -> str:
        return f"{self.tournament.name} - {self.field_name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate field_key from field_name if not provided."""
        if not self.field_key:
            self.field_key = slugify(self.field_name)
        super().save(*args, **kwargs)


class TournamentVersion(models.Model):
    """
    Configuration version control for tournaments.
    
    Stores snapshots of tournament configuration for rollback capability
    and audit trail.
    
    Source: PART_3.1_DATABASE_DESIGN_ERD.md, Section 3.4
    """
    
    # Fields
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='versions',
        help_text='Tournament this version belongs to'
    )
    
    version_number = models.PositiveIntegerField(
        help_text='Sequential version number'
    )
    
    # Complete snapshot (JSONB)
    version_data = models.JSONField(
        help_text='Complete tournament configuration at this version'
    )
    
    # Change tracking
    change_summary = models.TextField(
        help_text='Human-readable summary of changes'
    )
    changed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='tournament_version_changes',
        help_text='User who made this change'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When this version was created'
    )
    
    # Rollback tracking
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this version is the active one'
    )
    rolled_back_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this version was rolled back to'
    )
    rolled_back_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_version_rollbacks',
        help_text='User who performed the rollback'
    )
    
    class Meta:
        ordering = ['-version_number']
        verbose_name = 'Tournament Version'
        verbose_name_plural = 'Tournament Versions'
        unique_together = [('tournament', 'version_number')]
        indexes = [
            models.Index(fields=['tournament', '-version_number']),
            models.Index(fields=['changed_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.tournament.name} - v{self.version_number}"


# =============================================================================
# STUB MODELS FOR LEGACY MIGRATION COMPATIBILITY
# =============================================================================
# These stub models satisfy legacy migration references from economy, notifications,
# and teams apps that reference tournaments.match.
# Full implementation will be provided in:
# - Module 1.4 (Bracket & Match Models)
# 
# Note: Registration model has been moved to apps/tournaments/models/registration.py
# (Module 1.3 complete implementation)
#
# Note: Match and Dispute models have been moved to apps/tournaments/models/match.py
# (Module 1.4 complete implementation)
# =============================================================================
