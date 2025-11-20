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


class Game(models.Model):
    """
    Game definitions for supported tournament games.
    
    Defines game-specific configuration including team size, result types,
    and integration with user profiles for game IDs.
    
    Source: PART_3.1_DATABASE_DESIGN_ERD.md, Section 3.2
    """
    
    # Team size choices
    TEAM_SIZE_1V1 = 1
    TEAM_SIZE_2V2 = 2
    TEAM_SIZE_3V3 = 3
    TEAM_SIZE_4V4 = 4
    TEAM_SIZE_5V5 = 5
    TEAM_SIZE_VARIABLE = 0
    
    TEAM_SIZE_CHOICES = [
        (TEAM_SIZE_1V1, '1v1'),
        (TEAM_SIZE_2V2, '2v2'),
        (TEAM_SIZE_3V3, '3v3'),
        (TEAM_SIZE_4V4, '4v4'),
        (TEAM_SIZE_5V5, '5v5'),
        (TEAM_SIZE_VARIABLE, 'Variable'),
    ]
    
    # Result type choices
    MAP_SCORE = 'map_score'
    BEST_OF = 'best_of'
    POINT_BASED = 'point_based'
    
    RESULT_TYPE_CHOICES = [
        (MAP_SCORE, 'Map Score (e.g., 13-11)'),
        (BEST_OF, 'Best of X'),
        (POINT_BASED, 'Point Based'),
    ]
    
    # Fields
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    icon = models.ImageField(upload_to='games/icons/', help_text='Game icon/logo image')
    
    default_team_size = models.PositiveIntegerField(
        choices=TEAM_SIZE_CHOICES,
        default=TEAM_SIZE_5V5,
        help_text='Default team size for this game'
    )
    
    profile_id_field = models.CharField(
        max_length=50,
        help_text="Field name in UserProfile (e.g., 'riot_id', 'steam_id')"
    )
    
    default_result_type = models.CharField(
        max_length=20,
        choices=RESULT_TYPE_CHOICES,
        default=MAP_SCORE,
        help_text='How match results are recorded'
    )
    
    # Game-specific configuration (JSONB)
    game_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Game configuration schema and settings (JSONB)'
    )
    
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this game is actively supported'
    )
    
    description = models.TextField(blank=True, help_text='Game description and notes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Media fields (uploaded via Django admin)
    banner = models.ImageField(upload_to='games/banners/', blank=True, null=True, help_text='Game banner image')
    card_image = models.ImageField(upload_to='games/cards/', blank=True, null=True, help_text='Game card/thumbnail image')
    logo = models.ImageField(upload_to='games/logos/', blank=True, null=True, help_text='Game logo image')
    
    # Presentation fields
    primary_color = models.CharField(max_length=20, blank=True, null=True, help_text='Primary brand color (hex)')
    secondary_color = models.CharField(max_length=20, blank=True, null=True, help_text='Secondary brand color (hex)')
    
    # Metadata fields
    category = models.CharField(max_length=50, blank=True, null=True, help_text='Game category (MOBA, FPS, etc.)')
    platform = models.CharField(max_length=50, blank=True, null=True, help_text='Platform (PC, Mobile, Console)')
    
    # Team structure
    min_team_size = models.PositiveIntegerField(default=1, help_text='Minimum team size')
    max_team_size = models.PositiveIntegerField(default=5, help_text='Maximum team size')
    roster_rules = models.JSONField(default=dict, blank=True, help_text='Roster rules and structure (JSONB)')
    
    # Roles (optional)
    roles = models.JSONField(default=list, blank=True, help_text='Available roles for this game (JSONB array)')
    
    # Result logic
    result_logic = models.JSONField(default=dict, blank=True, help_text='Result calculation logic (JSONB)')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'name']),
        ]
    
    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


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
    
    # Game (ForeignKey to Game)
    game = models.ForeignKey(
        'Game',
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
    
    # Capacity
    max_participants = models.PositiveIntegerField(
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
    tournament_start = models.DateTimeField(help_text='When tournament begins')
    tournament_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When tournament ends (set automatically)'
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
    
    # Payment methods (PostgreSQL ArrayField)
    payment_methods = ArrayField(
        models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES),
        default=list,
        blank=True,
        help_text='Accepted payment methods'
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
        help_text='Tournament banner image'
    )
    thumbnail_image = models.ImageField(
        upload_to='tournaments/thumbnails/',
        null=True,
        blank=True,
        help_text='Tournament thumbnail for listings'
    )
    rules_pdf = models.FileField(
        upload_to='tournaments/rules/',
        null=True,
        blank=True,
        help_text='Tournament rules PDF file'
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
        help_text='Terms & Conditions PDF document (optional)'
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
                check=models.Q(min_participants__gte=2),
                name='min_participants_at_least_2'
            ),
            models.CheckConstraint(
                check=models.Q(max_participants__gte=models.F('min_participants')),
                name='max_participants_gte_min_participants'
            ),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.game.name})"
    
    def save(self, *args, **kwargs):
        """
        Auto-generate slug from name if not provided.
        Auto-assign official organizer for official tournaments.
        """
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
    
    def spots_remaining(self) -> int:
        """
        Calculate number of spots remaining.
        
        Returns:
            Number of available spots (0 if full or over-subscribed)
        """
        return max(0, self.max_participants - self.total_registrations)
    
    def is_full(self) -> bool:
        """Check if tournament has reached capacity."""
        return self.total_registrations >= self.max_participants


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
