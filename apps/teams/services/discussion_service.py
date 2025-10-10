"""
Discussion Service - Business logic for team discussion board (Task 7 Phase 2)

Handles posts, comments, likes, subscriptions, and notifications.
"""
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django.core.exceptions import PermissionDenied, ValidationError
from typing import Optional, List, Dict, Any

from apps.teams.models import (
    Team,
    TeamMembership,
    TeamDiscussionPost,
    TeamDiscussionComment,
    DiscussionSubscription,
    DiscussionNotification,
)
from apps.user_profile.models import UserProfile


class DiscussionService:
    """
    Service class for discussion board operations.
    """
    
    @staticmethod
    def _check_team_access(
        user_profile: UserProfile,
        team: Team,
        require_active: bool = True
    ) -> TeamMembership:
        """
        Check if user has access to team discussions.
        
        Args:
            user_profile: The user to check
            team: The team
            require_active: Whether to require active membership
            
        Returns:
            TeamMembership object
            
        Raises:
            PermissionDenied: If user doesn't have access
        """
        try:
            membership = TeamMembership.objects.get(
                team=team,
                user_profile=user_profile
            )
            
            if require_active and membership.status != 'active':
                raise PermissionDenied("You are not an active member of this team")
            
            return membership
        except TeamMembership.DoesNotExist:
            raise PermissionDenied("You are not a member of this team")
    
    @staticmethod
    def _can_view_post(post: TeamDiscussionPost, user_profile: Optional[UserProfile]) -> bool:
        """
        Check if user can view a post.
        
        Args:
            post: The post to check
            user_profile: The user (can be None for anonymous)
            
        Returns:
            True if user can view the post
        """
        # Deleted posts are only visible to admins
        if post.is_deleted:
            if not user_profile:
                return False
            try:
                membership = TeamMembership.objects.get(
                    team=post.team,
                    user_profile=user_profile
                )
                return membership.role in ['owner', 'admin'] or post.team.owner == user_profile
            except TeamMembership.DoesNotExist:
                return False
        
        # Public posts are visible to everyone
        if post.is_public:
            return True
        
        # Private posts require team membership
        if not user_profile:
            return False
        
        return TeamMembership.objects.filter(
            team=post.team,
            user_profile=user_profile,
            status='active'
        ).exists()
    
    @classmethod
    @transaction.atomic
    def create_post(
        cls,
        team: Team,
        author: UserProfile,
        title: str,
        content: str,
        post_type: str = 'general',
        is_public: bool = False
    ) -> TeamDiscussionPost:
        """
        Create a new discussion post.
        
        Args:
            team: The team
            author: The post author
            title: Post title
            content: Post content (markdown)
            post_type: Type of post
            is_public: Whether post is public
            
        Returns:
            The created post
            
        Raises:
            PermissionDenied: If user cannot create posts
            ValidationError: If data is invalid
        """
        # Check access
        membership = cls._check_team_access(author, team)
        
        # Validate title
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty")
        
        if len(title) > 200:
            raise ValidationError("Title cannot exceed 200 characters")
        
        # Validate content
        if not content or not content.strip():
            raise ValidationError("Content cannot be empty")
        
        if len(content) > 10000:
            raise ValidationError("Content cannot exceed 10,000 characters")
        
        # Validate post type
        valid_types = [choice[0] for choice in TeamDiscussionPost.POST_TYPES]
        if post_type not in valid_types:
            raise ValidationError(f"Invalid post type: {post_type}")
        
        # Only announcements by admins
        if post_type == 'announcement':
            if membership.role not in ['owner', 'admin'] and team.owner != author:
                raise PermissionDenied("Only team owners and admins can create announcements")
        
        # Create post
        post = TeamDiscussionPost.objects.create(
            team=team,
            author=author,
            title=title.strip(),
            content=content.strip(),
            post_type=post_type,
            is_public=is_public
        )
        
        # Auto-subscribe author to post
        DiscussionSubscription.subscribe(author, post)
        
        return post
    
    @classmethod
    @transaction.atomic
    def edit_post(
        cls,
        post: TeamDiscussionPost,
        editor: UserProfile,
        title: Optional[str] = None,
        content: Optional[str] = None,
        post_type: Optional[str] = None,
        is_public: Optional[bool] = None
    ) -> TeamDiscussionPost:
        """
        Edit an existing post.
        
        Args:
            post: The post to edit
            editor: The user editing
            title: New title (optional)
            content: New content (optional)
            post_type: New type (optional)
            is_public: New visibility (optional)
            
        Returns:
            The updated post
            
        Raises:
            PermissionDenied: If user cannot edit
            ValidationError: If data is invalid
        """
        # Check if user can edit
        membership = cls._check_team_access(editor, post.team)
        
        can_edit = (
            post.author == editor or
            membership.role in ['owner', 'admin'] or
            post.team.owner == editor
        )
        
        if not can_edit:
            raise PermissionDenied("You don't have permission to edit this post")
        
        if post.is_deleted:
            raise ValidationError("Cannot edit a deleted post")
        
        # Update title
        if title is not None:
            if not title.strip():
                raise ValidationError("Title cannot be empty")
            if len(title) > 200:
                raise ValidationError("Title cannot exceed 200 characters")
            post.title = title.strip()
            post.slug = slugify(title)[:250]
        
        # Update content
        if content is not None:
            if not content.strip():
                raise ValidationError("Content cannot be empty")
            if len(content) > 10000:
                raise ValidationError("Content cannot exceed 10,000 characters")
            post.content = content.strip()
        
        # Update post type (admins only)
        if post_type is not None:
            if membership.role not in ['owner', 'admin'] and post.team.owner != editor:
                raise PermissionDenied("Only admins can change post type")
            
            valid_types = [choice[0] for choice in TeamDiscussionPost.POST_TYPES]
            if post_type not in valid_types:
                raise ValidationError(f"Invalid post type: {post_type}")
            post.post_type = post_type
        
        # Update visibility (admins only)
        if is_public is not None:
            if membership.role not in ['owner', 'admin'] and post.team.owner != editor:
                raise PermissionDenied("Only admins can change post visibility")
            post.is_public = is_public
        
        post.save()
        
        return post
    
    @classmethod
    @transaction.atomic
    def delete_post(
        cls,
        post: TeamDiscussionPost,
        deleter: UserProfile
    ) -> TeamDiscussionPost:
        """
        Soft delete a post.
        
        Args:
            post: The post to delete
            deleter: The user deleting
            
        Returns:
            The deleted post
            
        Raises:
            PermissionDenied: If user cannot delete
        """
        # Check access
        membership = cls._check_team_access(deleter, post.team)
        
        can_delete = (
            post.author == deleter or
            membership.role in ['owner', 'admin'] or
            post.team.owner == deleter
        )
        
        if not can_delete:
            raise PermissionDenied("You don't have permission to delete this post")
        
        # Soft delete
        post.soft_delete()
        
        return post
    
    @classmethod
    @transaction.atomic
    def add_comment(
        cls,
        post: TeamDiscussionPost,
        author: UserProfile,
        content: str,
        reply_to: Optional[TeamDiscussionComment] = None
    ) -> TeamDiscussionComment:
        """
        Add a comment to a post.
        
        Args:
            post: The post to comment on
            author: The comment author
            content: Comment content (markdown)
            reply_to: Optional parent comment for threading
            
        Returns:
            The created comment
            
        Raises:
            PermissionDenied: If user cannot comment
            ValidationError: If data is invalid
        """
        # Check access
        cls._check_team_access(author, post.team)
        
        if post.is_deleted:
            raise ValidationError("Cannot comment on a deleted post")
        
        if post.is_locked:
            raise ValidationError("This post is locked and cannot receive new comments")
        
        # Validate content
        if not content or not content.strip():
            raise ValidationError("Comment cannot be empty")
        
        if len(content) > 5000:
            raise ValidationError("Comment cannot exceed 5,000 characters")
        
        # Create comment
        comment = TeamDiscussionComment.objects.create(
            post=post,
            author=author,
            content=content.strip(),
            reply_to=reply_to
        )
        
        # Auto-subscribe author to post
        DiscussionSubscription.subscribe(author, post)
        
        # Notify subscribers
        NotificationService.notify_new_comment(post, comment, author)
        
        # If replying to a comment, notify the parent comment author
        if reply_to and reply_to.author != author:
            DiscussionNotification.create_notification(
                recipient=reply_to.author,
                notification_type='new_reply',
                post=post,
                comment=comment,
                actor=author
            )
        
        return comment
    
    @classmethod
    @transaction.atomic
    def edit_comment(
        cls,
        comment: TeamDiscussionComment,
        editor: UserProfile,
        new_content: str
    ) -> TeamDiscussionComment:
        """
        Edit a comment.
        
        Args:
            comment: The comment to edit
            editor: The user editing
            new_content: New comment content
            
        Returns:
            The updated comment
            
        Raises:
            PermissionDenied: If user cannot edit
            ValidationError: If data is invalid
        """
        # Check if user can edit
        if comment.author != editor:
            raise PermissionDenied("You can only edit your own comments")
        
        if comment.is_deleted:
            raise ValidationError("Cannot edit a deleted comment")
        
        # Validate content
        if not new_content or not new_content.strip():
            raise ValidationError("Comment cannot be empty")
        
        if len(new_content) > 5000:
            raise ValidationError("Comment cannot exceed 5,000 characters")
        
        # Update comment
        comment.content = new_content.strip()
        comment.mark_as_edited()
        
        return comment
    
    @classmethod
    @transaction.atomic
    def delete_comment(
        cls,
        comment: TeamDiscussionComment,
        deleter: UserProfile
    ) -> TeamDiscussionComment:
        """
        Soft delete a comment.
        
        Args:
            comment: The comment to delete
            deleter: The user deleting
            
        Returns:
            The deleted comment
            
        Raises:
            PermissionDenied: If user cannot delete
        """
        # Check access
        membership = cls._check_team_access(deleter, comment.post.team)
        
        can_delete = (
            comment.author == deleter or
            membership.role in ['owner', 'admin'] or
            comment.post.team.owner == deleter
        )
        
        if not can_delete:
            raise PermissionDenied("You don't have permission to delete this comment")
        
        # Soft delete
        comment.soft_delete()
        
        return comment
    
    @classmethod
    @transaction.atomic
    def toggle_post_like(
        cls,
        post: TeamDiscussionPost,
        user: UserProfile
    ) -> tuple[bool, int]:
        """
        Toggle like on a post.
        
        Args:
            post: The post
            user: The user
            
        Returns:
            Tuple of (is_liked, new_like_count)
            
        Raises:
            PermissionDenied: If user cannot like
        """
        # Check access
        cls._check_team_access(user, post.team)
        
        if post.is_deleted:
            raise ValidationError("Cannot like a deleted post")
        
        # Toggle like
        if user in post.likes.all():
            post.likes.remove(user)
            is_liked = False
        else:
            post.likes.add(user)
            is_liked = True
            
            # Notify post author
            if post.author != user:
                DiscussionNotification.create_notification(
                    recipient=post.author,
                    notification_type='post_liked',
                    post=post,
                    actor=user
                )
        
        return is_liked, post.likes.count()
    
    @classmethod
    @transaction.atomic
    def toggle_comment_like(
        cls,
        comment: TeamDiscussionComment,
        user: UserProfile
    ) -> tuple[bool, int]:
        """
        Toggle like on a comment.
        
        Args:
            comment: The comment
            user: The user
            
        Returns:
            Tuple of (is_liked, new_like_count)
            
        Raises:
            PermissionDenied: If user cannot like
        """
        # Check access
        cls._check_team_access(user, comment.post.team)
        
        if comment.is_deleted:
            raise ValidationError("Cannot like a deleted comment")
        
        # Toggle like
        if user in comment.likes.all():
            comment.likes.remove(user)
            is_liked = False
        else:
            comment.likes.add(user)
            is_liked = True
            
            # Notify comment author
            if comment.author != user:
                DiscussionNotification.create_notification(
                    recipient=comment.author,
                    notification_type='comment_liked',
                    post=comment.post,
                    comment=comment,
                    actor=user
                )
        
        return is_liked, comment.likes.count()
    
    @classmethod
    @transaction.atomic
    def pin_post(
        cls,
        post: TeamDiscussionPost,
        user: UserProfile
    ) -> TeamDiscussionPost:
        """
        Toggle pin status of a post.
        
        Args:
            post: The post
            user: The user
            
        Returns:
            The updated post
            
        Raises:
            PermissionDenied: If user cannot pin
        """
        # Check access - only admins can pin
        membership = cls._check_team_access(user, post.team)
        
        if membership.role not in ['owner', 'admin'] and post.team.owner != user:
            raise PermissionDenied("Only team owners and admins can pin posts")
        
        # Toggle pin
        post.toggle_pin()
        
        # Notify post author if pinned
        if post.is_pinned and post.author != user:
            DiscussionNotification.create_notification(
                recipient=post.author,
                notification_type='post_pinned',
                post=post,
                actor=user
            )
        
        return post
    
    @classmethod
    @transaction.atomic
    def lock_post(
        cls,
        post: TeamDiscussionPost,
        user: UserProfile
    ) -> TeamDiscussionPost:
        """
        Toggle lock status of a post.
        
        Args:
            post: The post
            user: The user
            
        Returns:
            The updated post
            
        Raises:
            PermissionDenied: If user cannot lock
        """
        # Check access - only admins can lock
        membership = cls._check_team_access(user, post.team)
        
        if membership.role not in ['owner', 'admin'] and post.team.owner != user:
            raise PermissionDenied("Only team owners and admins can lock posts")
        
        # Toggle lock
        post.toggle_lock()
        
        return post
    
    @classmethod
    def increment_views(cls, post: TeamDiscussionPost) -> None:
        """
        Increment view count for a post.
        
        Args:
            post: The post
        """
        post.increment_views()
    
    @classmethod
    @transaction.atomic
    def subscribe_to_post(
        cls,
        post: TeamDiscussionPost,
        user: UserProfile,
        notify_comment: bool = True,
        notify_like: bool = False
    ) -> DiscussionSubscription:
        """
        Subscribe user to post notifications.
        
        Args:
            post: The post
            user: The user
            notify_comment: Notify on new comments
            notify_like: Notify on new likes
            
        Returns:
            The subscription
            
        Raises:
            PermissionDenied: If user cannot subscribe
        """
        # Check access
        cls._check_team_access(user, post.team)
        
        subscription = DiscussionSubscription.subscribe(
            user,
            post,
            notify_comment,
            notify_like
        )
        
        return subscription
    
    @classmethod
    @transaction.atomic
    def unsubscribe_from_post(
        cls,
        post: TeamDiscussionPost,
        user: UserProfile
    ) -> None:
        """
        Unsubscribe user from post notifications.
        
        Args:
            post: The post
            user: The user
        """
        DiscussionSubscription.unsubscribe(user, post)
    
    @classmethod
    def get_team_posts(
        cls,
        team: Team,
        user: Optional[UserProfile] = None,
        post_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[TeamDiscussionPost]:
        """
        Get posts for team discussion board.
        
        Args:
            team: The team
            user: The user requesting (can be None for public posts)
            post_type: Filter by post type
            limit: Maximum posts to return
            offset: Pagination offset
            
        Returns:
            List of posts
        """
        queryset = TeamDiscussionPost.objects.filter(
            team=team,
            is_deleted=False
        )
        
        # Filter by visibility
        if user:
            try:
                cls._check_team_access(user, team, require_active=False)
                # User is team member - can see all posts
            except PermissionDenied:
                # Not a member - only see public posts
                queryset = queryset.filter(is_public=True)
        else:
            # Anonymous - only see public posts
            queryset = queryset.filter(is_public=True)
        
        # Filter by type
        if post_type:
            queryset = queryset.filter(post_type=post_type)
        
        # Select related and prefetch
        queryset = queryset.select_related(
            'author__user',
            'team'
        ).prefetch_related(
            'likes'
        )
        
        # Apply pagination
        posts = list(queryset[offset:offset + limit])
        
        return posts


class NotificationService:
    """
    Service for creating discussion notifications.
    """
    
    @staticmethod
    @transaction.atomic
    def notify_new_comment(
        post: TeamDiscussionPost,
        comment: TeamDiscussionComment,
        actor: UserProfile
    ) -> List[DiscussionNotification]:
        """
        Notify subscribers about a new comment.
        
        Args:
            post: The post
            comment: The new comment
            actor: The user who commented
            
        Returns:
            List of created notifications
        """
        notifications = []
        
        # Get subscribers who want comment notifications
        subscriptions = DiscussionSubscription.objects.filter(
            post=post,
            notify_on_comment=True
        ).exclude(
            user=actor  # Don't notify the commenter
        ).select_related('user')
        
        for subscription in subscriptions:
            notification = DiscussionNotification.create_notification(
                recipient=subscription.user,
                notification_type='new_comment',
                post=post,
                comment=comment,
                actor=actor
            )
            if notification:
                notifications.append(notification)
        
        return notifications
    
    @staticmethod
    @transaction.atomic
    def mark_all_read(user: UserProfile) -> int:
        """
        Mark all notifications as read for user.
        
        Args:
            user: The user
            
        Returns:
            Number of notifications marked as read
        """
        unread = DiscussionNotification.objects.filter(
            recipient=user,
            is_read=False
        )
        
        count = unread.count()
        
        for notification in unread:
            notification.mark_as_read()
        
        return count
