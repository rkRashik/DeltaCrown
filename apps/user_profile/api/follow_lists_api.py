"""
UP PHASE 8: Instagram-like Followers/Following Lists API
Provides JSON endpoints for followers and following lists with privacy controls.
"""

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model

from apps.user_profile.models import Follow, PrivacySettings

User = get_user_model()


@require_http_methods(["GET"])
def get_followers_list(request, username):
    """
    GET /api/profile/<username>/followers/
    Returns list of users following the profile (Instagram-like).
    
    Privacy Rules:
    - Owner: Always see full list
    - Visitor: See list only if privacy allows (followers_list_visibility)
    - Anonymous: Blocked unless explicitly public
    """
    target_user = get_object_or_404(User, username=username)
    viewer_user = request.user if request.user.is_authenticated else None
    
    # Check if viewer is owner
    is_owner = viewer_user and viewer_user == target_user
    
    # Get privacy settings
    try:
        privacy_settings = PrivacySettings.objects.get(user=target_user)
    except PrivacySettings.DoesNotExist:
        # No privacy settings = default to public
        privacy_settings = None
    
    # Privacy check
    if not is_owner:
        if not viewer_user:
            # Anonymous user - check if list is public
            if privacy_settings and privacy_settings.followers_list_visibility != 'everyone':
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required to view followers list'
                }, status=401)
        else:
            # Authenticated visitor - check visibility setting
            if privacy_settings:
                visibility = privacy_settings.followers_list_visibility
                
                if visibility == 'only_me':
                    return JsonResponse({
                        'success': False,
                        'error': 'This followers list is private'
                    }, status=403)
                elif visibility == 'followers':
                    # Check if viewer follows target
                    is_following = Follow.objects.filter(
                        follower=viewer_user,
                        followee=target_user
                    ).exists()
                    if not is_following:
                        return JsonResponse({
                            'success': False,
                            'error': 'You must follow this user to see their followers list'
                        }, status=403)
                # 'everyone' = no restriction
    
    # Get followers (limit to 100 for performance)
    followers = Follow.objects.filter(followee=target_user).select_related(
        'follower',
        'follower__userprofile'
    )[:100]
    
    # Build response data
    followers_data = []
    for follow_obj in followers:
        follower = follow_obj.follower
        follower_profile = getattr(follower, 'userprofile', None)
        
        # Check if viewer follows this person
        is_followed_by_viewer = False
        if viewer_user and viewer_user != follower:
            is_followed_by_viewer = Follow.objects.filter(
                follower=viewer_user,
                followee=follower
            ).exists()
        
        # Get avatar URL
        avatar_url = None
        if follower_profile and follower_profile.avatar:
            avatar_url = follower_profile.avatar.url
        
        followers_data.append({
            'username': follower.username,
            'display_name': follower_profile.display_name if follower_profile else follower.username,
            'avatar_url': avatar_url,
            'is_followed_by_viewer': is_followed_by_viewer,
            'is_viewer': viewer_user == follower if viewer_user else False,
            'profile_url': f'/@{follower.username}/'
        })
    
    return JsonResponse({
        'success': True,
        'followers': followers_data,
        'count': len(followers_data),
        'has_more': Follow.objects.filter(followee=target_user).count() > 100
    })


@require_http_methods(["GET"])
def get_following_list(request, username):
    """
    GET /api/profile/<username>/following/
    Returns list of users the profile is following (Instagram-like).
    
    Privacy Rules:
    - Owner: Always see full list
    - Visitor: See list only if privacy allows (following_list_visibility)
    - Anonymous: Blocked unless explicitly public
    """
    target_user = get_object_or_404(User, username=username)
    viewer_user = request.user if request.user.is_authenticated else None
    
    # Check if viewer is owner
    is_owner = viewer_user and viewer_user == target_user
    
    # Get privacy settings
    try:
        privacy_settings = PrivacySettings.objects.get(user=target_user)
    except PrivacySettings.DoesNotExist:
        # No privacy settings = default to public
        privacy_settings = None
    
    # Privacy check
    if not is_owner:
        if not viewer_user:
            # Anonymous user - check if list is public
            if privacy_settings and privacy_settings.following_list_visibility != 'everyone':
                return JsonResponse({
                    'success': False,
                    'error': 'Authentication required to view following list'
                }, status=401)
        else:
            # Authenticated visitor - check visibility setting
            if privacy_settings:
                visibility = privacy_settings.following_list_visibility
                
                if visibility == 'only_me':
                    return JsonResponse({
                        'success': False,
                        'error': 'This following list is private'
                    }, status=403)
                elif visibility == 'followers':
                    # Check if viewer follows target
                    is_following = Follow.objects.filter(
                        follower=viewer_user,
                        followee=target_user
                    ).exists()
                    if not is_following:
                        return JsonResponse({
                            'success': False,
                            'error': 'You must follow this user to see their following list'
                        }, status=403)
                # 'everyone' = no restriction
    
    # Get following (limit to 100 for performance)
    following = Follow.objects.filter(follower=target_user).select_related(
        'followee',
        'followee__userprofile'
    )[:100]
    
    # Build response data
    following_data = []
    for follow_obj in following:
        followee = follow_obj.followee
        followee_profile = getattr(followee, 'userprofile', None)
        
        # Check if viewer follows this person
        is_followed_by_viewer = False
        if viewer_user and viewer_user != followee:
            is_followed_by_viewer = Follow.objects.filter(
                follower=viewer_user,
                followee=followee
            ).exists()
        
        # Get avatar URL
        avatar_url = None
        if followee_profile and followee_profile.avatar:
            avatar_url = followee_profile.avatar.url
        
        following_data.append({
            'username': followee.username,
            'display_name': followee_profile.display_name if followee_profile else followee.username,
            'avatar_url': avatar_url,
            'is_followed_by_viewer': is_followed_by_viewer,
            'is_viewer': viewer_user == followee if viewer_user else False,
            'profile_url': f'/@{followee.username}/'
        })
    
    return JsonResponse({
        'success': True,
        'following': following_data,
        'count': len(following_data),
        'has_more': Follow.objects.filter(follower=target_user).count() > 100
    })
