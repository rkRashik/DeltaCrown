"""
DeltaCoin Shop Models - Module 7.2

Models:
- ShopItem: Catalog items with SKU, price, and active status
- ReservationHold: Spend authorizations with state machine (authorized → captured/released/expired)
"""

from django.db import models
from django.core.validators import MinValueValidator
from apps.economy.models import DeltaCrownWallet


class ShopItem(models.Model):
    """
    Catalog item for DeltaCoin shop.
    
    Constraints:
    - sku: unique, indexed
    - price: positive integer (CHECK constraint)
    - active: boolean flag for availability
    """
    sku = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique item SKU")
    name = models.CharField(max_length=255, help_text="Display name")
    description = models.TextField(blank=True, help_text="Item description")
    price = models.IntegerField(validators=[MinValueValidator(1)], help_text="Price in DeltaCoins (must be positive)")
    active = models.BooleanField(default=True, help_text="Item available for purchase")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'shop_item'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=0),
                name='shop_item_price_positive',
            )
        ]

    def __str__(self):
        return f"{self.sku} - {self.name} ({self.price} DC)"


class ReservationHold(models.Model):
    """
    Spend authorization hold on a wallet.
    
    State Machine:
    - authorized → captured (via capture())
    - authorized → released (via release())
    - authorized → expired (via timeout or manual expiry)
    
    Terminal states: captured, released, expired
    No reverse transitions allowed.
    
    Constraints:
    - amount: positive integer (CHECK constraint)
    - status: enum constraint (authorized, captured, released, expired)
    - idempotency_key: partial unique (unique where not null)
    """
    STATUS_CHOICES = [
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('released', 'Released'),
        ('expired', 'Expired'),
    ]

    wallet = models.ForeignKey(
        DeltaCrownWallet,
        on_delete=models.PROTECT,
        related_name='reservation_holds',
        help_text="Wallet with reserved funds"
    )
    sku = models.CharField(max_length=100, help_text="Item SKU (denormalized)")
    amount = models.IntegerField(validators=[MinValueValidator(1)], help_text="Hold amount in DeltaCoins")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='authorized', db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Expiration timestamp (nullable)")
    idempotency_key = models.CharField(max_length=255, null=True, blank=True, help_text="Idempotency key (nullable)")
    captured_txn_id = models.IntegerField(null=True, blank=True, help_text="DeltaCrownTransaction ID if captured")
    meta = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'shop_reservation_hold'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'status'], name='shop_hold_wallet_status_idx'),
            models.Index(fields=['expires_at'], name='shop_hold_expires_idx'),
            models.Index(fields=['created_at'], name='shop_hold_created_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='shop_hold_amount_positive',
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=['authorized', 'captured', 'released', 'expired']),
                name='shop_hold_status_valid',
            ),
            models.UniqueConstraint(
                fields=['idempotency_key'],
                condition=models.Q(idempotency_key__isnull=False),
                name='shop_hold_idempotency_key_unique',
            ),
        ]

    def __str__(self):
        return f"Hold #{self.id} - {self.sku} - {self.amount} DC ({self.status})"
