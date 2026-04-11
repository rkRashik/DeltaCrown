# apps/economy/models/inventory.py
from __future__ import annotations

from django.db import models

from apps.common.validators import validate_image_upload
from apps.common.models import SoftDeleteModel


class InventoryItem(SoftDeleteModel):
    """
    Master data for inventory items (cosmetics, cases, tokens, collectibles, badges).
    Immutable after creation (slug cannot change).
    
    Phase 3A Foundation - No marketplace yet.
    """
    class ItemType(models.TextChoices):
        COSMETIC = 'COSMETIC', 'Cosmetic Skin'
        CASE = 'CASE', 'Loot Case'
        TOKEN = 'TOKEN', 'Special Token'
        COLLECTIBLE = 'COLLECTIBLE', 'Collectible Item'
        BADGE = 'BADGE', 'Achievement Badge'
    
    class Rarity(models.TextChoices):
        COMMON = 'COMMON', 'Common'
        RARE = 'RARE', 'Rare'
        EPIC = 'EPIC', 'Epic'
        LEGENDARY = 'LEGENDARY', 'Legendary'
    
    # Core Fields
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text='Unique immutable identifier (e.g., awp-dragon-lore)'
    )
    name = models.CharField(
        max_length=200,
        help_text='Display name (e.g., AWP | Dragon Lore)'
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Item description for users'
    )
    
    # Classification
    item_type = models.CharField(
        max_length=20,
        choices=ItemType.choices,
        db_index=True
    )
    rarity = models.CharField(
        max_length=20,
        choices=Rarity.choices,
        db_index=True
    )
    
    # Trade & Gift Controls
    tradable = models.BooleanField(
        default=False,
        help_text='Can this item be traded between users?'
    )
    giftable = models.BooleanField(
        default=False,
        help_text='Can this item be gifted to other users?'
    )
    
    # Visuals
    icon = models.ImageField(
        upload_to='inventory/items/',
        blank=True,
        null=True,
        help_text='Item icon/image',
        validators=[validate_image_upload],
    )
    icon_url = models.URLField(
        max_length=500,
        blank=True,
        default='',
        help_text='External icon URL (if not using ImageField)'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional item data (game-specific, stats, etc.)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'economy_inventory_item'
        ordering = ['name']
        indexes = [
            models.Index(fields=['item_type', 'rarity']),
            models.Index(fields=['slug']),
        ]
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
    
    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"
    
    @property
    def icon_display_url(self):
        """Get icon URL (ImageField or external URL)"""
        if self.icon:
            return self.icon.url
        return self.icon_url or ''


class UserInventoryItem(SoftDeleteModel):
    """
    User ownership of inventory items.
    Tracks quantity, acquisition method, and locked status.
    
    Constraints:
    - Unique(profile, item) - one row per user per item
    - quantity >= 0 enforced via CHECK constraint
    - locked items cannot be traded/gifted (enforced in views)
    """
    class AcquiredFrom(models.TextChoices):
        PURCHASE = 'PURCHASE', 'Purchase'
        REWARD = 'REWARD', 'Reward'
        GIFT = 'GIFT', 'Gift'
        TRADE = 'TRADE', 'Trade'
        ADMIN = 'ADMIN', 'Admin Grant'
    
    # Ownership
    profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='owned_inventory_items'
    )
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='owned_by'
    )
    
    # Quantity & Status
    quantity = models.PositiveIntegerField(
        default=1,
        help_text='How many of this item the user owns'
    )
    locked = models.BooleanField(
        default=False,
        help_text='Locked items cannot be traded/gifted'
    )
    
    # Acquisition Context
    acquired_from = models.CharField(
        max_length=20,
        choices=AcquiredFrom.choices,
        db_index=True
    )
    acquired_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'economy_user_inventory_item'
        unique_together = [['profile', 'item']]
        ordering = ['-acquired_at']
        indexes = [
            models.Index(fields=['profile', '-acquired_at']),
            models.Index(fields=['acquired_from']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name='economy_user_inventory_quantity_nonnegative'
            )
        ]
        verbose_name = 'User Inventory Item'
        verbose_name_plural = 'User Inventory Items'
    
    def __str__(self):
        username = getattr(self.profile.user, 'username', 'Unknown')
        return f"{username} owns {self.quantity}x {self.item.name}"
    
    def can_trade(self) -> bool:
        """Check if this inventory item can be traded"""
        return (
            not self.locked and
            self.item.tradable and
            self.quantity > 0
        )
    
    def can_gift(self) -> bool:
        """Check if this inventory item can be gifted"""
        return (
            not self.locked and
            self.item.giftable and
            self.quantity > 0
        )
