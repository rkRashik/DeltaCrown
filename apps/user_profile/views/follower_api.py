"""
Follower/Following API Endpoints (Phase 2F)

Instagram-style follower management with privacy controls:
- GET followers list (with privacy enforcement)
- GET following list (with privacy enforcement)
- POST follow/unfollow actions
"""

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.accounts.models import User
from apps.user_profile.models import UserProfile, Follow, PrivacySettings
import logging

logger = logging.getLogger(__name__)


def can_view_follower_list(viewer, target_user):
    """Check if viewer can see target's follower list"""
    # Owner can always see
    if viewer and viewer.is_authenticated and viewer == target_user:
        return True
    
    # Get privacy settings
    try:
        privacy = target_user.profile.privacy_settings
        # Simple boolean: True = public, False = private (owner only)
        return privacy.show_followers_list
    except:
        return True  # Default to public if privacy not set


def can_view_following_list(viewer, target_user):
    """Check if viewer can see target's following list"""
    # Owner can always see
    if viewer and viewer.is_authenticated and viewer == target_user:
        return True
    
    # Get privacy settings
    try:
        privacy = target_user.profile.privacy_settings
        # Simple boolean: True = public, False = private (owner only)
        return privacy.show_following_list
    except:
        return True  # Default to public if privacy not set


@require_http_methods(["GET"])
def get_followers(request, username):
    """
    GET /api/profile/<username>/followers/
    
    Returns list of users following the target user.
    Privacy-aware: respects followers_list_visibility setting.
    """
    target_user = get_object_or_404(User, username=username)
    
    # Check privacy
    if not can_view_follower_list(request.user, target_user):
        return JsonResponse({
            'error': 'This followers list is private',
            'private': True
        }, status=403)
    
    # Get followers
    followers = Follow.objects.filter(following=target_user).select_related('follower', 'follower__profile')
    
    # Build response
    followers_data = []
    for follow in followers:
        follower = follow.follower
        try:
            profile = follower.profile
            followers_data.append({
                'user_id': follower.id,
                'username': follower.username,
                'display_name': profile.display_name,
                'avatar_url': profile.avatar_url or '/static/images/default-avatar.png',
                'is_verified': profile.is_verified,
                'is_following': request.user.is_authenticated and Follow.objects.filter(
                    follower=request.user,
                    following=follower
                ).exists()
            })
        except:
            continue
    
    return JsonResponse({
        'success': True,
        'followers': followers_data,
        'count': len(followers_data)
    })


@require_http_methods(["GET"])
def get_following(request, username):
    """
    GET /api/profile/<username>/following/
    
    Returns list of users that the target user is following.
    Privacy-aware: respects following_list_visibility setting.
    """
    target_user = get_object_or_404(User, username=username)
    
    # Check privacy
    if not can_view_following_list(request.user, target_user):
        return JsonResponse({
            'error': 'This following list is private',
            'private': True
        }, status=403)
    
    # Get following
    following = Follow.objects.filter(follower=target_user).select_related('following', 'following__profile')
    
    # Build response
    following_data = []
    for follow in following:
        followed_user = follow.following
        try:
            profile = followed_user.profile
            following_data.append({
                'user_id': followed_user.id,
                'username': followed_user.username,
                'display_name': profile.display_name,
                'avatar_url': profile.avatar_url or '/static/images/default-avatar.png',
                'is_verified': profile.is_verified,
                'is_following': request.user.is_authenticated and Follow.objects.filter(
                    follower=request.user,
                    following=followed_user
                ).exists()
            })
        except:
            continue
    
    return JsonResponse({
        'success': True,
        'following': following_data,
        'count': len(following_data)
    })


@login_required
@require_http_methods(["POST"])
def follow_user(request, username):
    """
    POST /api/profile/<username>/follow/
    
    Follow a user. Idempotent - returns success if already following.
    """
    target_user = get_object_or_404(User, username=username)
    
    # Can't follow yourself
    if request.user == target_user:
        return JsonResponse({'error': 'Cannot follow yourself'}, status=400)
    
    # Create or get follow relationship
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=target_user
    )
    
    # Update follower/following counts on profiles
    try:
        request.user.profile.following_count = Follow.objects.filter(follower=request.user).count()
        request.user.profile.save(update_fields=['following_count'])
        
        target_user.profile.follower_count = Follow.objects.filter(following=target_user).count()
        target_user.profile.save(update_fields=['follower_count'])
    except:
        pass
    
    return JsonResponse({
        'success': True,
        'following': True,
        'message': 'Now following' if created else 'Already following'
    })


@login_required
@require_http_methods(["POST"])
def unfollow_user(request, username):
    """
    POST /api/profile/<username>/unfollow/
    
    Unfollow a user. Idempotent - returns success if not following.
    """
    target_user = get_object_or_404(User, username=username)
    
    # Can't unfollow yourself
    if request.user == target_user:
        return JsonResponse({'error': 'Cannot unfollow yourself'}, status=400)
    
    # Delete follow relationship
    deleted_count, _ = Follow.objects.filter(
        follower=request.user,
        following=target_user
    ).delete()
    
    # Update follower/following counts on profiles
    try:
        request.user.profile.following_count = Follow.objects.filter(follower=request.user).count()
        request.user.profile.save(update_fields=['following_count'])
        
        target_user.profile.follower_count = Follow.objects.filter(following=target_user).count()
        target_user.profile.save(update_fields=['follower_count'])
    except:
        pass
    
    return JsonResponse({
        'success': True,
        'following': False,
        'message': 'Unfollowed' if deleted_count > 0 else 'Not following'
    })
