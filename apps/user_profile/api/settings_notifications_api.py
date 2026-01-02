"""
Notification Settings API (UP-PHASE2B)

CSRF-protected JSON endpoints for notification preferences.
"""
import json
import logging
from datetime import time

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError

from apps.user_profile.models import UserProfile, NotificationPreferences

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["GET"])
def notifications_settings_get(request):
    """
    GET /me/settings/notifications/
    
    Fetch user notification preferences. Creates defaults if missing.
    
    Returns:
        JSON with success flag and notification preferences data
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
        prefs, created = NotificationPreferences.objects.get_or_create(user_profile=profile)
        
        data = {
            # Channels
            'email_enabled': prefs.email_enabled,
            'push_enabled': prefs.push_enabled,
            'sms_enabled': prefs.sms_enabled,
            
            # Categories
            'notif_tournaments': prefs.notif_tournaments,
            'notif_teams': prefs.notif_teams,
            'notif_bounties': prefs.notif_bounties,
            'notif_messages': prefs.notif_messages,
            'notif_system': prefs.notif_system,
            
            # Quiet hours
            'quiet_hours_enabled': prefs.quiet_hours_enabled,
            'quiet_hours_start': prefs.quiet_hours_start.strftime('%H:%M') if prefs.quiet_hours_start else None,
            'quiet_hours_end': prefs.quiet_hours_end.strftime('%H:%M') if prefs.quiet_hours_end else None,
            
            # Metadata
            'updated_at': prefs.updated_at.isoformat(),
        }
        
        return JsonResponse({
            'success': True,
            'data': data,
            'created': created,
        })
        
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Notification settings GET error for user {request.user.id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load notification settings'
        }, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def notifications_settings_save(request):
    """
    POST /me/settings/notifications/save/
    
    Save user notification preferences with validation.
    
    Payload:
        {
            "email_enabled": true,
            "push_enabled": true,
            "sms_enabled": false,
            "notif_tournaments": true,
            "notif_teams": true,
            "notif_bounties": true,
            "notif_messages": true,
            "notif_system": true,
            "quiet_hours_enabled": false,
            "quiet_hours_start": "22:00",
            "quiet_hours_end": "08:00"
        }
    
    Returns:
        JSON with success flag and message
    """
    try:
        data = json.loads(request.body)
        profile = UserProfile.objects.get(user=request.user)
        prefs, created = NotificationPreferences.objects.get_or_create(user_profile=profile)
        
        # Update channel toggles
        prefs.email_enabled = data.get('email_enabled', prefs.email_enabled)
        prefs.push_enabled = data.get('push_enabled', prefs.push_enabled)
        prefs.sms_enabled = data.get('sms_enabled', prefs.sms_enabled)
        
        # Update category toggles
        prefs.notif_tournaments = data.get('notif_tournaments', prefs.notif_tournaments)
        prefs.notif_teams = data.get('notif_teams', prefs.notif_teams)
        prefs.notif_bounties = data.get('notif_bounties', prefs.notif_bounties)
        prefs.notif_messages = data.get('notif_messages', prefs.notif_messages)
        prefs.notif_system = data.get('notif_system', prefs.notif_system)
        
        # Update quiet hours
        prefs.quiet_hours_enabled = data.get('quiet_hours_enabled', prefs.quiet_hours_enabled)
        
        # Parse time strings (format: "HH:MM")
        if 'quiet_hours_start' in data and data['quiet_hours_start']:
            try:
                hour, minute = map(int, data['quiet_hours_start'].split(':'))
                prefs.quiet_hours_start = time(hour=hour, minute=minute)
            except (ValueError, AttributeError):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid quiet_hours_start format. Use HH:MM (e.g., 22:00)'
                }, status=400)
        elif not prefs.quiet_hours_enabled:
            prefs.quiet_hours_start = None
        
        if 'quiet_hours_end' in data and data['quiet_hours_end']:
            try:
                hour, minute = map(int, data['quiet_hours_end'].split(':'))
                prefs.quiet_hours_end = time(hour=hour, minute=minute)
            except (ValueError, AttributeError):
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid quiet_hours_end format. Use HH:MM (e.g., 08:00)'
                }, status=400)
        elif not prefs.quiet_hours_enabled:
            prefs.quiet_hours_end = None
        
        # Validate via model clean()
        prefs.full_clean()
        prefs.save()
        
        logger.info(f"Notification settings saved for user {request.user.id}")
        
        return JsonResponse({
            'success': True,
            'message': 'Notification settings saved successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON payload'
        }, status=400)
    except UserProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User profile not found'
        }, status=404)
    except ValidationError as e:
        error_msg = '; '.join([f"{k}: {', '.join(v)}" for k, v in e.message_dict.items()])
        return JsonResponse({
            'success': False,
            'error': error_msg
        }, status=400)
    except Exception as e:
        logger.error(f"Notification settings save error for user {request.user.id}: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to save notification settings'
        }, status=500)
