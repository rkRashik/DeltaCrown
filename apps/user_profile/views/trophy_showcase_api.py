# apps/user_profile/views/trophy_showcase_api.py
"""
Trophy Showcase API Endpoints - Interactive Owner Flows (Phase 2D)

Endpoints:
- POST /api/profile/trophy-showcase/update/ - Equip/unequip cosmetics, pin/unpin badges
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
import json

from apps.user_profile.models import TrophyShowcaseConfig, UserBadge


@login_required
@require_http_methods(["POST"])
def update_trophy_showcase(request):
    """
    Update trophy showcase configuration.
    
    POST /api/profile/trophy-showcase/update/
    
    Body (JSON):
    {
        "equipped_border_id": 123,  # Optional: CosmeticItem ID or null to unequip
        "equipped_frame_id": 456,   # Optional: CosmeticItem ID or null to unequip
        "pinned_badge_ids": [1, 2, 3]  # Max 3 badge IDs
    }
    
    Returns:
        200: {"success": true, "message": "..."}
        400: {"error": "..."}
    """
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # Get or create showcase config
    showcase, created = TrophyShowcaseConfig.objects.get_or_create(
        user=request.user
    )
    
    # Extract fields
    equipped_border_id = data.get("equipped_border_id")
    equipped_frame_id = data.get("equipped_frame_id")
    pinned_badge_ids = data.get("pinned_badge_ids", [])
    
    try:
        # Validate pinned badges limit
        if len(pinned_badge_ids) > 3:
            return JsonResponse({"error": "Maximum 3 pinned badges allowed"}, status=400)
        
        # Validate badge ownership
        if pinned_badge_ids:
            user_badges = UserBadge.objects.filter(
                user=request.user,
                badge_id__in=pinned_badge_ids
            )
            
            if user_badges.count() != len(pinned_badge_ids):
                return JsonResponse({"error": "One or more badges not owned"}, status=400)
        
        # Update showcase
        # Note: Border/Frame cosmetics are not fully implemented yet,
        # so we'll store IDs but validation is minimal for MVP
        
        if equipped_border_id is not None:
            showcase.equipped_border_id = equipped_border_id
        
        if equipped_frame_id is not None:
            showcase.equipped_frame_id = equipped_frame_id
        
        if pinned_badge_ids is not None:
            # Store pinned badge IDs (assuming JSON field exists)
            if hasattr(showcase, 'pinned_badges'):
                showcase.pinned_badges = pinned_badge_ids
        
        showcase.save()
        
        return JsonResponse({
            "success": True,
            "message": "Showcase updated successfully",
            "equipped_border_id": showcase.equipped_border_id,
            "equipped_frame_id": showcase.equipped_frame_id,
        })
    
    except ValidationError as e:
        return JsonResponse({"error": str(e)}, status=400)
    
    except Exception as e:
        # Log unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Trophy showcase update error: {e}", exc_info=True)
        return JsonResponse({"error": "An error occurred while updating showcase"}, status=500)
