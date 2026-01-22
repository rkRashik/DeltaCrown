"""
Follow Status API - Returns current follow relationship state

POST /api/profile/<username>/follow/status/

Returns the current follow state between viewer and target user.
Used for follow button state persistence.

Response:
{
    "success": true,
    "state": "none" | "requested" | "following" | "self",
    "is_private_account": bool,
    "can_follow": bool
}

States:
- "self": Viewer is viewing their own profile
- "following": Viewer is following target
- "requested": Viewer has pending follow request (private account)
- "none": No relationship

Auth: Returns JSON 401 if not authenticated (not redirect)
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

from apps.user_profile.services.follow_service import FollowService
from apps.user_profile.models_main import PrivacySettings, UserProfile, FollowRequest

User = get_user_model()


@require_http_methods(["GET"])
def get_follow_status_api(request, username):
    """
    Get follow relationship status for button state.
    
    GET /api/profile/<username>/follow/status/
    
    Returns:
        JSON with state: none|requested|following|self
    """
    # Check authentication
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': 'Authentication required',
            'state': 'none',
            'can_follow': False
        }, status=401)
    
    try:
        target_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    # Self-view
    if request.user == target_user:
        return JsonResponse({
            'success': True,
            'state': 'self',
            'can_follow': False,
            'is_private_account': False
        })
    
    # Check if target has private account
    try:
        privacy_settings = PrivacySettings.objects.get(user_profile=target_user.profile)
        is_private = privacy_settings.is_private_account
    except (PrivacySettings.DoesNotExist, AttributeError):
        is_private = False
    
    # Check current relationship
    is_following = FollowService.is_following(
        follower_user=request.user,
        followee_user=target_user
    )
    
    if is_following:
        return JsonResponse({
            'success': True,
            'state': 'following',
            'can_follow': False,
            'is_private_account': is_private
        })
    
    # Check for pending follow request
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        target_profile = UserProfile.objects.get(user=target_user)
        has_pending = FollowRequest.objects.filter(
            requester=user_profile,
            target=target_profile,
            status=FollowRequest.STATUS_PENDING
        ).exists()
        
        if has_pending:
            return JsonResponse({
                'success': True,
                'state': 'requested',
                'can_follow': False,
                'is_private_account': is_private
            })
    except (UserProfile.DoesNotExist, AttributeError):
        pass
    
    # No relationship - can follow
    return JsonResponse({
        'success': True,
        'state': 'none',
        'can_follow': True,
        'is_private_account': is_private
    })
