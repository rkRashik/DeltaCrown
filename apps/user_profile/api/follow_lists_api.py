"""
UP PHASE 8: Instagram-like Followers/Following Lists API
Provides JSON endpoints for followers and following lists with privacy controls.

TWO-LAYER PRIVACY ENFORCEMENT:
1. Account Privacy (is_private_account): Controls who can see lists based on Follow relationship
2. List Visibility (followers_list_visibility): Further restricts visibility
"""

import logging
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.contrib.auth import get_user_model

from apps.user_profile.models import Follow, PrivacySettings, UserProfile

User = get_user_model()
logger = logging.getLogger(__name__)


def can_view_follow_list(viewer_user, target_user, target_profile, privacy_settings, list_type='followers'):
    """
    Instagram-like two-layer privacy enforcement for followers/following lists.
    
    Args:
        viewer_user: User or None (anonymous)
        target_user: User whose list is being viewed
        target_profile: UserProfile of target
        privacy_settings: PrivacySettings of target
        list_type: 'followers' or 'following'
    
    Returns:
        tuple: (can_view: bool, error_message: str|None, status_code: int|None)
    
    Privacy Logic:
    1. Owner always can view
    2. LAYER 1: Account Privacy (is_private_account)
       - If private account AND viewer is not approved follower → BLOCK
    3. LAYER 2: List Visibility Settings
       - only_me: Only owner can view
       - followers: Only approved followers can view
       - everyone: Anyone can view (if account not private OR viewer is follower)
    """
    # Owner always can view
    if viewer_user and viewer_user == target_user:
        return (True, None, None)
    
    # Get visibility setting
    if list_type == 'followers':
        visibility = privacy_settings.followers_list_visibility if privacy_settings else 'everyone'
    else:
        visibility = privacy_settings.following_list_visibility if privacy_settings else 'everyone'
    
    # Check if viewer is following target (for private account check)
    is_approved_follower = False
    if viewer_user:
        is_approved_follower = Follow.objects.filter(
            follower=viewer_user,
            following=target_user
        ).exists()
    
    # LAYER 1: Private Account Enforcement
    if privacy_settings and privacy_settings.is_private_account:
        if not is_approved_follower:
            # Private account + not following = cannot see lists
            if not viewer_user:
                return (False, 'This account is private. Follow to see their profile.', 401)
            else:
                return (False, 'This account is private. Follow to see their profile.', 403)
    
    # LAYER 2: List Visibility Settings
    if visibility == 'only_me':
        # Only owner can view
        if not viewer_user:
            return (False, f'This {list_type} list is private.', 401)
        else:
            return (False, f'This {list_type} list is private.', 403)
    
    elif visibility == 'followers':
        # Only followers can view
        if not viewer_user:
            return (False, f'You must follow this user to see their {list_type} list.', 401)
        elif not is_approved_follower:
            return (False, f'You must follow this user to see their {list_type} list.', 403)
    
    # visibility == 'everyone' and not blocked by private account = allow
    return (True, None, None)


@require_http_methods(["GET"])
@never_cache  # PHASE4_STEP5: Prevent caching of followers list
def get_followers_list(request, username):
    """
    GET /api/profile/<username>/followers/
    Returns list of users following the profile (Instagram-like).
    
    Privacy: Two-layer enforcement (account privacy + list visibility)
    Always returns JSON with proper status codes.
    
    PHASE4_STEP5: Added @never_cache to prevent 410 Gone from cached responses
    """
    try:
        target_user = get_object_or_404(User, username=username)
        viewer_user = request.user if request.user.is_authenticated else None
        
        # Get target profile and privacy settings (create if missing)
        try:
            target_profile, _ = UserProfile.objects.get_or_create(user=target_user)
            privacy_settings, _ = PrivacySettings.objects.get_or_create(
                user_profile=target_profile,
                defaults={
                    'followers_list_visibility': 'everyone',
                    'following_list_visibility': 'everyone',
                    'is_private_account': False,
                }
            )
        except Exception as e:
            logger.error(f"Error loading privacy settings for {username}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Unable to load privacy settings'
            }, status=500)
        
        # Privacy check with two-layer enforcement
        can_view, error_msg, status_code = can_view_follow_list(
            viewer_user, target_user, target_profile, privacy_settings, 'followers'
        )
        
        if not can_view:
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status_code)
        
        # Get followers (Follow.follower → Follow.following = target_user)
        followers = Follow.objects.filter(following=target_user).select_related(
            'follower',
            'follower__profile'
        )[:100]
        
        # Build response data
        followers_data = []
        for follow_obj in followers:
            follower_user = follow_obj.follower
            follower_profile = getattr(follower_user, 'profile', None)
            
            # Check if viewer follows this person
            is_followed_by_viewer = False
            if viewer_user and viewer_user != follower_user:
                is_followed_by_viewer = Follow.objects.filter(
                    follower=viewer_user,
                    following=follower_user
                ).exists()
            
            # Get avatar URL
            avatar_url = '/static/img/user_avatar/default-avatar.png'
            if follower_profile and follower_profile.avatar:
                try:
                    avatar_url = follower_profile.avatar.url
                except:
                    pass
            
            followers_data.append({
                'username': follower_user.username,
                'display_name': follower_profile.display_name if follower_profile else follower_user.username,
                'avatar_url': avatar_url,
                'is_followed_by_viewer': is_followed_by_viewer,
                'is_viewer': viewer_user == follower_user if viewer_user else False,
                'profile_url': f'/@{follower_user.username}/'
            })
        
        return JsonResponse({
            'success': True,
            'followers': followers_data,
            'count': len(followers_data),
            'has_more': Follow.objects.filter(following=target_user).count() > 100
        }, status=200)
        
    except Exception as e:
        logger.error(f"Unexpected error in get_followers_list for {username}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while loading followers'
        }, status=500)


@require_http_methods(["GET"])
@never_cache  # PHASE4_STEP5: Prevent caching of following list
def get_following_list(request, username):
    """
    GET /api/profile/<username>/following/
    Returns list of users the profile is following (Instagram-like).
    
    Privacy: Two-layer enforcement (account privacy + list visibility)
    Always returns JSON with proper status codes.
    
    PHASE4_STEP5: Added @never_cache to prevent 410 Gone from cached responses
    """
    try:
        target_user = get_object_or_404(User, username=username)
        viewer_user = request.user if request.user.is_authenticated else None
        
        # Get target profile and privacy settings (create if missing)
        try:
            target_profile, _ = UserProfile.objects.get_or_create(user=target_user)
            privacy_settings, _ = PrivacySettings.objects.get_or_create(
                user_profile=target_profile,
                defaults={
                    'followers_list_visibility': 'everyone',
                    'following_list_visibility': 'everyone',
                    'is_private_account': False,
                }
            )
        except Exception as e:
            logger.error(f"Error loading privacy settings for {username}: {e}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Unable to load privacy settings'
            }, status=500)
        
        # Privacy check with two-layer enforcement
        can_view, error_msg, status_code = can_view_follow_list(
            viewer_user, target_user, target_profile, privacy_settings, 'following'
        )
        
        if not can_view:
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=status_code)
        
        # Get following (Follow.follower = target_user → Follow.following)
        following = Follow.objects.filter(follower=target_user).select_related(
            'following',
            'following__profile'
        )[:100]
        
        # Build response data
        following_data = []
        for follow_obj in following:
            followed_user = follow_obj.following
            followed_profile = getattr(followed_user, 'profile', None)
            
            # Check if viewer follows this person
            is_followed_by_viewer = False
            if viewer_user and viewer_user != followed_user:
                is_followed_by_viewer = Follow.objects.filter(
                    follower=viewer_user,
                    following=followed_user
                ).exists()
            
            # Get avatar URL
            avatar_url = '/static/img/user_avatar/default-avatar.png'
            if followed_profile and followed_profile.avatar:
                try:
                    avatar_url = followed_profile.avatar.url
                except:
                    pass
            
            following_data.append({
                'username': followed_user.username,
                'display_name': followed_profile.display_name if followed_profile else followed_user.username,
                'avatar_url': avatar_url,
                'is_followed_by_viewer': is_followed_by_viewer,
                'is_viewer': viewer_user == followed_user if viewer_user else False,
                'profile_url': f'/@{followed_user.username}/'
            })
        
        return JsonResponse({
            'success': True,
            'following': following_data,
            'count': len(following_data),
            'has_more': Follow.objects.filter(follower=target_user).count() > 100
        }, status=200)
        
    except Exception as e:
        logger.error(f"Unexpected error in get_following_list for {username}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while loading following list'
        }, status=500)
