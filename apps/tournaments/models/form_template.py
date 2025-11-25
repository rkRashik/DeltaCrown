"""
Dynamic Form Builder Models

Sprint 1: Database Foundation
Created: November 25, 2025

This module contains models for the dynamic form builder system that allows
tournament organizers to create custom registration forms.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.text import slugify
from django.contrib.postgres.indexes import GinIndex
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class RegistrationFormTemplate(models.Model):
    """
    Pre-built form templates for quick tournament setup.
    
    System templates are created by DeltaCrown staff and cannot be edited.
    User templates can be created by organizers and shared with the community.
    
    Example templates:
    - "Valorant Solo APAC" (system)
    - "PUBG Mobile Team Bangladesh" (system)
    - "Free Fire Solo Tournament" (user-created)
    """
    
    # Basic Info
    name = models.CharField(
        max_length=200,
        help_text="Template name (e.g., 'Valorant Solo Registration')"
    )
    slug = models.SlugField(
        max_length=220,
        unique=True,
        help_text="URL-friendly identifier"
    )
    description = models.TextField(
        blank=True,
        help_text="What makes this template special?"
    )
    
    # Classification
    PARTICIPATION_TYPES = [
        ('solo', 'Solo Player'),
        ('team', 'Team'),
        ('duo', 'Duo/Squad'),
    ]
    participation_type = models.CharField(
        max_length=20,
        choices=PARTICIPATION_TYPES,
        db_index=True,
        help_text="Type of registration this template supports"
    )
    
    game = models.ForeignKey(
        'tournaments.Game',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_templates',
        help_text="Specific game this template is designed for"
    )
    
    # Form Structure (JSON Schema)
    form_schema = models.JSONField(
        default=dict,
        help_text="Complete form configuration including sections, fields, validation"
    )
    
    # Visual Metadata
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Emoji or icon class (e.g., '🎮' or 'fa-gamepad')"
    )
    thumbnail = models.ImageField(
        upload_to='form_templates/thumbnails/',
        null=True,
        blank=True,
        help_text="Preview image for template selection"
    )
    
    # Template Status
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this template visible to organizers?"
    )
    is_system_template = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Created by DeltaCrown staff (cannot be edited)"
    )
    is_featured = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Show in featured templates section"
    )
    
    # Usage Analytics
    usage_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of tournaments using this template"
    )
    average_completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Average % of users who complete registration"
    )
    
    # Creator Info
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_form_templates',
        help_text="User who created this template"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Discovery & Search
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for search/filtering (e.g., ['valorant', 'apac', 'ranked'])"
    )
    
    class Meta:
        db_table = 'tournaments_registration_form_template'
        ordering = ['-is_featured', '-usage_count', 'name']
        indexes = [
            models.Index(fields=['participation_type', 'game'], name='formtpl_type_game_idx'),
            models.Index(fields=['is_active', 'is_system_template'], name='formtpl_status_idx'),
            GinIndex(fields=['tags'], name='formtpl_tags_gin_idx'),
        ]
        verbose_name = 'Registration Form Template'
        verbose_name_plural = 'Registration Form Templates'
    
    def __str__(self):
        prefix = "⭐ " if self.is_system_template else ""
        return f"{prefix}{self.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided"""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def duplicate(self, new_name=None, created_by=None):
        """
        Create a copy of this template for customization.
        
        Args:
            new_name: Optional custom name for the duplicate
            created_by: User who is duplicating the template
        
        Returns:
            New RegistrationFormTemplate instance
        """
        duplicate = RegistrationFormTemplate.objects.create(
            name=new_name or f"{self.name} (Copy)",
            description=self.description,
            participation_type=self.participation_type,
            game=self.game,
            form_schema=self.form_schema.copy(),
            icon=self.icon,
            is_active=True,
            is_system_template=False,
            is_featured=False,
            created_by=created_by,
            tags=self.tags.copy() if self.tags else [],
        )
        return duplicate
    
    def increment_usage(self):
        """Increment usage counter when a tournament uses this template"""
        self.usage_count = models.F('usage_count') + 1
        self.save(update_fields=['usage_count'])
    
    def update_completion_rate(self, new_rate):
        """
        Update average completion rate with new data.
        
        Args:
            new_rate: Completion rate from a tournament (0-100)
        """
        if self.usage_count == 0:
            self.average_completion_rate = new_rate
        else:
            # Calculate running average
            total = self.average_completion_rate * self.usage_count
            self.average_completion_rate = (total + new_rate) / (self.usage_count + 1)
        
        self.save(update_fields=['average_completion_rate'])


class TournamentRegistrationForm(models.Model):
    """
    Per-tournament customized registration form.
    
    Each tournament has exactly one registration form. This is created by
    either selecting a template or building from scratch.
    
    The form_schema is an editable copy, so organizers can customize templates
    without affecting the original.
    """
    
    # Core Relationship
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='registration_form',
        help_text="Tournament this form belongs to"
    )
    
    # Template Source (optional)
    based_on_template = models.ForeignKey(
        RegistrationFormTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tournament_forms',
        help_text="Template this form was created from (if any)"
    )
    
    # Form Structure (Editable Copy)
    form_schema = models.JSONField(
        default=dict,
        help_text="Complete form configuration (editable copy from template)"
    )
    
    # Form Behavior Settings
    enable_multi_step = models.BooleanField(
        default=True,
        help_text="Split form into multiple steps/pages"
    )
    enable_autosave = models.BooleanField(
        default=True,
        help_text="Auto-save draft responses in browser"
    )
    enable_progress_bar = models.BooleanField(
        default=True,
        help_text="Show progress indicator during registration"
    )
    allow_edits_after_submit = models.BooleanField(
        default=False,
        help_text="Let users edit their registration after submission"
    )
    require_email_verification = models.BooleanField(
        default=False,
        help_text="Send verification email before accepting registration"
    )
    
    # Anti-Spam Settings
    enable_captcha = models.BooleanField(
        default=True,
        help_text="Require CAPTCHA on submission"
    )
    rate_limit_per_ip = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Max submissions per IP per hour"
    )
    
    # Confirmation Settings
    success_message = models.TextField(
        blank=True,
        help_text="Custom success message after registration"
    )
    redirect_url = models.URLField(
        blank=True,
        help_text="Redirect to external URL after success (optional)"
    )
    send_confirmation_email = models.BooleanField(
        default=True,
        help_text="Send email confirmation to participant"
    )
    
    # Advanced Features
    conditional_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Show/hide fields based on other field values"
    )
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom validation rules beyond field-level validation"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_tournament_forms',
        help_text="Last user who edited this form"
    )
    
    # Analytics
    total_views = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of times form was loaded"
    )
    total_starts = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of users who started filling the form"
    )
    total_completions = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Number of submitted registrations"
    )
    
    class Meta:
        db_table = 'tournaments_registration_form'
        verbose_name = 'Tournament Registration Form'
        verbose_name_plural = 'Tournament Registration Forms'
    
    def __str__(self):
        return f"Registration Form - {self.tournament.name}"
    
    @property
    def completion_rate(self):
        """Calculate completion rate percentage"""
        if self.total_starts == 0:
            return 0
        return round((self.total_completions / self.total_starts) * 100, 2)
    
    @property
    def abandonment_rate(self):
        """Calculate abandonment rate percentage"""
        if self.total_starts == 0:
            return 0
        abandoned = self.total_starts - self.total_completions
        return round((abandoned / self.total_starts) * 100, 2)
    
    def increment_views(self):
        """Track form view"""
        self.total_views = models.F('total_views') + 1
        self.save(update_fields=['total_views'])
    
    def increment_starts(self):
        """Track form start (user interacted with first field)"""
        self.total_starts = models.F('total_starts') + 1
        self.save(update_fields=['total_starts'])
    
    def increment_completions(self):
        """Track successful submission"""
        self.total_completions = models.F('total_completions') + 1
        self.save(update_fields=['total_completions'])
    
    def get_field_by_id(self, field_id):
        """
        Find a specific field in the form schema.
        
        Args:
            field_id: Unique field identifier
        
        Returns:
            Field dict or None if not found
        """
        for section in self.form_schema.get('sections', []):
            for field in section.get('fields', []):
                if field.get('id') == field_id:
                    return field
        return None
    
    def is_field_required(self, field_id):
        """Check if a field is marked as required"""
        field = self.get_field_by_id(field_id)
        return field.get('required', False) if field else False


class FormResponse(models.Model):
    """
    Participant's registration form submission.
    
    Stores all form responses in a JSONField for flexibility.
    Replaces the old TournamentRegistration model.
    """
    
    # Relationships
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='form_responses',
        help_text="Tournament this registration is for"
    )
    registration_form = models.ForeignKey(
        TournamentRegistrationForm,
        on_delete=models.SET_NULL,
        null=True,
        related_name='responses',
        help_text="Form version used for this registration"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='form_responses',
        help_text="User who submitted the registration"
    )
    
    # Team Registration (if applicable)
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_tournament_registrations',
        help_text="Team (if team tournament)"
    )
    
    # Form Response Data
    response_data = models.JSONField(
        default=dict,
        help_text="Complete form responses as JSON"
    )
    
    # Status Tracking
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current registration status"
    )
    
    # Payment Info (if applicable)
    has_paid = models.BooleanField(default=False, db_index=True)
    payment_verified = models.BooleanField(default=False, db_index=True)
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount paid (if entry fee exists)"
    )
    payment_method = models.CharField(max_length=50, blank=True)
    payment_transaction_id = models.CharField(max_length=200, blank=True)
    payment_proof = models.FileField(
        upload_to='registration_payments/',
        null=True,
        blank=True,
        help_text="Screenshot of payment"
    )
    payment_verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='form_verified_payments',
        help_text="Admin who verified payment"
    )
    payment_verified_at = models.DateTimeField(null=True, blank=True)
    
    # Admin Notes
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes (not visible to participant)"
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection (visible to participant)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    submission_duration = models.IntegerField(
        null=True,
        blank=True,
        help_text="Time taken to complete form (seconds)"
    )
    
    class Meta:
        db_table = 'tournaments_form_response'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tournament', 'status'], name='formresp_tourn_status_idx'),
            models.Index(fields=['user', 'tournament'], name='formresp_user_tourn_idx'),
            models.Index(fields=['status', 'payment_verified'], name='formresp_status_pay_idx'),
        ]
        unique_together = [('tournament', 'user')]
        verbose_name = 'Form Response'
        verbose_name_plural = 'Form Responses'
    
    def __str__(self):
        user_display = self.user.username if self.user else "Unknown"
        return f"{user_display} - {self.tournament.name} ({self.status})"
    
    def get_field_value(self, field_id):
        """Get value of a specific field from response data"""
        return self.response_data.get(field_id)
    
    def mark_as_submitted(self):
        """Mark registration as submitted"""
        self.status = 'submitted'
        self.submitted_at = models.functions.Now()
        self.save(update_fields=['status', 'submitted_at'])
    
    def approve(self, approved_by=None):
        """Approve registration"""
        self.status = 'approved'
        self.approved_at = models.functions.Now()
        self.save(update_fields=['status', 'approved_at'])
    
    def reject(self, reason='', rejected_by=None):
        """Reject registration"""
        self.status = 'rejected'
        self.rejection_reason = reason
        self.save(update_fields=['status', 'rejection_reason'])
