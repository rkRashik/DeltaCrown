# apps/accounts/deletion_api.py
"""
API endpoints for account deletion scheduling, cancellation, and status.
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.core.exceptions import ValidationError

from .deletion_services import (
    schedule_account_deletion,
    cancel_account_deletion,
    get_deletion_status,
    REQUIRED_CONFIRMATION_PHRASE,
    DELETION_COOLDOWN_DAYS
)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def schedule_deletion_view(request):
    """
    POST /me/settings/account-deletion/schedule/
    
    Schedule account deletion with 14-day cooling-off period.
    
    Request body:
    {
        "password": "user_password",  // Optional if OAuth-only user
        "reason": "optional reason",
        "confirm_phrase": "DELETE MY ACCOUNT"  // Required exact match
    }
    
    Response:
    {
        "success": true,
        "message": "Account deletion scheduled...",
        "scheduled_for": "2026-01-16T12:00:00Z",
        "days_remaining": 14
    }
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON'
        }, status=400)
    
    password = data.get('password', '')
    reason = data.get('reason', '')
    confirmation_phrase = data.get('confirm_phrase', '')
    
    # Validate confirmation phrase
    if not confirmation_phrase:
        return JsonResponse({
            'success': False,
            'error': 'Confirmation phrase is required',
            'required_phrase': REQUIRED_CONFIRMATION_PHRASE
        }, status=400)
    
    # Get request metadata
    request_meta = {
        'ip': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT', '')
    }
    
    try:
        result = schedule_account_deletion(
            user=request.user,
            password=password,
            reason=reason,
            confirmation_phrase=confirmation_phrase,
            request_meta=request_meta
        )
        
        if not result['success']:
            return JsonResponse(result, status=400)
        
        return JsonResponse({
            'success': True,
            'message': result['message'],
            'scheduled_for': result['scheduled_for'].isoformat(),
            'days_remaining': result['days_remaining']
        })
    
    except ValidationError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while scheduling deletion'
        }, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def cancel_deletion_view(request):
    """
    POST /me/settings/account-deletion/cancel/
    
    Cancel scheduled account deletion and restore access.
    
    Response:
    {
        "success": true,
        "message": "Account deletion has been canceled..."
    }
    """
    try:
        result = cancel_account_deletion(request.user)
        
        if not result['success']:
            return JsonResponse(result, status=400)
        
        return JsonResponse(result)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while canceling deletion'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def deletion_status_view(request):
    """
    GET /me/settings/account-deletion/status/
    
    Get current deletion status for authenticated user.
    
    Response (if scheduled):
    {
        "success": true,
        "data": {
            "status": "SCHEDULED",
            "requested_at": "2026-01-02T12:00:00Z",
            "scheduled_for": "2026-01-16T12:00:00Z",
            "days_remaining": 14,
            "can_cancel": true,
            "reason": "optional reason"
        }
    }
    
    Response (if not scheduled):
    {
        "success": true,
        "data": null
    }
    """
    try:
        status = get_deletion_status(request.user)
        
        return JsonResponse({
            'success': True,
            'data': status,
            'required_phrase': REQUIRED_CONFIRMATION_PHRASE,
            'cooldown_days': DELETION_COOLDOWN_DAYS
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while fetching deletion status'
        }, status=500)
