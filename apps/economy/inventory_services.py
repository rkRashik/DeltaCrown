# apps/economy/inventory_services.py
"""
Phase 3A: Inventory Service Layer
Handles inventory visibility, gift/trade operations with atomic guarantees.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.economy.models import (
    InventoryItem,
    UserInventoryItem,
    GiftRequest,
    TradeRequest
)
from apps.user_profile.models import UserProfile, PrivacySettings


def can_view_inventory(viewer_profile: UserProfile, owner_profile: UserProfile) -> bool:
    """
    Check if viewer can see owner's inventory based on privacy settings.
    
    Args:
        viewer_profile: Profile trying to view inventory (None if anonymous)
        owner_profile: Profile whose inventory is being viewed
    
    Returns:
        True if viewer can see inventory, False otherwise
    
    Rules:
        - PUBLIC → anyone can view
        - FRIENDS → only friends/followers can view
        - PRIVATE → only owner can view
    """
    # Get privacy settings
    try:
        privacy = PrivacySettings.objects.get(user_profile=owner_profile)
        visibility = privacy.inventory_visibility
    except PrivacySettings.DoesNotExist:
        # Default to PUBLIC if no privacy settings exist
        visibility = 'PUBLIC'
    
    # PUBLIC: everyone can view
    if visibility == 'PUBLIC':
        return True
    
    # If viewer is anonymous, can only view PUBLIC
    if viewer_profile is None:
        return False
    
    # Owner can always view own inventory
    if viewer_profile.id == owner_profile.id:
        return True
    
    # PRIVATE: only owner can view
    if visibility == 'PRIVATE':
        return False
    
    # FRIENDS: check if viewer follows owner
    if visibility == 'FRIENDS':
        # Check if viewer follows owner (simplified friend check)
        from apps.user_profile.models import Follow
        try:
            Follow.objects.get(follower=viewer_profile.user, following=owner_profile.user)
            return True
        except Follow.DoesNotExist:
            return False
    
    # Default deny
    return False


@transaction.atomic
def process_gift_accept(gift_request: GiftRequest) -> dict:
    """
    Process gift acceptance with atomic transfer.
    
    Args:
        gift_request: GiftRequest to accept
    
    Returns:
        dict with success status and message
    
    Raises:
        ValidationError: If gift cannot be processed
    """
    # Validation: must be pending
    if gift_request.status != GiftRequest.Status.PENDING:
        raise ValidationError(f"Cannot accept gift with status '{gift_request.status}'")
    
    # Validate sender still owns sufficient quantity
    try:
        sender_inventory = UserInventoryItem.objects.select_for_update().get(
            profile=gift_request.sender_profile,
            item=gift_request.item
        )
    except UserInventoryItem.DoesNotExist:
        raise ValidationError("Sender no longer owns this item")
    
    # Check quantity
    if sender_inventory.quantity < gift_request.quantity:
        raise ValidationError(
            f"Insufficient quantity. Sender has {sender_inventory.quantity}, "
            f"gift requires {gift_request.quantity}"
        )
    
    # Check locked status
    if sender_inventory.locked:
        raise ValidationError("Item is locked and cannot be gifted")
    
    # Atomic transfer
    # Step 1: Decrease sender quantity
    sender_inventory.quantity -= gift_request.quantity
    if sender_inventory.quantity == 0:
        sender_inventory.delete()
    else:
        sender_inventory.save(update_fields=['quantity', 'updated_at'])
    
    # Step 2: Increase receiver quantity (or create)
    receiver_inventory, created = UserInventoryItem.objects.get_or_create(
        profile=gift_request.receiver_profile,
        item=gift_request.item,
        defaults={
            'quantity': gift_request.quantity,
            'acquired_from': UserInventoryItem.AcquiredFrom.GIFT,
            'locked': False
        }
    )
    
    if not created:
        receiver_inventory.quantity += gift_request.quantity
        receiver_inventory.save(update_fields=['quantity', 'updated_at'])
    
    # Step 3: Update gift request status
    gift_request.status = GiftRequest.Status.ACCEPTED
    gift_request.resolved_at = timezone.now()
    gift_request.save(update_fields=['status', 'resolved_at'])
    
    return {
        'success': True,
        'message': f'Gift accepted: {gift_request.quantity}x {gift_request.item.name}'
    }


@transaction.atomic
def process_trade_accept(trade_request: TradeRequest) -> dict:
    """
    Process trade acceptance with atomic swap.
    
    Args:
        trade_request: TradeRequest to accept
    
    Returns:
        dict with success status and message
    
    Raises:
        ValidationError: If trade cannot be processed
    """
    # Validation: must be pending
    if trade_request.status != TradeRequest.Status.PENDING:
        raise ValidationError(f"Cannot accept trade with status '{trade_request.status}'")
    
    # Lock both parties' inventories
    try:
        initiator_offered = UserInventoryItem.objects.select_for_update().get(
            profile=trade_request.initiator_profile,
            item=trade_request.offered_item
        )
    except UserInventoryItem.DoesNotExist:
        raise ValidationError("Initiator no longer owns offered item")
    
    # Validate initiator's offered quantity
    if initiator_offered.quantity < trade_request.offered_quantity:
        raise ValidationError(
            f"Initiator has insufficient quantity. "
            f"Has {initiator_offered.quantity}, offered {trade_request.offered_quantity}"
        )
    
    if initiator_offered.locked:
        raise ValidationError("Offered item is locked")
    
    # If trade requests an item in return, validate target owns it
    if trade_request.requested_item:
        try:
            target_requested = UserInventoryItem.objects.select_for_update().get(
                profile=trade_request.target_profile,
                item=trade_request.requested_item
            )
        except UserInventoryItem.DoesNotExist:
            raise ValidationError("Target no longer owns requested item")
        
        if target_requested.quantity < trade_request.requested_quantity:
            raise ValidationError(
                f"Target has insufficient quantity. "
                f"Has {target_requested.quantity}, requested {trade_request.requested_quantity}"
            )
        
        if target_requested.locked:
            raise ValidationError("Requested item is locked")
        
        # Atomic swap: Move requested item from target to initiator
        target_requested.quantity -= trade_request.requested_quantity
        if target_requested.quantity == 0:
            target_requested.delete()
        else:
            target_requested.save(update_fields=['quantity', 'updated_at'])
        
        # Give requested item to initiator
        initiator_received, created = UserInventoryItem.objects.get_or_create(
            profile=trade_request.initiator_profile,
            item=trade_request.requested_item,
            defaults={
                'quantity': trade_request.requested_quantity,
                'acquired_from': UserInventoryItem.AcquiredFrom.TRADE,
                'locked': False
            }
        )
        
        if not created:
            initiator_received.quantity += trade_request.requested_quantity
            initiator_received.save(update_fields=['quantity', 'updated_at'])
    
    # Move offered item from initiator to target
    initiator_offered.quantity -= trade_request.offered_quantity
    if initiator_offered.quantity == 0:
        initiator_offered.delete()
    else:
        initiator_offered.save(update_fields=['quantity', 'updated_at'])
    
    # Give offered item to target
    target_received, created = UserInventoryItem.objects.get_or_create(
        profile=trade_request.target_profile,
        item=trade_request.offered_item,
        defaults={
            'quantity': trade_request.offered_quantity,
            'acquired_from': UserInventoryItem.AcquiredFrom.TRADE,
            'locked': False
        }
    )
    
    if not created:
        target_received.quantity += trade_request.offered_quantity
        target_received.save(update_fields=['quantity', 'updated_at'])
    
    # Update trade request status
    trade_request.status = TradeRequest.Status.ACCEPTED
    trade_request.resolved_at = timezone.now()
    trade_request.save(update_fields=['status', 'resolved_at'])
    
    return {
        'success': True,
        'message': 'Trade completed successfully'
    }


def reject_gift(gift_request: GiftRequest) -> dict:
    """
    Reject a gift request.
    
    Args:
        gift_request: GiftRequest to reject
    
    Returns:
        dict with success status and message
    """
    if gift_request.status != GiftRequest.Status.PENDING:
        raise ValidationError(f"Cannot reject gift with status '{gift_request.status}'")
    
    gift_request.status = GiftRequest.Status.REJECTED
    gift_request.resolved_at = timezone.now()
    gift_request.save(update_fields=['status', 'resolved_at'])
    
    return {
        'success': True,
        'message': 'Gift rejected'
    }


def cancel_gift(gift_request: GiftRequest) -> dict:
    """
    Cancel a gift request (sender-initiated).
    
    Args:
        gift_request: GiftRequest to cancel
    
    Returns:
        dict with success status and message
    """
    if gift_request.status != GiftRequest.Status.PENDING:
        raise ValidationError(f"Cannot cancel gift with status '{gift_request.status}'")
    
    gift_request.status = GiftRequest.Status.CANCELED
    gift_request.resolved_at = timezone.now()
    gift_request.save(update_fields=['status', 'resolved_at'])
    
    return {
        'success': True,
        'message': 'Gift canceled'
    }


def reject_trade(trade_request: TradeRequest) -> dict:
    """
    Reject a trade request.
    
    Args:
        trade_request: TradeRequest to reject
    
    Returns:
        dict with success status and message
    """
    if trade_request.status != TradeRequest.Status.PENDING:
        raise ValidationError(f"Cannot reject trade with status '{trade_request.status}'")
    
    trade_request.status = TradeRequest.Status.REJECTED
    trade_request.resolved_at = timezone.now()
    trade_request.save(update_fields=['status', 'resolved_at'])
    
    return {
        'success': True,
        'message': 'Trade rejected'
    }


def cancel_trade(trade_request: TradeRequest) -> dict:
    """
    Cancel a trade request (initiator-initiated).
    
    Args:
        trade_request: TradeRequest to cancel
    
    Returns:
        dict with success status and message
    """
    if trade_request.status != TradeRequest.Status.PENDING:
        raise ValidationError(f"Cannot cancel trade with status '{trade_request.status}'")
    
    trade_request.status = TradeRequest.Status.CANCELED
    trade_request.resolved_at = timezone.now()
    trade_request.save(update_fields=['status', 'resolved_at'])
    
    return {
        'success': True,
        'message': 'Trade canceled'
    }
