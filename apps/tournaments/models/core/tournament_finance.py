"""
Tournament Finance Model

Handles all financial aspects of tournaments including entry fees,
prize pools, payment tracking, and financial reporting.

Fields:
    - entry_fee_bdt: Entry fee in Bangladeshi Taka
    - prize_pool_bdt: Total prize pool
    - prize_distribution: JSON field for prize breakdown
    - currency: Currency code (default: BDT)
    - payment_required: Whether payment is required for registration
    - payment_deadline_hours: Hours after registration to complete payment
    - refund_policy: Refund policy text

Properties:
    - has_entry_fee: Check if tournament requires payment
    - formatted_entry_fee: Human-readable entry fee
    - formatted_prize_pool: Human-readable prize pool
    - prize_to_entry_ratio: Calculate ROI potential

Author: DeltaCrown Development Team
Date: October 3, 2025
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import json


class TournamentFinance(models.Model):
    """
    Manages financial aspects of tournaments.
    
    This model encapsulates all finance-related logic including:
    - Entry fees and prize pools
    - Payment requirements and deadlines
    - Prize distribution configuration
    - Refund policies
    - Financial reporting and calculations
    """
    
    # Currency choices
    CURRENCY_BDT = 'BDT'
    CURRENCY_USD = 'USD'
    CURRENCY_EUR = 'EUR'
    
    CURRENCY_CHOICES = [
        (CURRENCY_BDT, _('Bangladeshi Taka (৳)')),
        (CURRENCY_USD, _('US Dollar ($)')),
        (CURRENCY_EUR, _('Euro (€)')),
    ]
    
    # Relationships
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='finance',
        verbose_name=_('Tournament'),
        help_text=_('The tournament this finance configuration belongs to')
    )
    
    # Financial Fields
    entry_fee_bdt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Entry Fee (BDT)'),
        help_text=_('Entry fee in Bangladeshi Taka (৳). Set to 0 for free tournaments.')
    )
    
    prize_pool_bdt = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Prize Pool (BDT)'),
        help_text=_('Total prize pool in Bangladeshi Taka (৳)')
    )
    
    currency = models.CharField(
        max_length=3,
        choices=CURRENCY_CHOICES,
        default=CURRENCY_BDT,
        verbose_name=_('Currency'),
        help_text=_('Primary currency for this tournament')
    )
    
    # Prize Distribution (JSON field for flexibility)
    prize_distribution = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Prize Distribution'),
        help_text=_('Prize breakdown by position (JSON format)')
    )
    
    # Payment Configuration
    payment_required = models.BooleanField(
        default=False,
        verbose_name=_('Payment Required'),
        help_text=_('Whether participants must pay to complete registration')
    )
    
    payment_deadline_hours = models.PositiveIntegerField(
        default=48,
        validators=[MinValueValidator(1), MaxValueValidator(720)],  # Max 30 days
        verbose_name=_('Payment Deadline (Hours)'),
        help_text=_('Hours after registration to complete payment (1-720)')
    )
    
    # Policies
    refund_policy = models.TextField(
        blank=True,
        verbose_name=_('Refund Policy'),
        help_text=_('Refund policy for this tournament')
    )
    
    # Additional Fees (Optional)
    platform_fee_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name=_('Platform Fee (%)'),
        help_text=_('Platform fee as percentage of entry fee (0-100%)')
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Tournament Finance')
        verbose_name_plural = _('Tournament Finances')
        db_table = 'tournaments_finance'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_required']),
            models.Index(fields=['entry_fee_bdt']),
        ]
    
    def __str__(self):
        if self.has_entry_fee:
            return f"{self.tournament.name} - Fee: ৳{self.entry_fee_bdt}, Pool: ৳{self.prize_pool_bdt}"
        return f"{self.tournament.name} - Free Entry, Pool: ৳{self.prize_pool_bdt}"
    
    def clean(self):
        """Validate finance configuration"""
        errors = {}
        
        # If payment required, entry fee must be > 0
        if self.payment_required and self.entry_fee_bdt <= 0:
            errors['payment_required'] = _(
                'Payment required tournaments must have entry fee > 0'
            )
        
        # Prize pool should not be negative
        if self.prize_pool_bdt < 0:
            errors['prize_pool_bdt'] = _('Prize pool cannot be negative')
        
        # Validate prize distribution JSON
        if self.prize_distribution:
            try:
                if not isinstance(self.prize_distribution, dict):
                    errors['prize_distribution'] = _('Prize distribution must be a dictionary')
                else:
                    # Validate prize amounts don't exceed prize pool
                    total_prizes = sum(
                        Decimal(str(v)) for v in self.prize_distribution.values()
                        if isinstance(v, (int, float, str, Decimal))
                    )
                    if total_prizes > self.prize_pool_bdt:
                        errors['prize_distribution'] = _(
                            f'Total prize distribution (৳{total_prizes}) exceeds prize pool (৳{self.prize_pool_bdt})'
                        )
            except (TypeError, ValueError) as e:
                errors['prize_distribution'] = _(f'Invalid prize distribution format: {str(e)}')
        
        # Platform fee validation
        if self.platform_fee_percent < 0 or self.platform_fee_percent > 100:
            errors['platform_fee_percent'] = _('Platform fee must be between 0% and 100%')
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Ensure validation before save"""
        self.full_clean()
        super().save(*args, **kwargs)
    
    # ==========================================
    # Properties - Computed Values
    # ==========================================
    
    @property
    def has_entry_fee(self) -> bool:
        """Check if tournament requires entry fee"""
        return self.entry_fee_bdt > 0
    
    @property
    def is_free(self) -> bool:
        """Check if tournament is free to enter"""
        return self.entry_fee_bdt == 0
    
    @property
    def has_prize_pool(self) -> bool:
        """Check if tournament has prize money"""
        return self.prize_pool_bdt > 0
    
    @property
    def formatted_entry_fee(self) -> str:
        """Get formatted entry fee with currency symbol"""
        if self.is_free:
            return "Free"
        
        if self.currency == self.CURRENCY_BDT:
            return f"৳{self.entry_fee_bdt:,.2f}"
        elif self.currency == self.CURRENCY_USD:
            return f"${self.entry_fee_bdt:,.2f}"
        elif self.currency == self.CURRENCY_EUR:
            return f"€{self.entry_fee_bdt:,.2f}"
        return f"{self.entry_fee_bdt:,.2f} {self.currency}"
    
    @property
    def formatted_prize_pool(self) -> str:
        """Get formatted prize pool with currency symbol"""
        if not self.has_prize_pool:
            return "No prizes"
        
        if self.currency == self.CURRENCY_BDT:
            return f"৳{self.prize_pool_bdt:,.2f}"
        elif self.currency == self.CURRENCY_USD:
            return f"${self.prize_pool_bdt:,.2f}"
        elif self.currency == self.CURRENCY_EUR:
            return f"€{self.prize_pool_bdt:,.2f}"
        return f"{self.prize_pool_bdt:,.2f} {self.currency}"
    
    @property
    def prize_to_entry_ratio(self) -> float:
        """
        Calculate ROI potential (prize pool / entry fee).
        Returns 0 if entry fee is 0.
        """
        if self.entry_fee_bdt == 0:
            return 0.0
        return float(self.prize_pool_bdt / self.entry_fee_bdt)
    
    @property
    def total_with_platform_fee(self) -> Decimal:
        """Calculate total amount including platform fee"""
        if self.platform_fee_percent == 0:
            return self.entry_fee_bdt
        
        platform_fee = self.entry_fee_bdt * (self.platform_fee_percent / 100)
        return self.entry_fee_bdt + platform_fee
    
    @property
    def platform_fee_amount(self) -> Decimal:
        """Calculate platform fee amount"""
        return self.entry_fee_bdt * (self.platform_fee_percent / 100)
    
    # ==========================================
    # Methods - Actions
    # ==========================================
    
    def get_prize_for_position(self, position: int) -> Decimal:
        """
        Get prize amount for a specific position.
        
        Args:
            position: Position/rank (1 for first place, 2 for second, etc.)
            
        Returns:
            Decimal: Prize amount for that position (0 if not defined)
        """
        if not self.prize_distribution:
            return Decimal('0.00')
        
        # Try different key formats
        keys_to_try = [
            str(position),  # "1", "2", "3"
            f"position_{position}",  # "position_1"
            f"rank_{position}",  # "rank_1"
            f"{position}st" if position == 1 else f"{position}nd" if position == 2 else f"{position}rd" if position == 3 else f"{position}th"
        ]
        
        for key in keys_to_try:
            if key in self.prize_distribution:
                try:
                    return Decimal(str(self.prize_distribution[key]))
                except (ValueError, TypeError):
                    pass
        
        return Decimal('0.00')
    
    def set_prize_for_position(self, position: int, amount: Decimal) -> None:
        """
        Set prize amount for a specific position.
        
        Args:
            position: Position/rank
            amount: Prize amount
        """
        if not self.prize_distribution:
            self.prize_distribution = {}
        
        self.prize_distribution[str(position)] = float(amount)
        self.save(update_fields=['prize_distribution', 'updated_at'])
    
    def calculate_total_revenue(self, participant_count: int) -> Decimal:
        """
        Calculate total revenue from entry fees.
        
        Args:
            participant_count: Number of registered participants
            
        Returns:
            Decimal: Total revenue
        """
        return self.entry_fee_bdt * participant_count
    
    def calculate_platform_revenue(self, participant_count: int) -> Decimal:
        """
        Calculate platform revenue from fees.
        
        Args:
            participant_count: Number of registered participants
            
        Returns:
            Decimal: Platform revenue
        """
        return self.platform_fee_amount * participant_count
    
    def get_payment_deadline_display(self) -> str:
        """Get human-readable payment deadline"""
        hours = self.payment_deadline_hours
        
        if hours < 24:
            return f"{hours} hours"
        
        days = hours // 24
        remaining_hours = hours % 24
        
        if remaining_hours == 0:
            return f"{days} days" if days > 1 else "1 day"
        
        return f"{days} days {remaining_hours} hours"
    
    # ==========================================
    # Helper Methods
    # ==========================================
    
    def clone_for_tournament(self, target_tournament) -> 'TournamentFinance':
        """
        Create a copy of this finance configuration for another tournament.
        
        Args:
            target_tournament: Tournament instance to link the clone to
            
        Returns:
            TournamentFinance: New finance instance
        """
        return TournamentFinance.objects.create(
            tournament=target_tournament,
            entry_fee_bdt=self.entry_fee_bdt,
            prize_pool_bdt=self.prize_pool_bdt,
            currency=self.currency,
            prize_distribution=self.prize_distribution.copy() if self.prize_distribution else {},
            payment_required=self.payment_required,
            payment_deadline_hours=self.payment_deadline_hours,
            refund_policy=self.refund_policy,
            platform_fee_percent=self.platform_fee_percent
        )
    
    def to_dict(self) -> dict:
        """Convert finance to dictionary for API/serialization"""
        return {
            'entry_fee': float(self.entry_fee_bdt),
            'entry_fee_formatted': self.formatted_entry_fee,
            'prize_pool': float(self.prize_pool_bdt),
            'prize_pool_formatted': self.formatted_prize_pool,
            'currency': self.currency,
            'has_entry_fee': self.has_entry_fee,
            'is_free': self.is_free,
            'has_prize_pool': self.has_prize_pool,
            'payment_required': self.payment_required,
            'payment_deadline_hours': self.payment_deadline_hours,
            'payment_deadline_display': self.get_payment_deadline_display(),
            'prize_distribution': self.prize_distribution,
            'prize_to_entry_ratio': self.prize_to_entry_ratio,
            'platform_fee_percent': float(self.platform_fee_percent),
            'platform_fee_amount': float(self.platform_fee_amount),
            'total_with_fee': float(self.total_with_platform_fee),
        }
