# apps/economy/models/social.py
from __future__ import annotations

from django.db import models

from apps.common.managers import SoftDeleteManager
from apps.common.models import SoftDeleteModel
from .inventory import InventoryItem, UserInventoryItem


class GiftRequest(SoftDeleteModel):
    """
    Gift request from one user to another.
    Phase 3A Foundation - Request-based flow only, no UI yet.
    
    Workflow:
    1. Sender creates gift request
    2. Receiver accepts/rejects
    3. On accept: atomic transfer
    4. On reject/cancel: no action
    
    Rules:
    - Item must be giftable
    - Sender must own sufficient quantity
    - Cannot gift locked items
    - Sender != Receiver
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELED = 'CANCELED', 'Canceled'
    
    # Parties
    sender_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='gifts_sent'
    )
    receiver_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='gifts_received'
    )
    
    # Item Details
    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='gift_requests'
    )
    quantity = models.PositiveIntegerField(default=1)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Optional Message
    message = models.TextField(
        blank=True,
        default='',
        max_length=500,
        help_text='Optional message from sender'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'economy_gift_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender_profile', '-created_at']),
            models.Index(fields=['receiver_profile', 'status', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        verbose_name = 'Gift Request'
        verbose_name_plural = 'Gift Requests'
    
    def __str__(self):
        sender_name = getattr(self.sender_profile.user, 'username', 'Unknown')
        receiver_name = getattr(self.receiver_profile.user, 'username', 'Unknown')
        return f"Gift: {sender_name} → {receiver_name} ({self.quantity}x {self.item.name}) - {self.status}"
    
    def clean(self):
        """Validation rules"""
        from django.core.exceptions import ValidationError
        
        if self.sender_profile_id == self.receiver_profile_id:
            raise ValidationError("Cannot gift items to yourself")
        
        if not self.item.giftable:
            raise ValidationError(f"Item '{self.item.name}' is not giftable")
        
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than 0")
        
        if self.pk is None:
            try:
                sender_inventory = UserInventoryItem.objects.get(
                    profile=self.sender_profile,
                    item=self.item
                )
                
                if sender_inventory.locked:
                    raise ValidationError("Cannot gift locked items")
                
                if sender_inventory.quantity < self.quantity:
                    raise ValidationError(
                        f"Insufficient quantity. Have: {sender_inventory.quantity}, "
                        f"Requested: {self.quantity}"
                    )
            except UserInventoryItem.DoesNotExist:
                raise ValidationError(f"You do not own '{self.item.name}'")


class TradeRequest(SoftDeleteModel):
    """
    Trade request between two users (1-sided offers for Phase 3A).
    Phase 3A Foundation - Simple 1-for-nothing offers, no complex barter yet.
    
    Workflow:
    1. Initiator creates trade request (offers item, optionally requests item)
    2. Target accepts/rejects
    3. On accept: atomic swap
    4. On reject/cancel: no action
    """
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELED = 'CANCELED', 'Canceled'
    
    # Parties
    initiator_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='trades_initiated'
    )
    target_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='trades_received'
    )
    
    # Offered Item (what initiator gives)
    offered_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='trade_offers'
    )
    offered_quantity = models.PositiveIntegerField(default=1)
    
    # Requested Item (what initiator wants - nullable for simple gifts)
    requested_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='trade_requests',
        null=True,
        blank=True,
        help_text='Optional: What initiator wants in return'
    )
    requested_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Quantity of requested item'
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Optional Message
    message = models.TextField(
        blank=True,
        default='',
        max_length=500,
        help_text='Optional message from initiator'
    )
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        db_table = 'economy_trade_request'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['initiator_profile', '-created_at']),
            models.Index(fields=['target_profile', 'status', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]
        verbose_name = 'Trade Request'
        verbose_name_plural = 'Trade Requests'
    
    def __str__(self):
        initiator_name = getattr(self.initiator_profile.user, 'username', 'Unknown')
        target_name = getattr(self.target_profile.user, 'username', 'Unknown')
        request_part = f" for {self.requested_quantity}x {self.requested_item.name}" if self.requested_item else ""
        return f"Trade: {initiator_name} → {target_name} ({self.offered_quantity}x {self.offered_item.name}{request_part}) - {self.status}"
    
    def clean(self):
        """Validation rules"""
        from django.core.exceptions import ValidationError
        
        if self.initiator_profile_id == self.target_profile_id:
            raise ValidationError("Cannot trade with yourself")
        
        if not self.offered_item.tradable:
            raise ValidationError(f"Item '{self.offered_item.name}' is not tradable")
        
        if self.requested_item and not self.requested_item.tradable:
            raise ValidationError(f"Requested item '{self.requested_item.name}' is not tradable")
        
        if self.offered_quantity <= 0:
            raise ValidationError("Offered quantity must be greater than 0")
        
        if self.requested_item and (self.requested_quantity is None or self.requested_quantity <= 0):
            raise ValidationError("Requested quantity must be greater than 0 when requesting an item")
        
        if self.pk is None:
            try:
                initiator_inventory = UserInventoryItem.objects.get(
                    profile=self.initiator_profile,
                    item=self.offered_item
                )
                
                if initiator_inventory.locked:
                    raise ValidationError("Cannot trade locked items")
                
                if initiator_inventory.quantity < self.offered_quantity:
                    raise ValidationError(
                        f"Insufficient quantity. Have: {initiator_inventory.quantity}, "
                        f"Offered: {self.offered_quantity}"
                    )
            except UserInventoryItem.DoesNotExist:
                raise ValidationError(f"You do not own '{self.offered_item.name}'")
            
            if self.requested_item:
                try:
                    target_inventory = UserInventoryItem.objects.get(
                        profile=self.target_profile,
                        item=self.requested_item
                    )
                    
                    if target_inventory.locked:
                        raise ValidationError("Target's item is locked and cannot be traded")
                    
                    if target_inventory.quantity < self.requested_quantity:
                        raise ValidationError(
                            f"Target has insufficient quantity. "
                            f"They have: {target_inventory.quantity}, "
                            f"You requested: {self.requested_quantity}"
                        )
                except UserInventoryItem.DoesNotExist:
                    raise ValidationError(
                        f"Target does not own '{self.requested_item.name}'"
                    )
