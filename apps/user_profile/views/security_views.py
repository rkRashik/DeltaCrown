"""
Security & KYC views for DeltaCrown.
Phase 4C.3: Production-ready security settings.

Endpoints:
- Change Password
- DOB Management (with KYC lock)
- KYC Status API
- Session Management
"""

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.sessions.models import Session
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def check_rate_limit(user_id, action, max_attempts=5, window_seconds=600):
    """
    Simple rate limiting using Django cache.
    
    Args:
        user_id: User ID
        action: Action name (e.g., 'change_password')
        max_attempts: Maximum attempts allowed
        window_seconds: Time window in seconds (default: 10 minutes)
    
    Returns:
        tuple: (is_allowed: bool, attempts_left: int, retry_after: int)
    """
    cache_key = f"rate_limit:{action}:{user_id}"
    attempts = cache.get(cache_key, 0)
    
    if attempts >= max_attempts:
        # Get TTL for retry_after
        ttl = cache.ttl(cache_key) if hasattr(cache, 'ttl') else window_seconds
        return False, 0, ttl if ttl > 0 else window_seconds
    
    # Increment attempts
    cache.set(cache_key, attempts + 1, timeout=window_seconds)
    return True, max_attempts - attempts - 1, 0


@login_required
@require_http_methods(["POST"])
def change_password(request):
    """
    Change user password with current password verification.
    Rate limited to 5 attempts per 10 minutes.
    
    POST /me/settings/security/change-password/
    
    Payload:
        - current_password (required)
        - new_password (required)
        - confirm_password (required)
    
    Returns:
        - 200: {success: true, message: "Password changed successfully"}
        - 400: {success: false, error: "..."} (validation errors)
        - 429: {success: false, error: "Too many attempts", retry_after: seconds}
    """
    try:
        # Rate limiting: 5 attempts per 10 minutes
        is_allowed, attempts_left, retry_after = check_rate_limit(
            request.user.id, 
            'change_password', 
            max_attempts=5, 
            window_seconds=600
        )
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for password change: user {request.user.username}")
            return JsonResponse({
                'success': False,
                'error': f'Too many password change attempts. Please try again in {retry_after // 60} minutes.',
                'retry_after': retry_after
            }, status=429)
        
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        # Validation
        if not current_password:
            return JsonResponse({
                'success': False,
                'error': 'Current password is required'
            }, status=400)
        
        if not new_password:
            return JsonResponse({
                'success': False,
                'error': 'New password is required'
            }, status=400)
        
        if new_password != confirm_password:
            return JsonResponse({
                'success': False,
                'error': 'New passwords do not match'
            }, status=400)
        
        # Check current password
        if not request.user.check_password(current_password):
            return JsonResponse({
                'success': False,
                'error': 'Current password is incorrect'
            }, status=400)
        
        # Check if new password is same as current
        if current_password == new_password:
            return JsonResponse({
                'success': False,
                'error': 'New password must be different from current password'
            }, status=400)
        
        # Validate new password strength (Django built-in validators)
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        try:
            validate_password(new_password, user=request.user)
        except ValidationError as e:
            return JsonResponse({
                'success': False,
                'error': '; '.join(e.messages)
            }, status=400)
        
        # Set new password
        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        
        # CRITICAL: Keep user logged in after password change
        update_session_auth_hash(request, request.user)
        
        logger.info(f"Password changed successfully for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Password changed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error changing password for user {request.user.username}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error. Please try again later.'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def save_dob(request):
    """
    Save or update date of birth.
    Respects KYC lock: read-only if user is KYC verified.
    
    POST /me/settings/security/dob/
    
    Payload:
        - date_of_birth (YYYY-MM-DD format)
    
    Returns:
        - 200: {success: true, message: "Date of birth saved"}
        - 400: {success: false, error: "..."}
    """
    try:
        profile = request.user.profile
        
        # Check KYC lock
        if profile.is_kyc_verified:
            return JsonResponse({
                'success': False,
                'error': 'Date of birth is locked after KYC verification'
            }, status=400)
        
        dob_str = request.POST.get('date_of_birth', '').strip()
        
        if not dob_str:
            return JsonResponse({
                'success': False,
                'error': 'Date of birth is required'
            }, status=400)
        
        # Parse date
        try:
            from django.utils.dateparse import parse_date
            dob = parse_date(dob_str)
            if not dob:
                raise ValueError("Invalid date format")
        except Exception:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date format. Use YYYY-MM-DD (e.g., 1995-03-15)'
            }, status=400)
        
        # Validate date is in the past
        if dob >= timezone.now().date():
            return JsonResponse({
                'success': False,
                'error': 'Date of birth must be in the past'
            }, status=400)
        
        # Validate minimum age (13 years old for most platforms)
        from datetime import date
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        if age < 13:
            return JsonResponse({
                'success': False,
                'error': 'You must be at least 13 years old to use this platform'
            }, status=400)
        
        if age > 120:
            return JsonResponse({
                'success': False,
                'error': 'Invalid date of birth'
            }, status=400)
        
        # Save DOB
        profile.date_of_birth = dob
        profile.save(update_fields=['date_of_birth', 'updated_at'])
        
        logger.info(f"DOB saved for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': 'Date of birth saved successfully',
            'age': age
        })
        
    except Exception as e:
        logger.error(f"Error saving DOB for user {request.user.username}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error. Please try again later.'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def kyc_status_api(request):
    """
    Get current KYC verification status.
    
    GET /me/settings/security/kyc/status/
    
    Returns:
        - 200: {
            status: "unverified|pending|verified|rejected",
            can_submit: boolean,
            submitted_at: ISO timestamp or null,
            reviewed_at: ISO timestamp or null,
            rejection_reason: string or null
        }
    """
    try:
        from apps.user_profile.models import KYCSubmission
        
        profile = request.user.profile
        
        # Get the latest submission
        latest_submission = profile.kyc_submissions.first()
        
        if latest_submission:
            return JsonResponse({
                'success': True,
                'status': profile.kyc_status,
                'can_submit': profile.kyc_status in ['unverified', 'rejected'],
                'submitted_at': latest_submission.submitted_at.isoformat(),
                'reviewed_at': latest_submission.reviewed_at.isoformat() if latest_submission.reviewed_at else None,
                'rejection_reason': latest_submission.rejection_reason or None,
                'has_documents': bool(latest_submission.document_front),
                'document_type': latest_submission.get_document_type_display(),
            })
        else:
            return JsonResponse({
                'success': True,
                'status': 'unverified',
                'can_submit': True,
                'submitted_at': None,
                'reviewed_at': None,
                'rejection_reason': None,
                'has_documents': False,
            })
        
    except Exception as e:
        logger.error(f"Error fetching KYC status for user {request.user.username}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def logout_other_sessions(request):
    """
    Logout all other sessions except the current one.
    
    POST /me/settings/security/sessions/logout-others/
    
    Returns:
        - 200: {success: true, message: "...", sessions_deleted: N}
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        current_session_key = request.session.session_key
        user_id = request.user.id
        
        # Find all active sessions for this user
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        
        deleted_count = 0
        for session in active_sessions:
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user_id):
                if session.session_key != current_session_key:
                    session.delete()
                    deleted_count += 1
        
        logger.info(f"Logged out {deleted_count} other sessions for user {request.user.username}")
        
        return JsonResponse({
            'success': True,
            'message': f'Logged out {deleted_count} other session{"s" if deleted_count != 1 else ""}',
            'sessions_deleted': deleted_count
        })
        
    except Exception as e:
        logger.error(f"Error logging out other sessions for user {request.user.username}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)


@login_required
@require_http_methods(["GET"])
def session_info(request):
    """
    Get information about current user's sessions.
    
    GET /me/settings/security/sessions/info/
    
    Returns:
        - 200: {
            current_session: {...},
            total_active_sessions: N,
            last_login: ISO timestamp
        }
    """
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        current_session_key = request.session.session_key
        user_id = request.user.id
        
        # Count active sessions
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        
        user_session_count = 0
        for session in active_sessions:
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(user_id):
                user_session_count += 1
        
        return JsonResponse({
            'success': True,
            'current_session_key': current_session_key,
            'total_active_sessions': user_session_count,
            'last_login': request.user.last_login.isoformat() if request.user.last_login else None,
            'date_joined': request.user.date_joined.isoformat(),
        })
        
    except Exception as e:
        logger.error(f"Error fetching session info for user {request.user.username}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)
