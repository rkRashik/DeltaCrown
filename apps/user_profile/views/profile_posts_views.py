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
from django.db import transaction
import logging

from apps.siteui.models import (
    CommunityPost, CommunityPostMedia, CommunityPostLike,
    CommunityPostComment, CommunityPostShare
)
from apps.user_profile.models import UserProfile

# Media upload constants
MAX_MEDIA_FILES = 4
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
ALLOWED_VIDEO_TYPES = ['video/mp4', 'video/webm', 'video/quicktime']

logger = logging.getLogger(__name__)


@login_required
@require_POST
def create_post(request):
    """
    Create a new community post on the user's own profile with optional media.
    
    POST /api/profile/posts/create/
    
    Payload:
        - content (required): Post content text
        - title (optional): Post title
        - visibility (optional): public/friends/private (default: public)
        - game (optional): Associated game name
        - media[] (optional): Multiple media files (max 4, 20MB each)
    
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
        
        # Get media files
        media_files = request.FILES.getlist('media[]')
        
        # Validate media count
        if len(media_files) > MAX_MEDIA_FILES:
            return JsonResponse({
                'success': False,
                'error': f'Maximum {MAX_MEDIA_FILES} media files allowed'
            }, status=400)
        
        # Validate each media file
        for media_file in media_files:
            # Check file size
            if media_file.size > MAX_FILE_SIZE:
                return JsonResponse({
                    'success': False,
                    'error': f'{media_file.name} exceeds 20MB limit'
                }, status=400)
            
            # Check file type
            content_type = media_file.content_type
            if not (content_type in ALLOWED_IMAGE_TYPES or content_type in ALLOWED_VIDEO_TYPES):
                return JsonResponse({
                    'success': False,
                    'error': f'{media_file.name} is not a supported format'
                }, status=400)
        
        # Optional fields
        title = request.POST.get('title', '').strip()
        visibility = request.POST.get('visibility', 'public')
        game = request.POST.get('game', '').strip()
        
        # Validate visibility choice
        valid_visibilities = ['public', 'friends', 'private']
        if visibility not in valid_visibilities:
            visibility = 'public'
        
        # Create post with media in a transaction
        with transaction.atomic():
            post = CommunityPost.objects.create(
                author=profile,
                content=content,
                title=title,
                visibility=visibility,
                game=game,
                is_approved=True
            )
            
            # Create media records
            media_data = []
            for media_file in media_files:
                # Determine media type
                content_type = media_file.content_type
                if content_type in ALLOWED_IMAGE_TYPES:
                    if content_type == 'image/gif':
                        media_type = 'gif'
                    else:
                        media_type = 'image'
                elif content_type in ALLOWED_VIDEO_TYPES:
                    media_type = 'video'
                else:
                    continue
                
                # Create media object
                media = CommunityPostMedia.objects.create(
                    post=post,
                    media_type=media_type,
                    file=media_file,
                    file_size=media_file.size
                )
                
                # Extract dimensions for images
                if media_type in ['image', 'gif']:
                    try:
                        from PIL import Image
                        img = Image.open(media.file.path)
                        media.width, media.height = img.size
                        media.save(update_fields=['width', 'height'])
                    except Exception as e:
                        logger.warning(f"Could not extract image dimensions: {e}")
                
                media_data.append({
                    'url': media.file.url,
                    'type': media.media_type,
                    'width': media.width,
                    'height': media.height
                })
        
        logger.info(f"[POSTS] create user={request.user.username} post={post.id} media_count={len(media_files)}")
        
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
                'media': media_data,
                'likes_count': 0,
                'comments_count': 0,
                'shares_count': 0,
                'is_liked': False
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


@login_required
@require_POST
def like_post(request, post_id):
    """
    Toggle like on a post.
    
    POST /api/profile/posts/<post_id>/like/
    
    Returns:
        JSON with liked status and count
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
        
        # Get post
        try:
            post = CommunityPost.objects.get(id=post_id)
        except CommunityPost.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Post not found'
            }, status=404)
        
        # Toggle like
        like, created = CommunityPostLike.objects.get_or_create(
            post=post,
            user=profile
        )
        
        if not created:
            # Unlike
            like.delete()
            liked = False
            logger.info(f"[POSTS] unlike user={request.user.username} post={post_id}")
        else:
            liked = True
            logger.info(f"[POSTS] like user={request.user.username} post={post_id}")
        
        # Get updated count and save to post
        likes_count = post.likes.count()
        post.likes_count = likes_count
        post.save(update_fields=['likes_count'])
        
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': likes_count
        })
        
    except Exception as e:
        logger.error(f"Error toggling like on post {post_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to toggle like'
        }, status=500)


@login_required
@require_POST
def comment_on_post(request, post_id):
    """
    Add a comment to a post.
    
    POST /api/profile/posts/<post_id>/comment/
    
    Payload:
        - text (required): Comment content
    
    Returns:
        JSON with comment data
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
        
        # Get post
        try:
            post = CommunityPost.objects.get(id=post_id)
        except CommunityPost.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Post not found'
            }, status=404)
        
        # Validate comment text
        text = request.POST.get('text', '').strip()
        if not text:
            return JsonResponse({
                'success': False,
                'error': 'Comment text is required'
            }, status=400)
        
        if len(text) > 1000:
            return JsonResponse({
                'success': False,
                'error': 'Comment too long (max 1000 characters)'
            }, status=400)
        
        # Create comment
        comment = CommunityPostComment.objects.create(
            post=post,
            author=profile,
            content=text,
            is_approved=True
        )
        
        logger.info(f"[POSTS] comment user={request.user.username} post={post_id}")
        
        # Get updated count and save to post
        comments_count = post.comments.count()
        post.comments_count = comments_count
        post.save(update_fields=['comments_count'])
        
        return JsonResponse({
            'success': True,
            'comment': {
                'id': comment.id,
                'author': {
                    'username': profile.user.username,
                    'display_name': profile.display_name or profile.user.username,
                    'avatar_url': profile.get_avatar_url() or '',
                },
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'time_ago': 'just now'
            },
            'comments_count': comments_count
        })
        
    except Exception as e:
        logger.error(f"Error adding comment to post {post_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to add comment'
        }, status=500)


@login_required
def get_comments(request, post_id):
    """
    Get comments for a post.
    
    GET /api/profile/posts/<post_id>/comments/
    
    Returns:
        JSON with list of comments
    """
    try:
        # Get post
        try:
            post = CommunityPost.objects.get(id=post_id)
        except CommunityPost.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Post not found'
            }, status=404)
        
        # Get comments (latest 20, can add pagination later)
        comments = post.comments.filter(is_approved=True).select_related('author', 'author__user')[:20]
        
        comments_data = []
        for comment in comments:
            comments_data.append({
                'id': comment.id,
                'author': {
                    'username': comment.author.user.username,
                    'display_name': comment.author.display_name or comment.author.user.username,
                    'avatar_url': comment.author.get_avatar_url() or '',
                },
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'time_ago': 'just now'  # Can implement proper time ago calculation
            })
        
        return JsonResponse({
            'success': True,
            'comments': comments_data,
            'count': len(comments_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting comments for post {post_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to get comments'
        }, status=500)


@login_required
@require_POST
def share_post(request, post_id):
    """
    Share a post.
    
    POST /api/profile/posts/<post_id>/share/
    
    Returns:
        JSON with shares count
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
        
        # Get post
        try:
            post = CommunityPost.objects.get(id=post_id)
        except CommunityPost.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Post not found'
            }, status=404)
        
        # Create or get share record
        share, created = CommunityPostShare.objects.get_or_create(
            original_post=post,
            shared_by=profile
        )
        
        if created:
            logger.info(f"[POSTS] share user={request.user.username} post={post_id}")
        
        # Get updated count and save to post
        shares_count = post.shares.count()
        post.shares_count = shares_count
        post.save(update_fields=['shares_count'])
        
        return JsonResponse({
            'success': True,
            'shares_count': shares_count
        })
        
    except Exception as e:
        logger.error(f"Error sharing post {post_id}: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to share post'
        }, status=500)
