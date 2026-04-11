# apps/economy/models/requests.py
from __future__ import annotations

from django.conf import settings
from django.db import models, transaction

from apps.common.managers import SoftDeleteManager
from apps.common.models import SoftDeleteModel
from .wallet import DeltaCrownWallet
from .transaction import DeltaCrownTransaction


class TopUpRequest(SoftDeleteModel):
    """
    Bangladesh Payment Top-Up Request.
    
    Workflow:
    1. User submits top-up request (amount + payment method + payment proof)
    2. Status = 'pending'
    3. Admin reviews payment proof
    4. On approval: DeltaCrownTransaction created (credit), status='completed'
    5. On rejection: status='rejected' with reason
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class PaymentMethod(models.TextChoices):
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        ROCKET = 'rocket', 'Rocket'
        BANK = 'bank', 'Bank Transfer'
    
    # Core Fields
    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name='topup_requests'
    )
    amount = models.PositiveIntegerField(
        help_text='Amount in DeltaCoins to add'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Payment Details
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )
    payment_number = models.CharField(
        max_length=50,
        help_text='bKash/Nagad/Rocket transaction ID or bank reference'
    )
    payment_details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional payment info (sender name, transaction ID, etc.)'
    )
    
    # Exchange Rate
    dc_to_bdt_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text='DeltaCoin to BDT exchange rate (e.g., 1 DC = 1.00 BDT)'
    )
    bdt_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Amount paid in BDT'
    )
    
    # Review Metadata
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_topups'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When credits were actually added'
    )
    
    # Notes
    user_note = models.TextField(
        blank=True,
        default='',
        help_text='User note/payment proof details'
    )
    admin_note = models.TextField(
        blank=True,
        default='',
        help_text='Admin note (approval details, verification notes, etc.)'
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for rejection (shown to user)'
    )
    
    # Transaction Reference
    transaction = models.ForeignKey(
        DeltaCrownTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='topup_request',
        help_text='Transaction that credited the coins (created on approval)'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['wallet', '-requested_at']),
            models.Index(fields=['status', '-requested_at']),
        ]
        verbose_name = 'Top-Up Request'
        verbose_name_plural = 'Top-Up Requests'
    
    def __str__(self):
        return f"TopUp {self.id}: {self.amount} DC via {self.get_payment_method_display()} - {self.get_status_display()}"
    
    def save(self, *args, **kwargs):
        """Calculate BDT amount if not set"""
        if not self.bdt_amount and self.amount:
            self.bdt_amount = self.amount * self.dc_to_bdt_rate
        super().save(*args, **kwargs)


class WithdrawalRequest(SoftDeleteModel):
    """
    Bangladesh Payment Withdrawal Request.
    
    Workflow:
    1. User requests withdrawal (amount + payment method + PIN verification)
    2. Status changes to 'pending'
    3. Amount is locked in wallet.pending_balance
    4. Admin reviews and approves/rejects
    5. On approval: funds transferred, status='completed', pending_balance reduced
    6. On rejection: pending_balance returned to available balance
    """
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        APPROVED = 'approved', 'Approved'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class PaymentMethod(models.TextChoices):
        BKASH = 'bkash', 'bKash'
        NAGAD = 'nagad', 'Nagad'
        ROCKET = 'rocket', 'Rocket'
        BANK = 'bank', 'Bank Transfer'
    
    # Core Fields
    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name='withdrawal_requests'
    )
    amount = models.PositiveIntegerField(
        help_text='Amount in DeltaCoins to withdraw'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Payment Details
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices
    )
    payment_number = models.CharField(
        max_length=50,
        help_text='bKash/Nagad/Rocket number or bank account number'
    )
    payment_details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional payment info (bank name, branch, account name, etc.)'
    )
    
    # Exchange Rate & Fee
    dc_to_bdt_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1.00,
        help_text='DeltaCoin to BDT exchange rate (e.g., 1 DC = 1.00 BDT)'
    )
    processing_fee = models.PositiveIntegerField(
        default=0,
        help_text='Processing fee in DeltaCoins'
    )
    bdt_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Amount in BDT after conversion'
    )
    
    # Review Metadata
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_withdrawals'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='When funds were actually transferred'
    )
    
    # Notes
    user_note = models.TextField(
        blank=True,
        default='',
        help_text='User note/reason for withdrawal'
    )
    admin_note = models.TextField(
        blank=True,
        default='',
        help_text='Admin note (rejection reason, transfer details, etc.)'
    )
    rejection_reason = models.TextField(
        blank=True,
        default='',
        help_text='Reason for rejection (shown to user)'
    )
    
    # Transaction Reference
    transaction = models.ForeignKey(
        DeltaCrownTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='withdrawal_request',
        help_text='Transaction that debited the coins (created on approval)'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['wallet', '-requested_at']),
            models.Index(fields=['status', '-requested_at']),
        ]
        verbose_name = 'Withdrawal Request'
        verbose_name_plural = 'Withdrawal Requests'
    
    def __str__(self):
        return f"Withdrawal {self.id}: {self.amount} DC via {self.get_payment_method_display()} - {self.get_status_display()}"
    
    @property
    def net_amount(self):
        """Amount after processing fee"""
        return self.amount - self.processing_fee
    
    @property
    def can_cancel(self):
        """Check if user can cancel this request"""
        return self.status == self.Status.PENDING
    
    @property
    def can_review(self):
        """Check if admin can review this request"""
        return self.status == self.Status.PENDING
    
    def save(self, *args, **kwargs):
        """Calculate BDT amount on save"""
        if not self.bdt_amount:
            self.bdt_amount = float(self.net_amount) * float(self.dc_to_bdt_rate)
        super().save(*args, **kwargs)
    
    def approve(self, reviewed_by, admin_note='', completed_immediately=True):
        """
        Approve withdrawal request.
        
        Args:
            reviewed_by: User who approved the request
            admin_note: Admin notes about the approval
            completed_immediately: If True, mark as completed immediately
        """
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot approve withdrawal with status '{self.status}'")
        
        with transaction.atomic():
            debit_transaction = DeltaCrownTransaction.objects.create(
                wallet=self.wallet,
                amount=-self.amount,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note=f"Withdrawal #{self.id} via {self.get_payment_method_display()}",
                created_by=reviewed_by,
                idempotency_key=f"withdrawal_{self.id}"
            )
            
            self.transaction = debit_transaction
            
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.last_withdrawal_at = timezone.now()
            self.wallet.save(update_fields=['pending_balance', 'last_withdrawal_at', 'updated_at'])
            
            self.status = self.Status.COMPLETED if completed_immediately else self.Status.APPROVED
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.admin_note = admin_note
            
            if completed_immediately:
                self.completed_at = timezone.now()
            
            self.save()
    
    def reject(self, reviewed_by, rejection_reason):
        """
        Reject withdrawal request.
        
        Args:
            reviewed_by: User who rejected the request
            rejection_reason: Reason for rejection (shown to user)
        """
        from django.utils import timezone
        
        if self.status != self.Status.PENDING:
            raise ValueError(f"Cannot reject withdrawal with status '{self.status}'")
        
        with transaction.atomic():
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.save(update_fields=['pending_balance', 'updated_at'])
            
            self.status = self.Status.REJECTED
            self.reviewed_by = reviewed_by
            self.reviewed_at = timezone.now()
            self.rejection_reason = rejection_reason
            self.admin_note = rejection_reason
            
            self.save()
    
    def cancel(self):
        """
        Cancel withdrawal request (user-initiated).
        Only allowed for pending requests.
        """
        if not self.can_cancel:
            raise ValueError(f"Cannot cancel withdrawal with status '{self.status}'")
        
        with transaction.atomic():
            self.wallet.pending_balance = max(0, self.wallet.pending_balance - self.amount)
            self.wallet.save(update_fields=['pending_balance', 'updated_at'])
            
            self.status = self.Status.CANCELLED
            self.save()
