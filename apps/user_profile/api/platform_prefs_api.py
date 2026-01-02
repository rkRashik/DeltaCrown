"""
Platform Preferences API (Phase 5A)

CSRF-protected JSON endpoints for platform-wide preferences.

Endpoints:
- GET /me/settings/platform-global/ - Get current preferences + available options
- POST /me/settings/platform-global/save/ - Update preferences

NO HARDCODED VALUES: All dropdown choices come from backend.
"""

import json
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from apps.user_profile.services.platform_prefs_service import (
    get_user_platform_prefs,
    set_user_platform_prefs,
    get_available_options,
)
from apps.user_profile.utils import get_user_profile_safe

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def get_platform_global_settings(request):
    """
    GET /me/settings/platform-global/
    
    Returns current preferences + available options for dropdowns.
    
    Response:
        {
            "success": true,
            "preferences": {
                "preferred_language": "en",
                "timezone": "Asia/Dhaka",
                "time_format": "12h",
                "currency": "BDT"
            },
            "available_options": {
                "languages": [["en", "English"], ["bn", "Bengali"]],
                "timezones": ["Asia/Dhaka", "UTC", ...],
                "time_formats": [["12h", "12-hour (3:00 PM)"], ...],
                "currencies": [["BDT", "BDT (৳)"], ["USD", "USD ($)"]]
            }
        }
    """
    try:
        profile = get_user_profile_safe(request.user)
        
        # Get current preferences
        prefs = get_user_platform_prefs(profile)
        
        # Get available options
        options = get_available_options()
        
        return JsonResponse({
            'success': True,
            'preferences': prefs,
            'available_options': options,
        })
    
    except Exception as e:
        logger.error(f"Error loading platform settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def save_platform_global_settings(request):
    """
    POST /me/settings/platform-global/save/
    
    Update platform preferences.
    
    Body (JSON):
        {
            "preferred_language": "en",
            "timezone": "Asia/Dhaka",
            "time_format": "12h",
            "currency": "BDT"
        }
    
    Response:
        {
            "success": true,
            "message": "Platform preferences updated successfully",
            "preferences": {...}  // Updated preferences
        }
    """
    try:
        profile = get_user_profile_safe(request.user)
        
        data = json.loads(request.body)
        
        # Update preferences (validates and saves)
        updated_prefs = set_user_platform_prefs(profile, data)
        
        return JsonResponse({
            'success': True,
            'message': 'Platform preferences updated successfully',
            'preferences': updated_prefs,
        })
    
    except ValueError as e:
        # Validation error
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error saving platform settings: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'Server error'}, status=500)
