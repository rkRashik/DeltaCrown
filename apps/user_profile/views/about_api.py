"""
Profile About API - CRUD endpoints for ProfileAboutItem

Allows users to manage their Facebook-style About section:
- GET: List all About items (with viewer role filtering)
- POST: Create new About item
- PATCH: Update existing item (text, visibility, order)
- DELETE: Remove About item

All endpoints enforce ownership and privacy.

Created: Phase 15 (2025-12-29)
"""
import logging
import json
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.db import models
from apps.user_profile.models import ProfileAboutItem, UserProfile
from apps.user_profile.utils import get_user_profile_safe

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def get_about_items(request):
    """
    Get user's About items (ordered list).
    
    GET /api/profile/about/
    
    Returns:
        {
            "success": true,
            "items": [
                {
                    "id": 1,
                    "item_type": "team",
                    "display_text": "Captain at Team Delta",
                    "icon_emoji": "👑",
                    "visibility": "public",
                    "order_index": 0,
                    "source_model": "Team",
                    "source_id": 123
                },
                ...
            ]
        }
    """
    try:
        profile = get_user_profile_safe(request.user)
        
        items = ProfileAboutItem.objects.filter(
            user_profile=profile,
            is_active=True
        ).order_by('order_index', '-created_at')
        
        items_data = [
            {
                'id': item.id,
                'item_type': item.item_type,
                'display_text': item.display_text,
                'icon_emoji': item.icon_emoji,
                'visibility': item.visibility,
                'order_index': item.order_index,
                'source_model': item.source_model,
                'source_id': item.source_id,
                'created_at': item.created_at.isoformat() if item.created_at else None
            }
            for item in items
        ]
        
        return JsonResponse({
            'success': True,
            'items': items_data
        })
        
    except Exception as e:
        logger.error(f"Error getting About items: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to load About items'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def create_about_item(request):
    """
    Create new About item.
    
    POST /api/profile/about/create/
    
    Body:
        {
            "item_type": "team",  // team, game, achievement, stat, bio, custom
            "display_text": "Captain at Team Delta",
            "icon_emoji": "👑",  // optional
            "visibility": "public",  // public, followers_only, private
            "source_model": "Team",  // optional
            "source_id": 123  // optional
        }
    
    Returns:
        {"success": true, "item": {...}}
    """
    try:
        profile = get_user_profile_safe(request.user)
        
        # Parse JSON body
        data = json.loads(request.body)
        
        # Validate required fields
        item_type = data.get('item_type', '').strip()
        display_text = data.get('display_text', '').strip()
        
        if not item_type or item_type not in dict(ProfileAboutItem.TYPE_CHOICES):
            return JsonResponse({
                'success': False,
                'error': 'Invalid item_type'
            }, status=400)
        
        if not display_text:
            return JsonResponse({
                'success': False,
                'error': 'display_text is required'
            }, status=400)
        
        if len(display_text) > 200:
            return JsonResponse({
                'success': False,
                'error': 'display_text must be 200 characters or less'
            }, status=400)
        
        # Validate visibility
        visibility = data.get('visibility', ProfileAboutItem.VISIBILITY_PUBLIC)
        if visibility not in dict(ProfileAboutItem.VISIBILITY_CHOICES):
            visibility = ProfileAboutItem.VISIBILITY_PUBLIC
        
        # Get next order index
        max_order = ProfileAboutItem.objects.filter(
            user_profile=profile,
            is_active=True
        ).aggregate(models.Max('order_index'))['order_index__max'] or 0
        
        # Create item
        with transaction.atomic():
            item = ProfileAboutItem.objects.create(
                user_profile=profile,
                item_type=item_type,
                display_text=display_text,
                icon_emoji=data.get('icon_emoji', '')[:10],
                visibility=visibility,
                source_model=data.get('source_model', '')[:100],
                source_id=data.get('source_id'),
                order_index=max_order + 1,
                is_active=True
            )
        
        return JsonResponse({
            'success': True,
            'message': 'About item created',
            'item': {
                'id': item.id,
                'item_type': item.item_type,
                'display_text': item.display_text,
                'icon_emoji': item.icon_emoji,
                'visibility': item.visibility,
                'order_index': item.order_index
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error creating About item: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to create About item'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_about_item(request, item_id):
    """
    Update existing About item.
    
    POST /api/profile/about/<item_id>/update/
    
    Body:
        {
            "display_text": "Updated text",  // optional
            "icon_emoji": "🎮",  // optional
            "visibility": "followers_only"  // optional
        }
    
    Returns:
        {"success": true, "item": {...}}
    """
    try:
        profile = get_user_profile_safe(request.user)
        
        # Get item (ownership check)
        try:
            item = ProfileAboutItem.objects.get(
                id=item_id,
                user_profile=profile
            )
        except ProfileAboutItem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'About item not found'
            }, status=404)
        
        # Parse JSON body
        data = json.loads(request.body)
        
        # Update fields if provided
        if 'display_text' in data:
            display_text = data['display_text'].strip()
            if not display_text:
                return JsonResponse({
                    'success': False,
                    'error': 'display_text cannot be empty'
                }, status=400)
            if len(display_text) > 200:
                return JsonResponse({
                    'success': False,
                    'error': 'display_text must be 200 characters or less'
                }, status=400)
            item.display_text = display_text
        
        if 'icon_emoji' in data:
            item.icon_emoji = data['icon_emoji'][:10]
        
        if 'visibility' in data:
            visibility = data['visibility']
            if visibility in dict(ProfileAboutItem.VISIBILITY_CHOICES):
                item.visibility = visibility
        
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'About item updated',
            'item': {
                'id': item.id,
                'display_text': item.display_text,
                'icon_emoji': item.icon_emoji,
                'visibility': item.visibility
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating About item: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to update About item'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def delete_about_item(request, item_id):
    """
    Delete (soft delete) About item.
    
    POST /api/profile/about/<item_id>/delete/
    
    Returns:
        {"success": true, "message": "Item deleted"}
    """
    try:
        profile = get_user_profile_safe(request.user)
        
        # Get item (ownership check)
        try:
            item = ProfileAboutItem.objects.get(
                id=item_id,
                user_profile=profile
            )
        except ProfileAboutItem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'About item not found'
            }, status=404)
        
        # Soft delete
        item.is_active = False
        item.save()
        
        return JsonResponse({
            'success': True,
            'message': 'About item deleted'
        })
        
    except Exception as e:
        logger.error(f"Error deleting About item: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to delete About item'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def reorder_about_items(request):
    """
    Reorder About items.
    
    POST /api/profile/about/reorder/
    
    Body:
        {
            "item_ids": [3, 1, 2]  // New order (item IDs)
        }
    
    Returns:
        {"success": true, "message": "Items reordered"}
    """
    try:
        profile = get_user_profile_safe(request.user)
        
        # Parse JSON body
        data = json.loads(request.body)
        item_ids = data.get('item_ids', [])
        
        if not isinstance(item_ids, list):
            return JsonResponse({
                'success': False,
                'error': 'item_ids must be an array'
            }, status=400)
        
        # Update order_index for each item
        with transaction.atomic():
            for index, item_id in enumerate(item_ids):
                try:
                    item = ProfileAboutItem.objects.get(
                        id=item_id,
                        user_profile=profile
                    )
                    item.order_index = index
                    item.save(update_fields=['order_index'])
                except ProfileAboutItem.DoesNotExist:
                    logger.warning(f"Item {item_id} not found for reorder")
                    continue
        
        return JsonResponse({
            'success': True,
            'message': 'About items reordered'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        logger.error(f"Error reordering About items: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to reorder items'
        }, status=500)
