"""
UP PHASE 8: Follow/Unfollow API Endpoints

Simplified follow/unfollow endpoints for hero section with instant UI updates.
Returns updated follower counts and privacy-aware data.

Endpoints:
- POST /api/profile/<username>/follow/
- POST /api/profile/<username>/unfollow/
"""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied
from django.contrib.auth import get_user_model
from django.db.models import Count
import logging

from apps.user_profile.services.follow_service import FollowService
from apps.user_profile.models_main import Follow, FollowRequest, UserProfile, PrivacySettings

User = get_user_model()
logger = logging.getLogger(__name__)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def follow_user_hero_api(request, username):
    """
    Follow a user from hero section (or create follow request if private).
    
    POST /api/profile/<username>/follow/
    
    Response:
        {
            "success": true,
            "action": "followed" | "request_sent",
            "is_following": true | false,
            "has_pending_request": true | false,
            "follower_count": 123,
            "following_count": 45,
            "show_follower_count": true,
            "show_following_count": true,
            "message": "You are now following @username"
        }
    
    Errors:
        400: Invalid request (self-follow)
        403: Cannot follow user (privacy settings)
        404: User not found
    """
    try:
        # Follow user (service handles privacy + private accounts)
        result = FollowService.follow_user(
            follower_user=request.user,
            followee_username=username,
            request_id=request.META.get('HTTP_X_REQUEST_ID'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        obj, created = result
        
        # Get target user for counts
        target_user = User.objects.get(username=username)
        target_profile = UserProfile.objects.get(user=target_user)
        
        # Check if it's a FollowRequest (private account) or Follow (public account)
        if isinstance(obj, FollowRequest):
            # Private account - follow request sent
            return JsonResponse({
                'success': True,
                'action': 'request_sent',
                'is_following': False,
                'has_pending_request': True,
                'message': f'Follow request sent to @{username}'
            })
        elif isinstance(obj, Follow):
            # Public account - followed immediately
            return JsonResponse({
                'success': True,
                'action': 'followed',
                'is_following': True,
                'has_pending_request': False,
                'message': f'You are now following @{username}'
            })
        else:
            # Shouldn't happen, but handle gracefully
            return JsonResponse({
                'success': True,
                'action': 'followed',
                'is_following': True,
                'message': f'You are now following @{username}'
            })
    
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    except PermissionDenied as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=403)
    
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    
    except Exception as e:
        logger.error(f"Error in follow_user_hero_api: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request'
        }, status=500)


@login_required
@csrf_protect
@require_http_methods(["POST"])
def unfollow_user_hero_api(request, username):
    """
    Unfollow a user from hero section.
    
    POST /api/profile/<username>/unfollow/
    
    Response:
        {
            "success": true,
            "is_following": false,
            "has_pending_request": false,
            "follower_count": 122,
            "following_count": 45,
            "show_follower_count": true,
            "show_following_count": true,
            "message": "You unfollowed @username"
        }
    
    Errors:
        404: User not found
    """
    try:
        # Unfollow user (service handles cleanup)
        unfollowed = FollowService.unfollow_user(
            follower_user=request.user,
            followee_username=username,
            request_id=request.META.get('HTTP_X_REQUEST_ID'),
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT')
        )
        
        # Get target user for counts
        target_user = User.objects.get(username=username)
        
        # Get privacy settings for count visibility
        try:
            target_profile = UserProfile.objects.get(user=target_user)
            privacy_settings = PrivacySettings.objects.get(user_profile=target_profile)
        except (UserProfile.DoesNotExist, PrivacySettings.DoesNotExist):
            # Default to public if no settings
            privacy_settings = None
        
        # Calculate counts
        follower_count = target_user.followers.count()
        following_count = target_user.following.count()
        
        # Determine if counts should be shown based on privacy
        is_owner = request.user == target_user
        show_follower_count = is_owner or (
            privacy_settings is None or privacy_settings.show_followers_count
        )
        show_following_count = is_owner or (
            privacy_settings is None or privacy_settings.show_following_count
        )
        
        return JsonResponse({
            'success': True,
            'is_following': False,
            'has_pending_request': False,
            'follower_count': follower_count if show_follower_count else 0,
            'following_count': following_count if show_following_count else 0,
            'show_follower_count': show_follower_count,
            'show_following_count': show_following_count,
            'message': f'You unfollowed @{username}' if unfollowed else f'You were not following @{username}'
        })
    
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'User not found'
        }, status=404)
    
    except Exception as e:
        logger.error(f"Error in unfollow_user_hero_api: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while processing your request'
        }, status=500)
