"""
Smart Registration models for Phase 5.

Provides configuration-driven registration with:
- Dynamic questions per tournament/game
- Answer storage and validation
- Auto-approval/rejection rules
- Draft persistence for multi-session registration

Source Documents:
- Documents/Modify_TournamentApp/Workplan/SMART_REG_AND_RULES_PART_3.md (Section 3)
- Documents/Modify_TournamentApp/Workplan/ROADMAP_AND_EPICS_PART_4.md (Phase 5)
"""

import uuid
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.common.models import TimestampedModel


class RegistrationQuestion(TimestampedModel):
    """
    Configuration-driven registration question.
    
    Supports:
    - Built-in system questions (region, rank)
    - Custom organizer questions
    - Type validation (text, select, boolean, number)
    - Conditional display logic
    
    Source: SMART_REG_AND_RULES_PART_3.md Section 3.2
    """
    
    # Question Types
    TEXT = 'text'
    SELECT = 'select'
    MULTI_SELECT = 'multi_select'
    BOOLEAN = 'boolean'
    NUMBER = 'number'
    FILE = 'file'
    DATE = 'date'
    
    TYPE_CHOICES = [
        (TEXT, 'Text Input'),
        (SELECT, 'Single Select'),
        (MULTI_SELECT, 'Multi Select'),
        (BOOLEAN, 'Yes/No'),
        (NUMBER, 'Number'),
        (FILE, 'File Upload'),
        (DATE, 'Date'),
    ]
    
    # Scope
    TEAM_LEVEL = 'team'
    PLAYER_LEVEL = 'player'
    
    SCOPE_CHOICES = [
        (TEAM_LEVEL, 'Team Level'),
        (PLAYER_LEVEL, 'Player Level'),
    ]
    
    # Relationships
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='registration_questions',
        null=True,
        blank=True,
        help_text='Tournament-specific question (null for global)'
    )
    
    game = models.ForeignKey(
        'Game',
        on_delete=models.CASCADE,
        related_name='registration_questions',
        null=True,
        blank=True,
        help_text='Game-specific question (null for global)'
    )
    
    # Question Definition
    slug = models.SlugField(
        max_length=100,
        help_text='Machine-readable key: rank, region, discord_username'
    )
    
    text = models.TextField(
        help_text='Question label shown to user'
    )
    
    help_text = models.TextField(
        blank=True,
        help_text='Additional help text for users'
    )
    
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TEXT
    )
    
    scope = models.CharField(
        max_length=10,
        choices=SCOPE_CHOICES,
        default=PLAYER_LEVEL
    )
    
    # Validation
    is_required = models.BooleanField(
        default=False,
        help_text='Question must be answered'
    )
    
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Question configuration: {options: [], min: 0, max: 100, regex: "pattern", ...}'
    )
    
    # Display
    order = models.PositiveIntegerField(
        default=0,
        help_text='Display order (lower = first)'
    )
    
    show_if = models.JSONField(
        default=dict,
        blank=True,
        help_text='Conditional display: {tournament_type: "team", age: {"gte": 18}}'
    )
    
    # Metadata
    is_built_in = models.BooleanField(
        default=False,
        help_text='System-provided question (cannot be deleted)'
    )
    
    is_active = models.BooleanField(
        default=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['tournament', 'order']),
            models.Index(fields=['game', 'order']),
            models.Index(fields=['slug']),
        ]
        ordering = ['order', 'id']
    
    def __str__(self):
        if self.tournament:
            return f'{self.tournament.name} - {self.text}'
        elif self.game:
            return f'{self.game.name} - {self.text}'
        return self.text


class RegistrationDraft(TimestampedModel):
    """
    Persistent draft for multi-session registration.
    
    Features:
    - Cross-device resume via UUID
    - Auto-save every 30 seconds
    - Progress tracking
    - 7-day expiration
    
    Source: SMART_REG_AND_RULES_PART_3.md Section 3.2
    """
    
    # Step Choices
    PLAYER_INFO = 'player_info'
    TEAM_INFO = 'team_info'
    QUESTIONS = 'questions'
    REVIEW = 'review'
    PAYMENT = 'payment'
    
    STEP_CHOICES = [
        (PLAYER_INFO, 'Player Information'),
        (TEAM_INFO, 'Team Information'),
        (QUESTIONS, 'Additional Questions'),
        (REVIEW, 'Review & Confirm'),
        (PAYMENT, 'Payment'),
    ]
    
    # Identity
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        help_text='Universal draft ID for cross-device resume'
    )
    
    registration_number = models.CharField(
        max_length=20,
        unique=True,
        help_text='Human-readable: VCT-2025-001234'
    )
    
    # Relationships
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='registration_drafts'
    )
    
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='registration_drafts'
    )
    
    team_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text='Team ID (IntegerField to avoid circular dependency)'
    )
    
    # Draft Data
    form_data = models.JSONField(
        default=dict,
        help_text='All form fields: {riot_id, discord, phone, answers: {...}}'
    )
    
    auto_filled_fields = models.JSONField(
        default=list,
        help_text='Fields auto-filled: ["riot_id", "email"]'
    )
    
    locked_fields = models.JSONField(
        default=list,
        help_text='Fields locked (verified): ["email", "riot_id"]'
    )
    
    # Progress
    current_step = models.CharField(
        max_length=20,
        choices=STEP_CHOICES,
        default=PLAYER_INFO
    )
    
    completion_percentage = models.PositiveIntegerField(
        default=0,
        help_text='0-100'
    )
    
    # Status
    submitted = models.BooleanField(
        default=False,
        help_text='Draft converted to registration'
    )
    
    registration = models.OneToOneField(
        'Registration',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text='Created after draft submission'
    )
    
    # Timestamps
    last_saved_at = models.DateTimeField(
        auto_now=True,
        help_text='Auto-updated on every save (for auto-save tracking)'
    )
    
    expires_at = models.DateTimeField(
        help_text='Draft expires 7 days after creation'
    )
    
    class Meta:
        unique_together = [('user', 'tournament')]
        indexes = [
            models.Index(fields=['uuid']),
            models.Index(fields=['registration_number']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        # Set expiration on creation
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if draft has expired."""
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f'{self.registration_number} - {self.user.username} ({self.tournament.name})'


class RegistrationAnswer(TimestampedModel):
    """
    Answer to a registration question.
    
    Links Registration → RegistrationQuestion with answer value.
    
    Source: SMART_REG_AND_RULES_PART_3.md Section 3.2
    """
    
    registration = models.ForeignKey(
        'Registration',
        on_delete=models.CASCADE,
        related_name='answers'
    )
    
    question = models.ForeignKey(
        'RegistrationQuestion',
        on_delete=models.CASCADE,
        related_name='answers'
    )
    
    # Answer Value (JSON for flexibility)
    value = models.JSONField(
        help_text='Answer value: string, number, boolean, list, or dict'
    )
    
    normalized_value = models.TextField(
        blank=True,
        help_text='Normalized value for search/filtering'
    )
    
    class Meta:
        unique_together = [('registration', 'question')]
        indexes = [
            models.Index(fields=['registration']),
            models.Index(fields=['question']),
        ]
    
    def __str__(self):
        return f'{self.registration.id} - {self.question.slug}: {self.value}'


class RegistrationRule(TimestampedModel):
    """
    Auto-approval/rejection rule for smart registration.
    
    Evaluates registration data + answers to determine:
    - AUTO_APPROVE (bypass manual review)
    - AUTO_REJECT (deny registration)
    - FLAG_FOR_REVIEW (organizer review required)
    
    Source: SMART_REG_AND_RULES_PART_3.md Section 3.2
    """
    
    # Rule Types
    AUTO_APPROVE = 'auto_approve'
    AUTO_REJECT = 'auto_reject'
    FLAG_FOR_REVIEW = 'flag_for_review'
    
    TYPE_CHOICES = [
        (AUTO_APPROVE, 'Auto Approve'),
        (AUTO_REJECT, 'Auto Reject'),
        (FLAG_FOR_REVIEW, 'Flag for Review'),
    ]
    
    # Relationships
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='registration_rules'
    )
    
    # Rule Definition
    name = models.CharField(
        max_length=200,
        help_text='Rule description: "Auto-approve verified Immortal+ players"'
    )
    
    rule_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )
    
    # Condition (simple JSON expression for Phase 5)
    condition = models.JSONField(
        help_text='Condition expression: {"rank": {"in": ["Immortal", "Radiant"]}, "email_verified": true}'
    )
    
    # Execution
    priority = models.PositiveIntegerField(
        default=0,
        help_text='Lower = higher priority (evaluated first)'
    )
    
    is_active = models.BooleanField(
        default=True
    )
    
    # Metadata
    reason_template = models.TextField(
        blank=True,
        help_text='Reason shown to user if rule triggers: "Registration auto-approved (verified Immortal player)"'
    )
    
    class Meta:
        ordering = ['priority', 'id']
        indexes = [
            models.Index(fields=['tournament', 'is_active', 'priority']),
        ]
    
    def __str__(self):
        return f'{self.tournament.name} - {self.name} ({self.rule_type})'
    
    def evaluate(self, registration_data: dict, answers: dict) -> bool:
        """
        Evaluate if condition matches registration data.
        
        Phase 5: Simple equality/in checks.
        Phase 6+: Full DSL with operators (gte, lte, regex, etc.)
        
        Args:
            registration_data: {user_id, team_id, email, phone, ...}
            answers: {question_slug: answer_value, ...}
        
        Returns:
            True if condition matches, False otherwise
        """
        # Combine data sources
        data = {**registration_data, **answers}
        
        # Evaluate each condition key
        for key, expected in self.condition.items():
            actual = data.get(key)
            
            # Handle different comparison types
            if isinstance(expected, dict):
                # Advanced operators: {"in": [...], "gte": 18, ...}
                for op, op_value in expected.items():
                    if op == 'in':
                        if actual not in op_value:
                            return False
                    elif op == 'gte':
                        if actual is None or actual < op_value:
                            return False
                    elif op == 'lte':
                        if actual is None or actual > op_value:
                            return False
                    elif op == 'eq':
                        if actual != op_value:
                            return False
                    else:
                        # Unknown operator
                        return False
            else:
                # Simple equality
                if actual != expected:
                    return False
        
        return True
