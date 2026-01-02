# apps/accounts/deletion_services.py
"""
Account deletion services with 14-day cooling-off period.
Handles scheduling, cancellation, and finalization of account deletions.
"""
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model, logout
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import AccountDeletionRequest

User = get_user_model()

# Cooling-off period (14 days)
DELETION_COOLDOWN_DAYS = 14

# Required confirmation phrase
REQUIRED_CONFIRMATION_PHRASE = "DELETE MY ACCOUNT"


def schedule_account_deletion(user, password=None, reason='', confirmation_phrase='', 
                              request_meta=None):
    """
    Schedule user account for deletion after cooling-off period.
    
    Args:
        user: User instance
        password: Password for verification (required for password users)
        reason: Optional reason for deletion
        confirmation_phrase: Must match REQUIRED_CONFIRMATION_PHRASE
        request_meta: Dict with 'ip' and 'user_agent' (optional)
    
    Returns:
        dict: {success: bool, message: str, deletion_request: AccountDeletionRequest}
    
    Raises:
        ValidationError: If validation fails
    """
    # Check if already scheduled
    if hasattr(user, 'deletion_request') and user.deletion_request.status == AccountDeletionRequest.Status.SCHEDULED:
        return {
            'success': False,
            'message': 'Account deletion is already scheduled',
            'deletion_request': user.deletion_request
        }
    
    # Validate confirmation phrase
    if confirmation_phrase.strip() != REQUIRED_CONFIRMATION_PHRASE:
        raise ValidationError(
            f'Confirmation phrase must be exactly: "{REQUIRED_CONFIRMATION_PHRASE}"'
        )
    
    # Verify password for password users
    if user.has_usable_password():
        if not password:
            raise ValidationError('Password is required for password-authenticated accounts')
        if not user.check_password(password):
            raise ValidationError('Incorrect password')
    else:
        # OAuth-only user - confirmation phrase is sufficient
        pass
    
    # Calculate scheduled_for
    scheduled_for = timezone.now() + timedelta(days=DELETION_COOLDOWN_DAYS)
    
    # Create or update deletion request
    with transaction.atomic():
        deletion_request, created = AccountDeletionRequest.objects.update_or_create(
            user=user,
            defaults={
                'status': AccountDeletionRequest.Status.SCHEDULED,
                'scheduled_for': scheduled_for,
                'reason': reason,
                'confirmation_phrase': confirmation_phrase,
                'last_ip': request_meta.get('ip') if request_meta else None,
                'last_user_agent': request_meta.get('user_agent', '')[:500] if request_meta else '',
                'canceled_at': None,
                'completed_at': None,
            }
        )
        
        # Clear all user sessions (log out from all devices)
        Session.objects.filter(
            expire_date__gte=timezone.now()
        ).filter(
            session_data__contains=f'"_auth_user_id":"{user.id}"'
        ).delete()
    
    return {
        'success': True,
        'message': f'Account deletion scheduled for {scheduled_for.strftime("%Y-%m-%d")}. You will be logged out immediately.',
        'deletion_request': deletion_request,
        'scheduled_for': scheduled_for,
        'days_remaining': DELETION_COOLDOWN_DAYS
    }


def cancel_account_deletion(user):
    """
    Cancel scheduled account deletion and restore access.
    
    Args:
        user: User instance
    
    Returns:
        dict: {success: bool, message: str}
    """
    try:
        deletion_request = user.deletion_request
    except AccountDeletionRequest.DoesNotExist:
        return {
            'success': False,
            'message': 'No deletion request found'
        }
    
    # Check if cancellable
    if not deletion_request.is_cancellable():
        if deletion_request.status == AccountDeletionRequest.Status.COMPLETED:
            return {
                'success': False,
                'message': 'Account deletion has already been completed'
            }
        elif deletion_request.status == AccountDeletionRequest.Status.CANCELED:
            return {
                'success': False,
                'message': 'Deletion request was already canceled'
            }
        else:
            return {
                'success': False,
                'message': 'Deletion deadline has passed. Cannot cancel.'
            }
    
    # Cancel the deletion
    deletion_request.status = AccountDeletionRequest.Status.CANCELED
    deletion_request.canceled_at = timezone.now()
    deletion_request.save(update_fields=['status', 'canceled_at'])
    
    return {
        'success': True,
        'message': 'Account deletion has been canceled. You can log in again.'
    }


def get_deletion_status(user):
    """
    Get current deletion status for user.
    
    Args:
        user: User instance
    
    Returns:
        dict: Status information or None if no deletion scheduled
    """
    try:
        deletion_request = user.deletion_request
    except AccountDeletionRequest.DoesNotExist:
        return None
    
    return {
        'status': deletion_request.status,
        'requested_at': deletion_request.requested_at.isoformat(),
        'scheduled_for': deletion_request.scheduled_for.isoformat(),
        'days_remaining': deletion_request.days_remaining(),
        'can_cancel': deletion_request.is_cancellable(),
        'reason': deletion_request.reason,
    }


def finalize_account_deletion(user):
    """
    Finalize account deletion (soft-delete + anonymize).
    
    This performs:
    1. Deactivate account (is_active=False)
    2. Anonymize PII (email, name, username)
    3. Clear sessions
    4. Mark deletion request as COMPLETED
    
    Args:
        user: User instance with deletion_request
    
    Returns:
        dict: {success: bool, message: str}
    """
    try:
        deletion_request = user.deletion_request
    except AccountDeletionRequest.DoesNotExist:
        return {
            'success': False,
            'message': 'No deletion request found'
        }
    
    if deletion_request.status != AccountDeletionRequest.Status.SCHEDULED:
        return {
            'success': False,
            'message': f'Deletion request is not scheduled (status: {deletion_request.status})'
        }
    
    if timezone.now() < deletion_request.scheduled_for:
        return {
            'success': False,
            'message': 'Scheduled deletion time has not yet arrived'
        }
    
    with transaction.atomic():
        # Soft-delete: deactivate account
        user.is_active = False
        
        # Anonymize PII
        anon_id = f"deleted_{user.id}_{timezone.now().strftime('%Y%m%d')}"
        user.username = anon_id
        user.email = f"{anon_id}@deleted.local"
        user.first_name = ''
        user.last_name = ''
        
        user.save(update_fields=['is_active', 'username', 'email', 'first_name', 'last_name'])
        
        # Clear all sessions
        Session.objects.filter(
            expire_date__gte=timezone.now()
        ).filter(
            session_data__contains=f'"_auth_user_id":"{user.id}"'
        ).delete()
        
        # Mark deletion as completed
        deletion_request.status = AccountDeletionRequest.Status.COMPLETED
        deletion_request.completed_at = timezone.now()
        deletion_request.save(update_fields=['status', 'completed_at'])
    
    return {
        'success': True,
        'message': f'Account {user.id} has been deactivated and anonymized'
    }


def process_pending_deletions():
    """
    Process all pending account deletions that have reached their scheduled_for date.
    
    This function should be called by a management command or cron job.
    
    Returns:
        dict: {processed: int, failed: int, results: list}
    """
    # Find all scheduled deletions that are due
    due_deletions = AccountDeletionRequest.objects.filter(
        status=AccountDeletionRequest.Status.SCHEDULED,
        scheduled_for__lte=timezone.now()
    ).select_related('user')
    
    results = []
    processed = 0
    failed = 0
    
    for deletion_request in due_deletions:
        try:
            result = finalize_account_deletion(deletion_request.user)
            if result['success']:
                processed += 1
                results.append({
                    'user_id': deletion_request.user.id,
                    'status': 'success',
                    'message': result['message']
                })
            else:
                failed += 1
                results.append({
                    'user_id': deletion_request.user.id,
                    'status': 'failed',
                    'message': result['message']
                })
        except Exception as e:
            failed += 1
            results.append({
                'user_id': deletion_request.user.id,
                'status': 'error',
                'message': str(e)
            })
    
    return {
        'processed': processed,
        'failed': failed,
        'total': len(due_deletions),
        'results': results
    }
