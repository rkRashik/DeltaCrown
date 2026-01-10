# apps/user_profile/api/settings_loadout_api.py
"""
Hardware Loadout Settings API (Phase 4B)
Simple endpoint for saving 4 brand fields: mouse, keyboard, headset, monitor
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
import json
import logging

from apps.user_profile.models import HardwareLoadout, UserProfile

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def loadout_settings_get(request):
    """
    GET /me/settings/loadout/ - Retrieve hardware loadout settings
    
    Returns:
        JSON: {
            "success": true,
            "data": {
                "mouse_brand": "Logitech G Pro X Superlight",
                "keyboard_brand": "Wooting 60HE",
                "headset_brand": "HyperX Cloud II",
                "monitor_brand": "BenQ Zowie XL2546K 240Hz"
            }
        }
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
        loadout, _ = HardwareLoadout.objects.get_or_create(user_profile=profile)
        
        return JsonResponse({
            'success': True,
            'data': {
                'mouse_brand': loadout.mouse_brand or '',
                'keyboard_brand': loadout.keyboard_brand or '',
                'headset_brand': loadout.headset_brand or '',
                'monitor_brand': loadout.monitor_brand or '',
            }
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching loadout settings for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def loadout_settings_save(request):
    """
    POST /me/settings/loadout/save/ - Save hardware loadout settings
    
    Body (JSON):
    {
        "mouse_brand": "Logitech G Pro X Superlight",
        "keyboard_brand": "Wooting 60HE",
        "headset_brand": "HyperX Cloud II",
        "monitor_brand": "BenQ Zowie XL2546K 240Hz"
    }
    
    Returns:
        JSON: {"success": true, "message": "Loadout saved successfully"}
    """
    try:
        data = json.loads(request.body)
        profile = UserProfile.objects.get(user=request.user)
        loadout, _ = HardwareLoadout.objects.get_or_create(user_profile=profile)
        
        # Update fields (allow empty strings)
        if 'mouse_brand' in data:
            loadout.mouse_brand = (data['mouse_brand'] or '').strip()[:100]
        if 'keyboard_brand' in data:
            loadout.keyboard_brand = (data['keyboard_brand'] or '').strip()[:100]
        if 'headset_brand' in data:
            loadout.headset_brand = (data['headset_brand'] or '').strip()[:100]
        if 'monitor_brand' in data:
            loadout.monitor_brand = (data['monitor_brand'] or '').strip()[:100]
        
        loadout.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Loadout saved successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload'}, status=400)
    except UserProfile.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'User profile not found'}, status=404)
    except Exception as e:
        logger.error(f"Error saving loadout settings for user {request.user.id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
