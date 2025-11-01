"""
Site UI Event Handlers

Handles counter updates for community posts (likes, comments, shares).
"""
import logging
from django.apps import apps

from apps.core.events import event_bus

logger = logging.getLogger(__name__)


def increment_like_count(event):
    """
    Increment like count when a like is created.
    
    Replaces: increment_like_count signal
    Triggered by: PostLikedEvent
    """
    try:
        post_id = event.data.get('post_id')
        CommunityPost = apps.get_model("siteui", "CommunityPost")
        
        post = CommunityPost.objects.get(id=post_id)
        post.likes_count = post.likes.count()
        post.save(update_fields=['likes_count'])
        
        logger.debug(f"✅ Incremented like count for post {post_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to increment like count: {e}", exc_info=True)


def decrement_like_count(event):
    """
    Decrement like count when a like is removed.
    
    Replaces: decrement_like_count signal
    Triggered by: PostUnlikedEvent
    """
    try:
        post_id = event.data.get('post_id')
        CommunityPost = apps.get_model("siteui", "CommunityPost")
        
        post = CommunityPost.objects.get(id=post_id)
        post.likes_count = post.likes.count()
        post.save(update_fields=['likes_count'])
        
        logger.debug(f"✅ Decremented like count for post {post_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to decrement like count: {e}", exc_info=True)


def increment_comment_count(event):
    """
    Increment comment count when a comment is created.
    
    Replaces: increment_comment_count signal
    Triggered by: PostCommentedEvent
    """
    try:
        post_id = event.data.get('post_id')
        CommunityPost = apps.get_model("siteui", "CommunityPost")
        
        post = CommunityPost.objects.get(id=post_id)
        post.comments_count = post.comments.count()
        post.save(update_fields=['comments_count'])
        
        logger.debug(f"✅ Incremented comment count for post {post_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to increment comment count: {e}", exc_info=True)


def decrement_comment_count(event):
    """
    Decrement comment count when a comment is deleted.
    
    Replaces: decrement_comment_count signal
    Triggered by: PostCommentDeletedEvent
    """
    try:
        post_id = event.data.get('post_id')
        CommunityPost = apps.get_model("siteui", "CommunityPost")
        
        post = CommunityPost.objects.get(id=post_id)
        post.comments_count = post.comments.count()
        post.save(update_fields=['comments_count'])
        
        logger.debug(f"✅ Decremented comment count for post {post_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to decrement comment count: {e}", exc_info=True)


def increment_share_count(event):
    """
    Increment share count when a post is shared.
    
    Replaces: increment_share_count signal
    Triggered by: PostSharedEvent
    """
    try:
        post_id = event.data.get('post_id')
        CommunityPost = apps.get_model("siteui", "CommunityPost")
        
        post = CommunityPost.objects.get(id=post_id)
        post.shares_count = post.shares.count()
        post.save(update_fields=['shares_count'])
        
        logger.debug(f"✅ Incremented share count for post {post_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to increment share count: {e}", exc_info=True)


def decrement_share_count(event):
    """
    Decrement share count when a share is removed.
    
    Replaces: decrement_share_count signal
    Triggered by: PostUnsharedEvent
    """
    try:
        post_id = event.data.get('post_id')
        CommunityPost = apps.get_model("siteui", "CommunityPost")
        
        post = CommunityPost.objects.get(id=post_id)
        post.shares_count = post.shares.count()
        post.save(update_fields=['shares_count'])
        
        logger.debug(f"✅ Decremented share count for post {post_id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to decrement share count: {e}", exc_info=True)


def register_siteui_event_handlers():
    """Register site UI event handlers"""
    
    # Like events
    event_bus.subscribe(
        'post.liked',
        increment_like_count,
        name='increment_like_count',
        priority=20
    )
    
    event_bus.subscribe(
        'post.unliked',
        decrement_like_count,
        name='decrement_like_count',
        priority=20
    )
    
    # Comment events
    event_bus.subscribe(
        'post.commented',
        increment_comment_count,
        name='increment_comment_count',
        priority=20
    )
    
    event_bus.subscribe(
        'post.comment_deleted',
        decrement_comment_count,
        name='decrement_comment_count',
        priority=20
    )
    
    # Share events
    event_bus.subscribe(
        'post.shared',
        increment_share_count,
        name='increment_share_count',
        priority=20
    )
    
    event_bus.subscribe(
        'post.unshared',
        decrement_share_count,
        name='decrement_share_count',
        priority=20
    )
    
    logger.info("📢 Registered site UI event handlers")


__all__ = [
    'increment_like_count',
    'decrement_like_count',
    'increment_comment_count',
    'decrement_comment_count',
    'increment_share_count',
    'decrement_share_count',
    'register_siteui_event_handlers',
]
