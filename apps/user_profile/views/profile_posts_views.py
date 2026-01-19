# apps/user_profile/views/profile_posts_views.py
"""
Community Posts API endpoints for user profiles.

Owner-only post creation/deletion on their own profile.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

from apps.siteui.models import CommunityPost
from apps.user_profile.models import UserProfile

logger = logging.getLogger(__name__)


@login_required
@require_POST
def create_post(request):
    """
    Create a new community post on the user's own profile.
    
    POST /api/profile/posts/create/
    
    Payload:
        - content (required): Post content text
        - title (optional): Post title
        - visibility (optional): public/friends/private (default: public)
        - game (optional): Associated game name
    
    Returns:
        JSON with created post data or error
    """
    try:
        # Get user's profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found'
            }, status=404)
        
        # Validate content
        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Content is required'
            }, status=400)
        
        if len(content) < 1:
            return JsonResponse({
                'success': False,
                'error': 'Content must not be empty'
            }, status=400)
        
        # Optional fields
        title = request.POST.get('title', '').strip()
        visibility = request.POST.get('visibility', 'public')
        game = request.POST.get('game', '').strip()
        
        # Validate visibility choice
        valid_visibilities = ['public', 'friends', 'private']
        if visibility not in valid_visibilities:
            visibility = 'public'
        
        # Create post
        post = CommunityPost.objects.create(
            author=profile,
            content=content,
            title=title,
            visibility=visibility,
            game=game,
            is_approved=True  # Auto-approve for now (can add moderation later)
        )
        
        logger.info(f"[POSTS] create user={request.user.username} post={post.id}")
        
        # Return post data for immediate UI insertion
        return JsonResponse({
            'success': True,
            'post': {
                'id': post.id,
                'author': {
                    'username': profile.user.username,
                    'display_name': profile.display_name or profile.user.username,
                    'avatar_url': profile.get_avatar_url() or '',
                },
                'title': post.title,
                'content': post.content,
                'visibility': post.visibility,
                'game': post.game,
                'created_at': post.created_at.isoformat(),
                'likes_count': 0,
                'comments_count': 0,
                'shares_count': 0,
                'media': []
            }
        })
        
    except Exception as e:
        logger.error(f"Error creating post: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to create post'
        }, status=500)


@login_required
@require_POST
def delete_post(request, post_id):
    """
    Delete a community post (owner only).
    
    POST /api/profile/posts/<post_id>/delete/
    
    Returns:
        JSON with success status
    """
    try:
        # Get user's profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found'
            }, status=404)
        
        # Get post and verify ownership
        try:
            post = CommunityPost.objects.get(id=post_id)
        except CommunityPost.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Post not found'
            }, status=404)
        
        # Check ownership
        if post.author != profile:
            return JsonResponse({
                'success': False,
                'error': 'You can only delete your own posts'
            }, status=403)
        
        # Delete post (or soft delete if needed)
        post_id_deleted = post.id
        post.delete()
        
        logger.info(f"[POSTS] delete user={request.user.username} post={post_id_deleted}")
        
        return JsonResponse({
            'success': True,
            'message': 'Post deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to delete post'
        }, status=500)


@login_required
@require_POST
def edit_post(request, post_id):
    """
    Edit a community post (owner only).
    
    POST /api/profile/posts/<post_id>/edit/
    
    Payload:
        - content (required): Updated post content
    
    Returns:
        JSON with updated post data or error
    """
    try:
        # Get user's profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found'
            }, status=404)
        
        # Get post and verify ownership
        try:
            post = CommunityPost.objects.get(id=post_id)
        except CommunityPost.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Post not found'
            }, status=404)
        
        # Check ownership
        if post.author != profile:
            return JsonResponse({
                'success': False,
                'error': 'You can only edit your own posts'
            }, status=403)
        
        # Validate new content
        content = request.POST.get('content', '').strip()
        if not content:
            return JsonResponse({
                'success': False,
                'error': 'Content is required'
            }, status=400)
        
        # Update post
        post.content = content
        post.save()
        
        logger.info(f"[POSTS] edit user={request.user.username} post={post.id}")
        
        return JsonResponse({
            'success': True,
            'post': {
                'id': post.id,
                'content': post.content,
                'updated_at': post.updated_at.isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error editing post {post_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to edit post'
        }, status=500)
