"""
Followers/Following API V2 - Modern Implementation
==================================================

Clean, professional API for followers/following lists.
Server-side rendering ready, optimized for performance.

Author: GitHub Copilot
Date: January 22, 2026
"""

import logging
import hashlib
from urllib.parse import quote
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q, Exists, OuterRef
from django.views.decorators.cache import cache_control

from apps.user_profile.models_main import Follow, UserProfile

logger = logging.getLogger(__name__)

User = get_user_model()


def _build_initials(label: str, fallback: str = 'DC') -> str:
    value = (label or '').strip()
    if not value:
        return fallback

    parts = [chunk for chunk in value.split() if chunk]
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[1][0]).upper()
    else:
        compact = ''.join(ch for ch in value if ch.isalnum())
        initials = (compact[:2] or value[:2] or fallback).upper()

    return ''.join(ch for ch in initials if ch.isalnum())[:2] or fallback


def _avatar_bg_color(seed: str) -> str:
    palette = ['#1f2937', '#0f4c81', '#0b6e4f', '#7c2d12', '#5b21b6', '#065f46']
    digest = hashlib.sha256((seed or 'deltacrown').encode('utf-8')).hexdigest()
    return palette[int(digest[:2], 16) % len(palette)]


def _fallback_avatar_data_uri(display_name: str, username: str = '') -> str:
    label = display_name or username or 'DeltaCrown'
    initials = _build_initials(label, fallback='DC')
    bg = _avatar_bg_color(username or label)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">'
        f'<rect width="96" height="96" fill="{bg}"/>'
        f'<text x="50%" y="53%" text-anchor="middle" dominant-baseline="middle" '
        'fill="#ffffff" font-family="Arial, sans-serif" font-size="34" font-weight="700">'
        f'{initials}</text>'
        '</svg>'
    )
    return f'data:image/svg+xml;utf8,{quote(svg)}'


def _safe_avatar_url(user, profile) -> str:
    if profile and getattr(profile, 'avatar', None):
        try:
            return profile.avatar.url
        except Exception:
            pass

    display_name = ''
    if profile:
        display_name = getattr(profile, 'display_name', '') or ''
    if not display_name:
        display_name = user.get_full_name() or user.username
    return _fallback_avatar_data_uri(display_name, user.username)


@login_required
@cache_control(max_age=60, private=True)  # Cache for 1 minute
def get_followers_list(request, username):
    """
    Get paginated list of users who follow the specified user.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Results per page (default: 20, max: 100)
        - search: Search query for username or display name
    
    Response:
        {
            "success": true,
            "data": {
                "users": [...],
                "pagination": {...}
            },
            "meta": {...}
        }
    """
    try:
        # Get target user
        target_user = User.objects.select_related('profile').get(username=username)
        
        # Get query parameters
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 100)
        search_query = request.GET.get('search', '').strip()
        
        # Base queryset: users who follow target_user
        followers = Follow.objects.filter(
            following=target_user
        ).select_related(
            'follower__profile'
        ).order_by('-created_at')
        
        # Apply search filter
        if search_query:
            followers = followers.filter(
                Q(follower__username__icontains=search_query) |
                Q(follower__first_name__icontains=search_query) |
                Q(follower__last_name__icontains=search_query)
            )
        
        # Annotate with relationship to viewer
        viewer = request.user
        followers = followers.annotate(
            is_followed_by_viewer=Exists(
                Follow.objects.filter(
                    follower=viewer,
                    following=OuterRef('follower')
                )
            )
        )
        
        # Paginate
        paginator = Paginator(followers, per_page)
        
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Serialize users
        users_data = []
        for follow in page_obj:
            follower = follow.follower
            profile = getattr(follower, 'profile', None)
            
            # Check if mutual (viewer follows this follower and follower follows viewer)
            is_mutual = False
            if viewer.is_authenticated and follower != viewer:
                is_mutual = Follow.objects.filter(
                    follower=viewer,
                    following=follower
                ).exists() and Follow.objects.filter(
                    follower=follower,
                    following=viewer
                ).exists()
            
            users_data.append({
                'id': follower.id,
                'username': follower.username,
                'display_name': profile.display_name if profile else follower.get_full_name() or follower.username,
                'avatar_url': _safe_avatar_url(follower, profile),
                'bio': profile.bio[:100] if profile and profile.bio else None,
                'verified': profile.kyc_status == 'verified' if profile else False,
                'is_following': follow.is_followed_by_viewer,
                'is_mutual': is_mutual,
                'is_self': follower == viewer,
                'profile_url': f'/@{follower.username}/',
                'followed_at': follow.created_at.isoformat()
            })
        
        # Pagination metadata
        pagination = {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
        
        return JsonResponse({
            'success': True,
            'followers': users_data,
            'users': users_data,
            'pagination': pagination,
            'data': {
                'users': users_data,
                'pagination': pagination
            },
            'meta': {
                'target_user': username,
                'search_query': search_query or None,
                'viewer': viewer.username
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'User @{username} not found'
        }, status=404)
    
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid page or per_page parameter'
        }, status=400)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': 'Server error'
        }, status=500)


@login_required
@cache_control(max_age=60, private=True)
def get_following_list(request, username):
    """
    Get paginated list of users that the specified user follows.
    
    Query Parameters:
        - page: Page number (default: 1)
        - per_page: Results per page (default: 20, max: 100)
        - search: Search query for username or display name
    
    Response: Same format as get_followers_list
    """
    try:
        # Get target user
        target_user = User.objects.select_related('profile').get(username=username)
        
        # Get query parameters
        page = int(request.GET.get('page', 1))
        per_page = min(int(request.GET.get('per_page', 20)), 100)
        search_query = request.GET.get('search', '').strip()
        
        # Base queryset: users that target_user follows
        following = Follow.objects.filter(
            follower=target_user
        ).select_related(
            'following__profile'
        ).order_by('-created_at')
        
        # Apply search filter
        if search_query:
            following = following.filter(
                Q(following__username__icontains=search_query) |
                Q(following__first_name__icontains=search_query) |
                Q(following__last_name__icontains=search_query)
            )
        
        # Annotate with relationship to viewer
        viewer = request.user
        following = following.annotate(
            is_followed_by_viewer=Exists(
                Follow.objects.filter(
                    follower=viewer,
                    following=OuterRef('following')
                )
            )
        )
        
        # Paginate
        paginator = Paginator(following, per_page)
        
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        
        # Serialize users
        users_data = []
        for follow in page_obj:
            followed_user = follow.following
            profile = getattr(followed_user, 'profile', None)
            
            # Check if mutual
            is_mutual = False
            if viewer.is_authenticated and followed_user != viewer:
                is_mutual = Follow.objects.filter(
                    follower=viewer,
                    following=followed_user
                ).exists() and Follow.objects.filter(
                    follower=followed_user,
                    following=viewer
                ).exists()
            
            users_data.append({
                'id': followed_user.id,
                'username': followed_user.username,
                'display_name': profile.display_name if profile else followed_user.get_full_name() or followed_user.username,
                'avatar_url': _safe_avatar_url(followed_user, profile),
                'bio': profile.bio[:100] if profile and profile.bio else None,
                'verified': profile.kyc_status == 'verified' if profile else False,
                'is_following': follow.is_followed_by_viewer,
                'is_mutual': is_mutual,
                'is_self': followed_user == viewer,
                'profile_url': f'/@{followed_user.username}/',
                'followed_at': follow.created_at.isoformat()
            })
        
        # Pagination metadata
        pagination = {
            'page': page_obj.number,
            'per_page': per_page,
            'total': paginator.count,
            'total_pages': paginator.num_pages,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }
        
        return JsonResponse({
            'success': True,
            'following': users_data,
            'users': users_data,
            'pagination': pagination,
            'data': {
                'users': users_data,
                'pagination': pagination
            },
            'meta': {
                'target_user': username,
                'search_query': search_query or None,
                'viewer': viewer.username
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'User @{username} not found'
        }, status=404)
    
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid page or per_page parameter'
        }, status=400)
    
    except Exception as e:
        logger.exception(f"Error in get_following_list for {username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Server error',
            'detail': str(e) if request.user.is_staff else None
        }, status=500)


@login_required
@cache_control(max_age=300, private=True)  # Cache for 5 minutes
def get_mutual_followers(request, username):
    """
    Get users who follow both the viewer and the target user.
    
    Query Parameters:
        - limit: Max results (default: 10, max: 50)
    
    Response: Simplified user list
    """
    try:
        target_user = User.objects.get(username=username)
        viewer = request.user
        
        if viewer == target_user:
            return JsonResponse({
                'success': True,
                'data': {'users': []},
                'meta': {'message': 'Cannot get mutual followers with yourself'}
            })
        
        limit = min(int(request.GET.get('limit', 10)), 50)
        
        # Get users who follow both viewer and target
        mutual_followers = Follow.objects.filter(
            following=target_user
        ).filter(
            follower__in=Follow.objects.filter(
                following=viewer
            ).values_list('follower', flat=True)
        ).select_related('follower__profile')[:limit]
        
        users_data = []
        for follow in mutual_followers:
            follower = follow.follower
            profile = getattr(follower, 'profile', None)
            
            users_data.append({
                'id': follower.id,
                'username': follower.username,
                'display_name': profile.display_name if profile else follower.username,
                'avatar_url': _safe_avatar_url(follower, profile),
                'profile_url': f'/@{follower.username}/'
            })
        
        return JsonResponse({
            'success': True,
            'data': {
                'users': users_data,
                'count': len(users_data)
            },
            'meta': {
                'target_user': username,
                'viewer': viewer.username
            }
        })
        
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'User @{username} not found'
        }, status=404)
    
    except Exception as e:
        logger.exception(f"Error in get_mutual_followers_api_v2 for {username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Server error',
            'detail': str(e) if request.user.is_staff else None
        }, status=500)
