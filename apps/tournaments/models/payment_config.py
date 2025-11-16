"""
Tournament Payment Configuration Models.

Provides detailed payment method configuration for tournaments,
replacing the simple ArrayField payment_methods approach with
a more robust system that stores account details and instructions.

Source: Documents/Reports/TOURNAMENT_SYSTEM_IMPROVEMENTS_PLAN.md
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


class TournamentPaymentMethod(models.Model):
    """
    Configurable payment method for tournament entry fees.
    
    Each tournament can have multiple payment methods configured with
    specific account details, instructions, and display order.
    
    Replaces the simple payment_methods ArrayField with detailed configuration
    for each payment provider (bKash, Nagad, Rocket, Bank).
    """
    
    # Payment method choices (matches Tournament.PAYMENT_METHOD_CHOICES)
    DELTACOIN = 'deltacoin'
    BKASH = 'bkash'
    NAGAD = 'nagad'
    ROCKET = 'rocket'
    BANK_TRANSFER = 'bank_transfer'
    
    METHOD_CHOICES = [
        (DELTACOIN, 'DeltaCoin'),
        (BKASH, 'bKash'),
        (NAGAD, 'Nagad'),
        (ROCKET, 'Rocket'),
        (BANK_TRANSFER, 'Bank Transfer'),
    ]
    
    # Account type choices (for mobile financial services)
    PERSONAL = 'personal'
    MERCHANT = 'merchant'
    AGENT = 'agent'
    
    ACCOUNT_TYPE_CHOICES = [
        (PERSONAL, 'Personal Account'),
        (MERCHANT, 'Merchant Account'),
        (AGENT, 'Agent Account'),
    ]
    
    # Relations
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='payment_configurations',
        help_text='Tournament this payment method belongs to'
    )
    
    # Basic configuration
    method = models.CharField(
        max_length=20,
        choices=METHOD_CHOICES,
        help_text='Payment method type'
    )
    is_enabled = models.BooleanField(
        default=True,
        help_text='Whether this payment method is currently active'
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text='Display order in payment options (lower = higher priority)'
    )
    
    # bKash Configuration
    bkash_account_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='bKash account/merchant number (e.g., 01712345678)'
    )
    bkash_account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default=PERSONAL,
        blank=True,
        help_text='Type of bKash account'
    )
    bkash_account_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name on bKash account (for verification)'
    )
    bkash_instructions = models.TextField(
        blank=True,
        help_text='Step-by-step payment instructions for participants (supports Markdown)'
    )
    bkash_reference_required = models.BooleanField(
        default=True,
        help_text='Require participants to provide bKash transaction ID'
    )
    
    # Nagad Configuration
    nagad_account_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Nagad account/merchant number'
    )
    nagad_account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default=PERSONAL,
        blank=True,
        help_text='Type of Nagad account'
    )
    nagad_account_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name on Nagad account'
    )
    nagad_instructions = models.TextField(
        blank=True,
        help_text='Step-by-step payment instructions for participants'
    )
    nagad_reference_required = models.BooleanField(
        default=True,
        help_text='Require participants to provide Nagad transaction ID'
    )
    
    # Rocket Configuration
    rocket_account_number = models.CharField(
        max_length=20,
        blank=True,
        help_text='Rocket account number'
    )
    rocket_account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default=PERSONAL,
        blank=True,
        help_text='Type of Rocket account'
    )
    rocket_account_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Name on Rocket account'
    )
    rocket_instructions = models.TextField(
        blank=True,
        help_text='Step-by-step payment instructions for participants'
    )
    rocket_reference_required = models.BooleanField(
        default=True,
        help_text='Require participants to provide Rocket transaction ID'
    )
    
    # Bank Transfer Configuration
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Bank name (e.g., Dutch Bangla Bank Limited)'
    )
    bank_branch = models.CharField(
        max_length=100,
        blank=True,
        help_text='Bank branch name/location'
    )
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Bank account number'
    )
    bank_account_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Account holder name'
    )
    bank_routing_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Bank routing number (if applicable)'
    )
    bank_swift_code = models.CharField(
        max_length=20,
        blank=True,
        help_text='SWIFT/BIC code for international transfers'
    )
    bank_instructions = models.TextField(
        blank=True,
        help_text='Step-by-step bank transfer instructions'
    )
    bank_reference_required = models.BooleanField(
        default=True,
        help_text='Require participants to provide bank reference/transaction ID'
    )
    
    # DeltaCoin Configuration (usually no custom fields needed)
    deltacoin_instructions = models.TextField(
        blank=True,
        help_text='Custom instructions for DeltaCoin payment (optional)'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments_tournament_payment_method'
        verbose_name = 'Tournament Payment Method'
        verbose_name_plural = 'Tournament Payment Methods'
        ordering = ['display_order', 'method']
        unique_together = [('tournament', 'method')]
        indexes = [
            models.Index(fields=['tournament', 'is_enabled']),
            models.Index(fields=['method', 'is_enabled']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_enabled else "✗"
        return f"{status} {self.get_method_display()} - {self.tournament.name}"
    
    def clean(self):
        """Validate that required fields are provided for the selected method."""
        super().clean()
        
        errors = {}
        
        if self.method == self.BKASH and self.is_enabled:
            if not self.bkash_account_number:
                errors['bkash_account_number'] = 'bKash account number is required when method is enabled.'
            if not self.bkash_instructions:
                errors['bkash_instructions'] = 'Payment instructions are required for participants.'
        
        elif self.method == self.NAGAD and self.is_enabled:
            if not self.nagad_account_number:
                errors['nagad_account_number'] = 'Nagad account number is required when method is enabled.'
            if not self.nagad_instructions:
                errors['nagad_instructions'] = 'Payment instructions are required for participants.'
        
        elif self.method == self.ROCKET and self.is_enabled:
            if not self.rocket_account_number:
                errors['rocket_account_number'] = 'Rocket account number is required when method is enabled.'
            if not self.rocket_instructions:
                errors['rocket_instructions'] = 'Payment instructions are required for participants.'
        
        elif self.method == self.BANK_TRANSFER and self.is_enabled:
            if not self.bank_name:
                errors['bank_name'] = 'Bank name is required when method is enabled.'
            if not self.bank_account_number:
                errors['bank_account_number'] = 'Bank account number is required when method is enabled.'
            if not self.bank_instructions:
                errors['bank_instructions'] = 'Payment instructions are required for participants.'
        
        if errors:
            raise ValidationError(errors)
    
    def get_account_number(self):
        """Get the primary account number for this payment method."""
        if self.method == self.BKASH:
            return self.bkash_account_number
        elif self.method == self.NAGAD:
            return self.nagad_account_number
        elif self.method == self.ROCKET:
            return self.rocket_account_number
        elif self.method == self.BANK_TRANSFER:
            return self.bank_account_number
        elif self.method == self.DELTACOIN:
            return 'Internal System'
        return ''
    
    def get_instructions(self):
        """Get payment instructions for this method."""
        if self.method == self.BKASH:
            return self.bkash_instructions
        elif self.method == self.NAGAD:
            return self.nagad_instructions
        elif self.method == self.ROCKET:
            return self.rocket_instructions
        elif self.method == self.BANK_TRANSFER:
            return self.bank_instructions
        elif self.method == self.DELTACOIN:
            return self.deltacoin_instructions or 'Use your DeltaCoin balance to pay the entry fee.'
        return ''
    
    def requires_reference(self):
        """Check if this payment method requires a transaction reference."""
        if self.method == self.BKASH:
            return self.bkash_reference_required
        elif self.method == self.NAGAD:
            return self.nagad_reference_required
        elif self.method == self.ROCKET:
            return self.rocket_reference_required
        elif self.method == self.BANK_TRANSFER:
            return self.bank_reference_required
        elif self.method == self.DELTACOIN:
            return False  # DeltaCoin is internal, no manual reference needed
        return True
