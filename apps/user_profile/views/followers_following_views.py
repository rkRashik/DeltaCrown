"""
Followers and Following List Views
===================================

Display paginated lists of followers and following users.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q

from apps.user_profile.models_main import UserProfile, Follow
from apps.user_profile.services.follow_service import FollowService

User = get_user_model()


def followers_page(request, username):
    """
    Display list of users following the target user.
    
    URL: /@username/followers/
    """
    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(UserProfile, user=target_user)
    
    # Get all followers
    followers = Follow.objects.filter(
        following=target_user
    ).select_related(
        'follower'
    ).order_by('-created_at')
    
    # Enrich with additional data
    enriched_followers = []
    viewer_profile = None
    if request.user.is_authenticated:
        try:
            viewer_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            pass
    
    for follow in followers:
        follower_user = follow.follower
        try:
            follower_profile = UserProfile.objects.get(user=follower_user)
        except UserProfile.DoesNotExist:
            continue
            
        follower_data = {
            'profile': follower_profile,
            'user': follower_user,
            'username': follower_user.username,
            'display_name': follower_profile.display_name or follower_user.username,
            'bio': follower_profile.bio or '',
            'avatar_url': follower_profile.avatar.url if follower_profile.avatar else '/static/images/default-avatar.png',
            'is_verified': follower_profile.kyc_status == 'verified',
            'followers_count': Follow.objects.filter(following=follower_user).count(),
            'following_count': Follow.objects.filter(follower=follower_user).count(),
        }
        
        # Check if viewer follows this user
        if viewer_profile:
            follower_data['viewer_follows'] = Follow.objects.filter(
                follower=request.user,
                following=follower_user
            ).exists()
            follower_data['is_self'] = request.user == follower_user
        else:
            follower_data['viewer_follows'] = False
            follower_data['is_self'] = False
        
        enriched_followers.append(follower_data)
    
    # Paginate
    paginator = Paginator(enriched_followers, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'target_user': target_user,
        'target_profile': target_profile,
        'followers': page_obj,
        'total_count': followers.count(),
        'page_obj': page_obj,
        'page_title': f"People following {target_profile.display_name or target_user.username}"
    }
    
    return render(request, 'user_profile/followers_list.html', context)


def following_page(request, username):
    """
    Display list of users that the target user is following.
    
    URL: /@username/following/
    """
    target_user = get_object_or_404(User, username=username)
    target_profile = get_object_or_404(UserProfile, user=target_user)
    
    # Get all following
    following = Follow.objects.filter(
        follower=target_user
    ).select_related(
        'following'
    ).order_by('-created_at')
    
    # Enrich with additional data
    enriched_following = []
    viewer_profile = None
    if request.user.is_authenticated:
        try:
            viewer_profile = UserProfile.objects.get(user=request.user)
        except UserProfile.DoesNotExist:
            pass
    
    for follow in following:
        followee_user = follow.following
        try:
            followee_profile = UserProfile.objects.get(user=followee_user)
        except UserProfile.DoesNotExist:
            continue
            
        followee_data = {
            'profile': followee_profile,
            'user': followee_user,
            'username': followee_user.username,
            'display_name': followee_profile.display_name or followee_user.username,
            'bio': followee_profile.bio or '',
            'avatar_url': followee_profile.avatar.url if followee_profile.avatar else '/static/images/default-avatar.png',
            'is_verified': followee_profile.kyc_status == 'verified',
            'followers_count': Follow.objects.filter(following=followee_user).count(),
            'following_count': Follow.objects.filter(follower=followee_user).count(),
        }
        
        # Check if viewer follows this user
        if viewer_profile:
            followee_data['viewer_follows'] = Follow.objects.filter(
                follower=request.user,
                following=followee_user
            ).exists()
            followee_data['is_self'] = request.user == followee_user
        else:
            followee_data['viewer_follows'] = False
            followee_data['is_self'] = False
        
        enriched_following.append(followee_data)
    
    # Paginate
    paginator = Paginator(enriched_following, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'target_user': target_user,
        'target_profile': target_profile,
        'following': page_obj,
        'total_count': following.count(),
        'page_obj': page_obj,
        'page_title': f"People {target_profile.display_name or target_user.username} is following"
    }
    
    return render(request, 'user_profile/following_list.html', context)
