"""
Registration and Payment models for tournament participation.

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 4: Registration Models)
- Documents/Planning/PART_3.2_CONSTRAINTS_INDEXES_TRIGGERS.md (Constraints + Indexes)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (UI behavior + flow)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-003 Soft Delete, ADR-004 PostgreSQL)

This module defines:
- Registration: Participant registration tracking with JSONB data storage
- Payment: Payment proof submission and verification workflow
"""

from decimal import Decimal
from typing import Optional, Any
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.common.models import SoftDeleteModel, TimestampedModel
from apps.common.managers import SoftDeleteManager


class Registration(SoftDeleteModel, TimestampedModel):
    """
    Participant registration for tournaments.
    
    Tracks user/team registrations with:
    - Status workflow (pending → payment_submitted → confirmed)
    - JSONB storage for flexible registration data
    - Check-in tracking for tournament day
    - Slot assignment for bracket generation
    - Soft delete support for cancellations
    
    Source: PART_3.1_DATABASE_DESIGN_ERD.md Section 4.1
    """
    
    # Status choices (workflow: pending → payment_submitted → confirmed/rejected/cancelled)
    PENDING = 'pending'
    PAYMENT_SUBMITTED = 'payment_submitted'
    CONFIRMED = 'confirmed'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PAYMENT_SUBMITTED, 'Payment Submitted'),
        (CONFIRMED, 'Confirmed'),
        (REJECTED, 'Rejected'),
        (CANCELLED, 'Cancelled'),
        (NO_SHOW, 'No Show'),
    ]
    
    # Core fields
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='registrations',
        help_text="Tournament being registered for"
    )
    
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='tournament_registrations',
        null=True,
        blank=True,
        help_text="User who registered (for solo tournaments or team captain)"
    )
    
    team_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Team ID reference (for team tournaments, IntegerField to avoid circular dependency)"
    )
    
    # Registration data (JSONB for flexibility)
    registration_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON storage for participant data (game IDs, contact info, custom fields)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
        help_text="Current registration status"
    )
    
    registered_at = models.DateTimeField(
        auto_now_add=True,
        null=True,  # Allow null for existing rows during migration
        help_text="When registration was submitted"
    )
    
    # Check-in tracking
    checked_in = models.BooleanField(
        default=False,
        help_text="Whether participant has checked in on tournament day"
    )
    
    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When participant checked in"
    )
    
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='checked_in_registrations',
        help_text="User who performed the check-in (owner, captain, or organizer)"
    )
    
    # Bracket/seeding fields
    slot_number = models.IntegerField(
        null=True,
        blank=True,
        help_text="Bracket slot number (1-based index for bracket position)"
    )
    
    seed = models.IntegerField(
        null=True,
        blank=True,
        help_text="Seeding number for bracket generation (lower = higher seed)"
    )
    
    # Manager
    objects = SoftDeleteManager()
    
    class Meta:
        db_table = 'tournaments_registration'
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'
        indexes = [
            models.Index(fields=['tournament', 'status']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['team_id', '-created_at']),
            models.Index(fields=['status', 'registered_at']),
            models.Index(fields=['tournament', 'slot_number']),
        ]
        unique_together = [
            ('tournament', 'user'),  # One registration per user per tournament
        ]
        constraints = [
            # Either user_id OR team_id must be set, not both
            models.CheckConstraint(
                check=(
                    models.Q(user__isnull=False, team_id__isnull=True) |
                    models.Q(user__isnull=True, team_id__isnull=False)
                ),
                name='registration_user_xor_team'
            ),
            # Slot number must be unique per tournament when set
            models.UniqueConstraint(
                fields=['tournament', 'slot_number'],
                condition=models.Q(slot_number__isnull=False, is_deleted=False),
                name='unique_slot_per_tournament'
            ),
            # Status must be valid
            models.CheckConstraint(
                check=models.Q(
                    status__in=[
                        'pending', 'payment_submitted', 'confirmed',
                        'rejected', 'cancelled', 'no_show'
                    ]
                ),
                name='registration_valid_status'
            ),
        ]
    
    def __str__(self) -> str:
        participant = self.user.username if self.user else f"Team {self.team_id}"
        return f"{participant} → {self.tournament.name} ({self.get_status_display()})"
    
    def clean(self):
        """Validate registration before saving"""
        super().clean()
        
        # Ensure either user or team_id is set, but not both
        if bool(self.user) == bool(self.team_id):
            raise ValidationError(
                "Registration must have either user or team_id set, but not both"
            )
    
    def check_in_participant(self, checked_in_by: Optional[Any] = None) -> None:
        """
        Mark participant as checked in.
        
        Args:
            checked_in_by: User who performed the check-in (optional)
        """
        self.checked_in = True
        self.checked_in_at = timezone.now()
        self.save(update_fields=['checked_in', 'checked_in_at', 'updated_at'])
    
    def assign_slot(self, slot_number: int) -> None:
        """
        Assign a bracket slot number to this registration.
        
        Args:
            slot_number: Bracket position (1-based index)
        
        Raises:
            ValidationError: If slot is already assigned or invalid
        """
        if slot_number < 1:
            raise ValidationError("Slot number must be positive")
        
        self.slot_number = slot_number
        self.save(update_fields=['slot_number', 'updated_at'])
    
    def assign_seed(self, seed: int) -> None:
        """
        Assign a seed number for bracket generation.
        
        Args:
            seed: Seeding number (lower = higher seed)
        """
        self.seed = seed
        self.save(update_fields=['seed', 'updated_at'])
    
    @property
    def participant_identifier(self) -> str:
        """Get participant identifier (username or team ID)"""
        if self.user:
            return self.user.username
        return f"Team {self.team_id}"
    
    @property
    def has_payment(self) -> bool:
        """Check if registration has an associated payment"""
        return hasattr(self, 'payment')
    
    @property
    def is_confirmed(self) -> bool:
        """Check if registration is confirmed"""
        return self.status == self.CONFIRMED
    
    @property
    def is_pending_payment(self) -> bool:
        """Check if registration is pending payment verification"""
        return self.status in [self.PENDING, self.PAYMENT_SUBMITTED]


class Payment(models.Model):
    """
    Payment proof and verification tracking for tournament registrations.
    
    Handles:
    - Multiple payment methods (bKash, Nagad, Rocket, Bank, DeltaCoin)
    - Payment proof upload and storage
    - Admin verification workflow
    - Status tracking (pending → submitted → verified/rejected)
    
    Source: PART_3.1_DATABASE_DESIGN_ERD.md Section 4.2
    """
    
    # Payment method choices
    BKASH = 'bkash'
    NAGAD = 'nagad'
    ROCKET = 'rocket'
    BANK = 'bank'
    DELTACOIN = 'deltacoin'
    
    PAYMENT_METHOD_CHOICES = [
        (BKASH, 'bKash'),
        (NAGAD, 'Nagad'),
        (ROCKET, 'Rocket'),
        (BANK, 'Bank Transfer'),
        (DELTACOIN, 'DeltaCoin'),
    ]
    
    # Status choices
    PENDING = 'pending'
    SUBMITTED = 'submitted'
    VERIFIED = 'verified'
    REJECTED = 'rejected'
    REFUNDED = 'refunded'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (SUBMITTED, 'Submitted'),
        (VERIFIED, 'Verified'),
        (REJECTED, 'Rejected'),
        (REFUNDED, 'Refunded'),
    ]
    
    # Core fields
    registration = models.OneToOneField(
        Registration,
        on_delete=models.CASCADE,
        related_name='payment',
        help_text="Associated registration"
    )
    
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        help_text="Payment method used"
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Payment amount in BDT"
    )
    
    transaction_id = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Transaction ID from payment provider"
    )
    
    # Payment proof file upload (Module 3.2: Payment Processing)
    payment_proof = models.FileField(
        upload_to='payment_proofs/%Y/%m/',
        blank=True,
        null=True,
        help_text="Payment proof file upload (image or PDF, max 5MB)"
    )
    
    file_type = models.CharField(
        max_length=10,
        blank=True,
        default='',
        choices=[
            ('IMAGE', 'Image'),
            ('PDF', 'PDF Document'),
        ],
        help_text="Type of uploaded proof file"
    )
    
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        default='',
        help_text="Payment reference number from receipt"
    )
    
    # Status and verification
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
        help_text="Current payment status"
    )
    
    admin_notes = models.TextField(
        blank=True,
        default='',
        help_text="Admin notes for verification/rejection"
    )
    
    verified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_payments',
        help_text="Admin who verified/rejected the payment"
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When payment was verified/rejected"
    )
    
    # Timestamps
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When payment proof was submitted"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    
    class Meta:
        db_table = 'tournaments_payment'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['registration']),
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['status', '-submitted_at']),
            models.Index(fields=['verified_by', 'verified_at']),
        ]
        constraints = [
            # Amount must be positive
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name='payment_amount_positive'
            ),
            # Payment method must be valid
            models.CheckConstraint(
                check=models.Q(
                    payment_method__in=['bkash', 'nagad', 'rocket', 'bank', 'deltacoin']
                ),
                name='payment_method_valid'
            ),
            # Status must be valid
            models.CheckConstraint(
                check=models.Q(
                    status__in=['pending', 'submitted', 'verified', 'rejected', 'refunded']
                ),
                name='payment_status_valid'
            ),
            # If verified, must have verified_by and verified_at
            models.CheckConstraint(
                check=(
                    models.Q(status='verified', verified_by__isnull=False, verified_at__isnull=False) |
                    ~models.Q(status='verified')
                ),
                name='payment_verification_complete'
            ),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_payment_method_display()} - {self.amount} BDT ({self.get_status_display()})"
    
    def clean(self):
        """Validate payment before saving"""
        super().clean()
        
        # Amount must be positive
        if self.amount <= 0:
            raise ValidationError("Payment amount must be positive")
        
        # If status is verified, must have verified_by and verified_at
        if self.status == self.VERIFIED:
            if not self.verified_by or not self.verified_at:
                raise ValidationError(
                    "Verified payments must have verified_by and verified_at set"
                )
        
        # Validate file upload (Module 3.2)
        if self.payment_proof:
            self._validate_proof_file()
    
    def _validate_proof_file(self) -> None:
        """
        Validate payment proof file (Module 3.2: Payment Processing).
        
        Validates:
        - File size (max 5MB)
        - File type (JPG, PNG, PDF only)
        - Sets file_type field based on content type
        
        Raises:
            ValidationError: If file is invalid
        """
        file = self.payment_proof
        
        # Check file size (5MB max)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if file.size > max_size:
            raise ValidationError(
                f"Payment proof file is too large ({file.size / 1024 / 1024:.1f}MB). "
                f"Maximum size is 5MB."
            )
        
        # Check file extension
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.pdf']
        file_extension = file.name.lower().split('.')[-1]
        if f'.{file_extension}' not in allowed_extensions:
            raise ValidationError(
                f"Invalid file type '.{file_extension}'. "
                f"Allowed types: JPG, PNG, PDF"
            )
        
        # Determine file type
        if file_extension == 'pdf':
            self.file_type = 'PDF'
        else:
            self.file_type = 'IMAGE'
    
    def verify(self, verified_by: Any, admin_notes: str = '') -> None:
        """
        Mark payment as verified by admin.
        
        Args:
            verified_by: Admin user who verified the payment
            admin_notes: Optional notes about verification
        """
        self.status = self.VERIFIED
        self.verified_by = verified_by
        self.verified_at = timezone.now()
        if admin_notes:
            self.admin_notes = admin_notes
        self.save(update_fields=['status', 'verified_by', 'verified_at', 'admin_notes', 'updated_at'])
    
    def reject(self, rejected_by: Any, reason: str) -> None:
        """
        Reject payment with reason.
        
        Args:
            rejected_by: Admin user who rejected the payment
            reason: Reason for rejection
        """
        self.status = self.REJECTED
        self.verified_by = rejected_by
        self.verified_at = timezone.now()
        self.admin_notes = reason
        self.save(update_fields=['status', 'verified_by', 'verified_at', 'admin_notes', 'updated_at'])
    
    def refund(self, refunded_by: Any, reason: str = '') -> None:
        """
        Mark payment as refunded.
        
        Args:
            refunded_by: Admin user who processed the refund
            reason: Reason for refund
        """
        self.status = self.REFUNDED
        self.verified_by = refunded_by
        self.verified_at = timezone.now()
        if reason:
            self.admin_notes = f"Refunded: {reason}"
        self.save(update_fields=['status', 'verified_by', 'verified_at', 'admin_notes', 'updated_at'])
    
    @property
    def is_verified(self) -> bool:
        """Check if payment is verified"""
        return self.status == self.VERIFIED
    
    @property
    def is_pending_verification(self) -> bool:
        """Check if payment is awaiting verification"""
        return self.status == self.SUBMITTED
    
    @property
    def can_be_verified(self) -> bool:
        """Check if payment can be verified (has proof and is submitted)"""
        # For DeltaCoin, only transaction_id is needed
        if self.payment_method == self.DELTACOIN:
            return self.status == self.SUBMITTED and bool(self.transaction_id)
        # For manual payments (bKash, Nagad, etc.), payment proof file is required
        return self.status == self.SUBMITTED and (bool(self.payment_proof) or bool(self.transaction_id))
    
    @property
    def proof_file_url(self) -> Optional[str]:
        """Get payment proof file URL if available"""
        if self.payment_proof:
            try:
                return self.payment_proof.url
            except ValueError:
                return None
        return None
