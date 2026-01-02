# apps/economy/inventory_api.py
"""
Phase 3A: Inventory API Endpoints
Backend-first implementation, no UI yet.
All endpoints require authentication and CSRF protection.
"""
import json
import logging

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from apps.economy.models import (
    InventoryItem,
    UserInventoryItem,
    GiftRequest,
    TradeRequest
)
from apps.economy.inventory_services import (
    can_view_inventory,
    process_gift_accept,
    process_trade_accept,
    reject_gift,
    cancel_gift,
    reject_trade,
    cancel_trade
)
from apps.user_profile.models import UserProfile
from apps.accounts.models import User

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def my_inventory_view(request):
    """
    GET /me/inventory/
    Returns authenticated user's own inventory.
    
    Response:
    {
        "success": true,
        "data": {
            "items": [
                {
                    "id": 1,
                    "item_slug": "awp-dragon-lore",
                    "item_name": "AWP | Dragon Lore",
                    "item_type": "COSMETIC",
                    "rarity": "LEGENDARY",
                    "quantity": 2,
                    "locked": false,
                    "acquired_from": "PURCHASE",
                    "acquired_at": "2026-01-02T10:00:00Z",
                    "tradable": true,
                    "giftable": true,
                    "icon_url": "..."
                },
                ...
            ],
            "total_items": 15,
            "total_unique_items": 5
        }
    }
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    
    # Get all inventory items
    inventory_items = UserInventoryItem.objects.filter(
        profile=profile
    ).select_related('item').order_by('-acquired_at')
    
    # Serialize
    items_data = []
    total_quantity = 0
    
    for inv_item in inventory_items:
        total_quantity += inv_item.quantity
        items_data.append({
            'id': inv_item.id,
            'item_slug': inv_item.item.slug,
            'item_name': inv_item.item.name,
            'item_type': inv_item.item.item_type,
            'rarity': inv_item.item.rarity,
            'quantity': inv_item.quantity,
            'locked': inv_item.locked,
            'acquired_from': inv_item.acquired_from,
            'acquired_at': inv_item.acquired_at.isoformat(),
            'tradable': inv_item.item.tradable,
            'giftable': inv_item.item.giftable,
            'icon_url': inv_item.item.icon_display_url,
            'can_trade': inv_item.can_trade(),
            'can_gift': inv_item.can_gift()
        })
    
    return JsonResponse({
        'success': True,
        'data': {
            'items': items_data,
            'total_items': total_quantity,
            'total_unique_items': len(items_data)
        }
    })


@login_required
@require_http_methods(["GET"])
def user_inventory_view(request, username):
    """
    GET /profiles/<username>/inventory/
    View another user's inventory (respects privacy settings).
    
    Privacy enforcement:
    - PUBLIC → anyone can view
    - FRIENDS → only followers can view
    - PRIVATE → only owner can view
    
    Response:
    {
        "success": true,
        "data": {
            "username": "johndoe",
            "items": [...],
            "total_items": 10,
            "total_unique_items": 3
        }
    }
    
    Or if blocked:
    {
        "success": false,
        "error": "This user's inventory is private",
        "visibility": "PRIVATE"
    }
    """
    # Get owner profile
    owner_user = get_object_or_404(User, username=username)
    try:
        owner_profile = UserProfile.objects.get(user=owner_user)
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    
    # Get viewer profile
    try:
        viewer_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        viewer_profile = None
    
    # Check visibility permission
    if not can_view_inventory(viewer_profile, owner_profile):
        return JsonResponse({
            'success': False,
            'error': "This user's inventory is private",
            'visibility': owner_profile.privacy_settings.inventory_visibility if hasattr(owner_profile, 'privacy_settings') else 'PRIVATE'
        }, status=403)
    
    # Get inventory items
    inventory_items = UserInventoryItem.objects.filter(
        profile=owner_profile
    ).select_related('item').order_by('-acquired_at')
    
    # Serialize (same format as my_inventory_view)
    items_data = []
    total_quantity = 0
    
    for inv_item in inventory_items:
        total_quantity += inv_item.quantity
        items_data.append({
            'id': inv_item.id,
            'item_slug': inv_item.item.slug,
            'item_name': inv_item.item.name,
            'item_type': inv_item.item.item_type,
            'rarity': inv_item.item.rarity,
            'quantity': inv_item.quantity,
            'locked': inv_item.locked,
            'acquired_from': inv_item.acquired_from,
            'acquired_at': inv_item.acquired_at.isoformat(),
            'tradable': inv_item.item.tradable,
            'giftable': inv_item.item.giftable,
            'icon_url': inv_item.item.icon_display_url
        })
    
    return JsonResponse({
        'success': True,
        'data': {
            'username': username,
            'items': items_data,
            'total_items': total_quantity,
            'total_unique_items': len(items_data)
        }
    })


@login_required
@csrf_protect
@require_http_methods(["POST"])
def gift_item_view(request):
    """
    POST /me/inventory/gift/
    Create a gift request to send an item to another user.
    
    Payload:
    {
        "receiver_username": "johndoe",
        "item_slug": "awp-dragon-lore",
        "quantity": 1,
        "message": "Happy birthday!" (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Gift request sent to johndoe",
        "data": {
            "gift_id": 123,
            "status": "PENDING"
        }
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    
    # Get sender profile
    try:
        sender_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    
    # Validate required fields
    receiver_username = data.get('receiver_username')
    item_slug = data.get('item_slug')
    quantity = data.get('quantity', 1)
    
    if not receiver_username or not item_slug:
        return JsonResponse({
            'success': False,
            'error': 'Missing required fields: receiver_username, item_slug'
        }, status=400)
    
    # Get receiver
    try:
        receiver_user = User.objects.get(username=receiver_username)
        receiver_profile = receiver_user.userprofile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': f'User {receiver_username} not found'
        }, status=404)
    
    # Get item
    try:
        item = InventoryItem.objects.get(slug=item_slug)
    except InventoryItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Item {item_slug} not found'
        }, status=404)
    
    # Create gift request
    try:
        gift_request = GiftRequest(
            sender_profile=sender_profile,
            receiver_profile=receiver_profile,
            item=item,
            quantity=quantity,
            message=data.get('message', '')
        )
        gift_request.full_clean()  # Validate
        gift_request.save()
        
        logger.info(
            f"Gift request created: {sender_profile.user.username} → "
            f"{receiver_profile.user.username} ({quantity}x {item.name})"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Gift request sent to {receiver_username}',
            'data': {
                'gift_id': gift_request.id,
                'status': gift_request.status
            }
        })
    
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def trade_request_view(request):
    """
    POST /me/inventory/trade/request/
    Create a trade request.
    
    Payload:
    {
        "target_username": "johndoe",
        "offered_item_slug": "awp-dragon-lore",
        "offered_quantity": 1,
        "requested_item_slug": "ak47-fire-serpent" (optional),
        "requested_quantity": 1 (optional),
        "message": "Want to trade?" (optional)
    }
    
    Response:
    {
        "success": true,
        "message": "Trade request sent to johndoe",
        "data": {
            "trade_id": 456,
            "status": "PENDING"
        }
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    
    # Get initiator profile
    try:
        initiator_profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    
    # Validate required fields
    target_username = data.get('target_username')
    offered_item_slug = data.get('offered_item_slug')
    offered_quantity = data.get('offered_quantity', 1)
    
    if not target_username or not offered_item_slug:
        return JsonResponse({
            'success': False,
            'error': 'Missing required fields: target_username, offered_item_slug'
        }, status=400)
    
    # Get target
    try:
        target_user = User.objects.get(username=target_username)
        target_profile = target_user.userprofile
    except (User.DoesNotExist, UserProfile.DoesNotExist):
        return JsonResponse({
            'success': False,
            'error': f'User {target_username} not found'
        }, status=404)
    
    # Get offered item
    try:
        offered_item = InventoryItem.objects.get(slug=offered_item_slug)
    except InventoryItem.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Item {offered_item_slug} not found'
        }, status=404)
    
    # Get requested item (optional)
    requested_item = None
    requested_quantity = None
    requested_item_slug = data.get('requested_item_slug')
    
    if requested_item_slug:
        try:
            requested_item = InventoryItem.objects.get(slug=requested_item_slug)
            requested_quantity = data.get('requested_quantity', 1)
        except InventoryItem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Requested item {requested_item_slug} not found'
            }, status=404)
    
    # Create trade request
    try:
        trade_request = TradeRequest(
            initiator_profile=initiator_profile,
            target_profile=target_profile,
            offered_item=offered_item,
            offered_quantity=offered_quantity,
            requested_item=requested_item,
            requested_quantity=requested_quantity,
            message=data.get('message', '')
        )
        trade_request.full_clean()  # Validate
        trade_request.save()
        
        logger.info(
            f"Trade request created: {initiator_profile.user.username} → "
            f"{target_profile.user.username} "
            f"(offering {offered_quantity}x {offered_item.name})"
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Trade request sent to {target_username}',
            'data': {
                'trade_id': trade_request.id,
                'status': trade_request.status
            }
        })
    
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def trade_respond_view(request):
    """
    POST /me/inventory/trade/respond/
    Respond to a gift or trade request (accept/reject/cancel).
    
    Payload:
    {
        "request_type": "gift" | "trade",
        "request_id": 123,
        "action": "ACCEPT" | "REJECT" | "CANCEL"
    }
    
    Response:
    {
        "success": true,
        "message": "Gift accepted" | "Trade rejected" | "Gift canceled"
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    
    # Validate required fields
    request_type = data.get('request_type')
    request_id = data.get('request_id')
    action = data.get('action')
    
    if not all([request_type, request_id, action]):
        return JsonResponse({
            'success': False,
            'error': 'Missing required fields: request_type, request_id, action'
        }, status=400)
    
    if request_type not in ['gift', 'trade']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid request_type. Must be "gift" or "trade"'
        }, status=400)
    
    if action not in ['ACCEPT', 'REJECT', 'CANCEL']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid action. Must be ACCEPT, REJECT, or CANCEL'
        }, status=400)
    
    # Get user profile
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    
    # Process gift request
    if request_type == 'gift':
        try:
            gift_request = GiftRequest.objects.select_related(
                'sender_profile__user',
                'receiver_profile__user',
                'item'
            ).get(id=request_id)
        except GiftRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Gift request not found'
            }, status=404)
        
        # Permission check
        if action == 'CANCEL':
            if gift_request.sender_profile != profile:
                return JsonResponse({
                    'success': False,
                    'error': 'Only sender can cancel gift'
                }, status=403)
            result = cancel_gift(gift_request)
        else:
            # ACCEPT or REJECT must be receiver
            if gift_request.receiver_profile != profile:
                return JsonResponse({
                    'success': False,
                    'error': 'Only receiver can accept/reject gift'
                }, status=403)
            
            if action == 'ACCEPT':
                result = process_gift_accept(gift_request)
            else:  # REJECT
                result = reject_gift(gift_request)
        
        return JsonResponse(result)
    
    # Process trade request
    else:  # request_type == 'trade'
        try:
            trade_request = TradeRequest.objects.select_related(
                'initiator_profile__user',
                'target_profile__user',
                'offered_item',
                'requested_item'
            ).get(id=request_id)
        except TradeRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Trade request not found'
            }, status=404)
        
        # Permission check
        if action == 'CANCEL':
            if trade_request.initiator_profile != profile:
                return JsonResponse({
                    'success': False,
                    'error': 'Only initiator can cancel trade'
                }, status=403)
            result = cancel_trade(trade_request)
        else:
            # ACCEPT or REJECT must be target
            if trade_request.target_profile != profile:
                return JsonResponse({
                    'success': False,
                    'error': 'Only target can accept/reject trade'
                }, status=403)
            
            if action == 'ACCEPT':
                result = process_trade_accept(trade_request)
            else:  # REJECT
                result = reject_trade(trade_request)
        
        return JsonResponse(result)


@login_required
@require_http_methods(["GET"])
def my_requests_view(request):
    """
    GET /me/inventory/requests/
    Fetch all gift and trade requests for authenticated user.
    
    Returns both incoming (received by me) and outgoing (sent by me) requests.
    
    Query params:
    - direction: "incoming" | "outgoing" | "all" (default: "all")
    - status: "PENDING" | "ACCEPTED" | "REJECTED" | "CANCELED" (optional, filters by status)
    - type: "gift" | "trade" (optional, filters by type)
    
    Response:
    {
        "success": true,
        "data": {
            "incoming": {
                "gifts": [
                    {
                        "id": 123,
                        "type": "gift",
                        "sender_username": "alice",
                        "sender_avatar": "...",
                        "item_name": "AWP | Dragon Lore",
                        "item_slug": "awp-dragon-lore",
                        "item_icon": "...",
                        "quantity": 1,
                        "message": "Happy birthday!",
                        "status": "PENDING",
                        "created_at": "2026-01-01T12:00:00Z",
                        "expires_at": "2026-01-08T12:00:00Z"
                    }
                ],
                "trades": [
                    {
                        "id": 456,
                        "type": "trade",
                        "initiator_username": "bob",
                        "initiator_avatar": "...",
                        "offered_item_name": "M4A4 | Howl",
                        "offered_item_slug": "m4a4-howl",
                        "offered_item_icon": "...",
                        "offered_quantity": 1,
                        "requested_item_name": "AWP | Dragon Lore",
                        "requested_item_slug": "awp-dragon-lore",
                        "requested_item_icon": "...",
                        "requested_quantity": 1,
                        "message": "Fair trade?",
                        "status": "PENDING",
                        "created_at": "2026-01-01T14:00:00Z",
                        "expires_at": "2026-01-08T14:00:00Z"
                    }
                ]
            },
            "outgoing": {
                "gifts": [...],
                "trades": [...]
            }
        }
    }
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    
    # Query params
    direction = request.GET.get('direction', 'all')
    status_filter = request.GET.get('status', None)
    type_filter = request.GET.get('type', None)
    
    # Validate params
    if direction not in ['incoming', 'outgoing', 'all']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid direction. Must be: incoming, outgoing, or all'
        }, status=400)
    
    if status_filter and status_filter not in ['PENDING', 'ACCEPTED', 'REJECTED', 'CANCELED']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid status. Must be: PENDING, ACCEPTED, REJECTED, or CANCELED'
        }, status=400)
    
    if type_filter and type_filter not in ['gift', 'trade']:
        return JsonResponse({
            'success': False,
            'error': 'Invalid type. Must be: gift or trade'
        }, status=400)
    
    result = {
        'success': True,
        'data': {}
    }
    
    # Helper function to serialize gift request
    def serialize_gift(gift_req, is_incoming):
        return {
            'id': gift_req.id,
            'type': 'gift',
            'direction': 'incoming' if is_incoming else 'outgoing',
            'sender_username': gift_req.sender_profile.user.username,
            'sender_avatar': gift_req.sender_profile.avatar_display_url,
            'receiver_username': gift_req.receiver_profile.user.username,
            'receiver_avatar': gift_req.receiver_profile.avatar_display_url,
            'item_name': gift_req.item.name,
            'item_slug': gift_req.item.slug,
            'item_icon': gift_req.item.icon_display_url,
            'item_rarity': gift_req.item.rarity,
            'quantity': gift_req.quantity,
            'message': gift_req.message or '',
            'status': gift_req.status,
            'created_at': gift_req.created_at.isoformat(),
            'expires_at': gift_req.expires_at.isoformat() if gift_req.expires_at else None,
            'resolved_at': gift_req.resolved_at.isoformat() if gift_req.resolved_at else None
        }
    
    # Helper function to serialize trade request
    def serialize_trade(trade_req, is_incoming):
        return {
            'id': trade_req.id,
            'type': 'trade',
            'direction': 'incoming' if is_incoming else 'outgoing',
            'initiator_username': trade_req.initiator_profile.user.username,
            'initiator_avatar': trade_req.initiator_profile.avatar_display_url,
            'target_username': trade_req.target_profile.user.username,
            'target_avatar': trade_req.target_profile.avatar_display_url,
            'offered_item_name': trade_req.offered_item.name,
            'offered_item_slug': trade_req.offered_item.slug,
            'offered_item_icon': trade_req.offered_item.icon_display_url,
            'offered_item_rarity': trade_req.offered_item.rarity,
            'offered_quantity': trade_req.offered_quantity,
            'requested_item_name': trade_req.requested_item.name if trade_req.requested_item else None,
            'requested_item_slug': trade_req.requested_item.slug if trade_req.requested_item else None,
            'requested_item_icon': trade_req.requested_item.icon_display_url if trade_req.requested_item else None,
            'requested_item_rarity': trade_req.requested_item.rarity if trade_req.requested_item else None,
            'requested_quantity': trade_req.requested_quantity,
            'message': trade_req.message or '',
            'status': trade_req.status,
            'created_at': trade_req.created_at.isoformat(),
            'expires_at': trade_req.expires_at.isoformat() if trade_req.expires_at else None,
            'resolved_at': trade_req.resolved_at.isoformat() if trade_req.resolved_at else None
        }
    
    # Fetch incoming requests
    if direction in ['incoming', 'all']:
        # Incoming gifts (I'm the receiver)
        incoming_gifts_query = GiftRequest.objects.filter(
            receiver_profile=profile
        ).select_related(
            'sender_profile__user',
            'receiver_profile__user',
            'item'
        ).order_by('-created_at')
        
        if status_filter:
            incoming_gifts_query = incoming_gifts_query.filter(status=status_filter)
        
        # Incoming trades (I'm the target)
        incoming_trades_query = TradeRequest.objects.filter(
            target_profile=profile
        ).select_related(
            'initiator_profile__user',
            'target_profile__user',
            'offered_item',
            'requested_item'
        ).order_by('-created_at')
        
        if status_filter:
            incoming_trades_query = incoming_trades_query.filter(status=status_filter)
        
        incoming_data = {}
        
        if not type_filter or type_filter == 'gift':
            incoming_data['gifts'] = [serialize_gift(g, True) for g in incoming_gifts_query]
        
        if not type_filter or type_filter == 'trade':
            incoming_data['trades'] = [serialize_trade(t, True) for t in incoming_trades_query]
        
        result['data']['incoming'] = incoming_data
    
    # Fetch outgoing requests
    if direction in ['outgoing', 'all']:
        # Outgoing gifts (I'm the sender)
        outgoing_gifts_query = GiftRequest.objects.filter(
            sender_profile=profile
        ).select_related(
            'sender_profile__user',
            'receiver_profile__user',
            'item'
        ).order_by('-created_at')
        
        if status_filter:
            outgoing_gifts_query = outgoing_gifts_query.filter(status=status_filter)
        
        # Outgoing trades (I'm the initiator)
        outgoing_trades_query = TradeRequest.objects.filter(
            initiator_profile=profile
        ).select_related(
            'initiator_profile__user',
            'target_profile__user',
            'offered_item',
            'requested_item'
        ).order_by('-created_at')
        
        if status_filter:
            outgoing_trades_query = outgoing_trades_query.filter(status=status_filter)
        
        outgoing_data = {}
        
        if not type_filter or type_filter == 'gift':
            outgoing_data['gifts'] = [serialize_gift(g, False) for g in outgoing_gifts_query]
        
        if not type_filter or type_filter == 'trade':
            outgoing_data['trades'] = [serialize_trade(t, False) for t in outgoing_trades_query]
        
        result['data']['outgoing'] = outgoing_data
    
    return JsonResponse(result)
