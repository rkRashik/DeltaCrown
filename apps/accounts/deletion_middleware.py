# apps/accounts/deletion_middleware.py
"""
Middleware to block access for users with scheduled account deletion.
"""
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout

from .models import AccountDeletionRequest


class BlockScheduledDeletionMiddleware:
    """
    Block authenticated users who have scheduled account deletion.
    
    Behavior:
    - If user is authenticated and has SCHEDULED deletion:
      - Log them out
      - Return 403 for API requests
      - Redirect to login for web requests with message
    - Allow access to cancellation endpoint
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Check for scheduled deletion
        try:
            deletion_request = request.user.deletion_request
            if deletion_request.status == AccountDeletionRequest.Status.SCHEDULED:
                # Allow access to cancellation endpoint
                if request.path == reverse('accounts:cancel_deletion'):
                    return self.get_response(request)
                
                # Allow access to deletion status endpoint
                if request.path == reverse('accounts:deletion_status'):
                    return self.get_response(request)
                
                # Allow access to settings page (deletion-only mode)
                if '/me/settings/' in request.path:
                    return self.get_response(request)
                
                # Allow logout
                if request.path == reverse('accounts:logout') or request.path == '/accounts/logout/':
                    return self.get_response(request)
                
                # Log out the user
                logout(request)
                
                # Return appropriate response
                if request.path.startswith('/api/') or request.headers.get('Accept') == 'application/json':
                    return JsonResponse({
                        'success': False,
                        'error': 'Account scheduled for deletion',
                        'message': 'Your account is scheduled for deletion. Login is blocked.',
                        'scheduled_for': deletion_request.scheduled_for.isoformat(),
                        'days_remaining': deletion_request.days_remaining(),
                    }, status=403)
                else:
                    # Redirect to login with message
                    return redirect(f"{reverse('accounts:login')}?next={request.path}&deletion_scheduled=1")
        
        except AccountDeletionRequest.DoesNotExist:
            pass
        
        return self.get_response(request)
