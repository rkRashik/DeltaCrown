"""
API decorators for notifications app.
Ensures JSON-only responses for API endpoints.
"""
from functools import wraps
from django.http import JsonResponse


def require_auth_json(view_func):
    """
    Decorator that requires authentication and returns JSON 401 if not authenticated.
    
    Unlike @login_required which returns HTML redirect (302), this returns:
    {"success": false, "error": "auth_required"} with 401 status.
    
    Usage:
        @require_auth_json
        def my_api_view(request):
            # User is guaranteed to be authenticated here
            pass
    """
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"success": False, "error": "auth_required"},
                status=401
            )
        return view_func(request, *args, **kwargs)
    return wrapped
