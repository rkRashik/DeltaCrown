"""
Tournament Template Model

Allows organizers to save tournament configurations as reusable templates
for faster tournament creation.

Source: BACKEND_ONLY_BACKLOG.md, Module 2.3
ADR-001: Service Layer Architecture
ADR-004: PostgreSQL JSONB for template storage
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.postgres.fields import ArrayField
from apps.common.models import TimestampedModel, SoftDeleteModel


class TournamentTemplate(TimestampedModel, SoftDeleteModel):
    """
    Reusable tournament configuration template.
    
    Stores tournament settings, game configs, rules, and prize structures
    that can be applied to create new tournaments quickly.
    
    **Visibility Levels**:
    - PRIVATE: Only visible to creator (organizer)
    - ORG: Visible to organization members
    - GLOBAL: Visible to all users (public templates)
    
    **Template Payload** (JSONB field):
    - format/brackets (tournament format)
    - game configs (from GameConfigService)
    - default registration settings
    - payment settings (entry fee, methods)
    - scheduling defaults (best-of, rounds, check-in)
    - prize distribution
    - custom fields schema
    """
    
    # Visibility choices
    PRIVATE = 'private'
    ORG = 'org'
    GLOBAL = 'global'
    
    VISIBILITY_CHOICES = [
        (PRIVATE, 'Private (Creator Only)'),
        (ORG, 'Organization'),
        (GLOBAL, 'Global (Public)'),
    ]
    
    # Basic information
    name = models.CharField(
        max_length=200,
        help_text='Template name (e.g., "5v5 Valorant Tournament")'
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        db_index=True,
        help_text='URL-friendly slug (auto-generated from name)'
    )
    description = models.TextField(
        blank=True,
        help_text='Template description and notes'
    )
    
    # Creator
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='tournament_templates',
        help_text='User who created this template'
    )
    
    # Game reference (optional - can be multi-game template)
    game = models.ForeignKey(
        'Game',
        on_delete=models.PROTECT,
        related_name='templates',
        null=True,
        blank=True,
        help_text='Game for this template (null = multi-game)'
    )
    
    # Visibility
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default=PRIVATE,
        db_index=True,
        help_text='Who can see and use this template'
    )
    
    # Organization (for ORG visibility)
    organization_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Organization ID from DeltaCrown organizations app (no ForeignKey)'
    )
    
    # Template payload (JSONB)
    template_config = models.JSONField(
        default=dict,
        help_text='''Tournament configuration template (JSONB). Structure:
        {
            "format": "single_elimination",
            "participation_type": "team",
            "max_participants": 16,
            "min_participants": 4,
            "has_entry_fee": true,
            "entry_fee_amount": "500.00",
            "entry_fee_currency": "BDT",
            "entry_fee_deltacoin": 0,
            "payment_methods": ["bkash", "nagad", "deltacoin"],
            "prize_pool": "10000.00",
            "prize_currency": "BDT",
            "prize_deltacoin": 0,
            "prize_distribution": {"1": "50%", "2": "30%", "3": "20%"},
            "enable_check_in": true,
            "check_in_minutes_before": 15,
            "enable_dynamic_seeding": false,
            "enable_live_updates": true,
            "enable_certificates": true,
            "enable_fee_waiver": false,
            "fee_waiver_top_n_teams": 0,
            "custom_fields": [
                {
                    "field_name": "Discord Server",
                    "field_type": "url",
                    "is_required": true,
                    "field_config": {"pattern": "^https://discord\\.gg/"}
                }
            ],
            "match_settings": {
                "default_best_of": 1,
                "auto_schedule_matches": false,
                "match_duration_minutes": 60
            }
        }
        '''
    )
    
    # Usage stats
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of times this template has been applied'
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When this template was last used'
    )
    
    # Active status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this template is active (can be used)'
    )
    
    class Meta:
        db_table = 'tournaments_tournamenttemplate'
        verbose_name = 'Tournament Template'
        verbose_name_plural = 'Tournament Templates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'is_active'], name='template_creator_active_idx'),
            models.Index(fields=['game', 'visibility'], name='template_game_visibility_idx'),
            models.Index(fields=['visibility', 'is_active'], name='template_visibility_active_idx'),
        ]
        constraints = [
            # Unique constraint for (created_by, game, name) to prevent duplicates
            models.UniqueConstraint(
                fields=['created_by', 'game', 'name'],
                name='unique_template_per_creator_game_name',
                condition=models.Q(is_deleted=False),
            ),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_visibility_display()})"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            from django.utils.text import slugify
            import uuid
            base_slug = slugify(self.name)
            unique_slug = f"{base_slug}-{uuid.uuid4().hex[:8]}"
            self.slug = unique_slug
        super().save(*args, **kwargs)
    
    def increment_usage(self):
        """Increment usage count and update last_used_at timestamp."""
        from django.utils import timezone
        self.usage_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['usage_count', 'last_used_at'])
