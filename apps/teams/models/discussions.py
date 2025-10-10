"""
Team Discussion Board Models (Task 7 - Social & Community Integration)

Forum-style discussion boards for teams with markdown support, categories, and moderation.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify


class TeamDiscussionPost(models.Model):
    """
    Discussion board posts (threads) for teams.
    Supports markdown, categories, pinning, and locking.
    """
    
    POST_TYPES = [
        ('general', 'General Discussion'),
        ('announcement', 'Announcement'),
        ('strategy', 'Strategy & Tactics'),
        ('recruitment', 'Recruitment'),
        ('question', 'Question'),
        ('feedback', 'Feedback'),
        ('event', 'Event'),
    ]
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='discussion_posts',
        help_text="Team this post belongs to"
    )
    
    author = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='discussion_posts',
        help_text="User who created the post"
    )
    
    post_type = models.CharField(
        max_length=20,
        choices=POST_TYPES,
        default='general',
        help_text="Category/type of post"
    )
    
    title = models.CharField(
        max_length=200,
        help_text="Post title"
    )
    
    slug = models.SlugField(
        max_length=250,
        help_text="URL-friendly version of title"
    )
    
    content = models.TextField(
        help_text="Post content (supports markdown)"
    )
    
    # Visibility
    is_public = models.BooleanField(
        default=False,
        help_text="Whether non-team members can view"
    )
    
    # Moderation
    is_pinned = models.BooleanField(
        default=False,
        help_text="Pin to top of discussion board"
    )
    
    is_locked = models.BooleanField(
        default=False,
        help_text="Prevent new comments"
    )
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    
    # Engagement
    views_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times viewed"
    )
    
    likes = models.ManyToManyField(
        'user_profile.UserProfile',
        blank=True,
        related_name='liked_posts',
        help_text="Users who liked this post"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Last comment or update time"
    )
    
    class Meta:
        db_table = 'teams_discussion_post'
        verbose_name = 'Discussion Post'
        verbose_name_plural = 'Discussion Posts'
        ordering = ['-is_pinned', '-last_activity_at']
        indexes = [
            models.Index(fields=['team', '-last_activity_at']),
            models.Index(fields=['team', 'post_type', '-last_activity_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['-is_pinned', '-last_activity_at']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.team.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:250]
        super().save(*args, **kwargs)
    
    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])
    
    def toggle_pin(self):
        """Toggle pin status"""
        self.is_pinned = not self.is_pinned
        self.save(update_fields=['is_pinned'])
    
    def toggle_lock(self):
        """Toggle lock status"""
        self.is_locked = not self.is_locked
        self.save(update_fields=['is_locked'])
    
    def soft_delete(self):
        """Soft delete post"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    @property
    def comment_count(self):
        """Get number of comments"""
        return self.comments.filter(is_deleted=False).count()
    
    @property
    def like_count(self):
        """Get number of likes"""
        return self.likes.count()
    
    @property
    def is_announcement(self):
        """Check if post is an announcement"""
        return self.post_type == 'announcement'


class TeamDiscussionComment(models.Model):
    """
    Comments/replies to discussion posts.
    Supports markdown, nested replies, and reactions.
    """
    
    post = models.ForeignKey(
        TeamDiscussionPost,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text="Post this comment belongs to"
    )
    
    author = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='discussion_comments',
        help_text="User who wrote the comment"
    )
    
    content = models.TextField(
        help_text="Comment content (supports markdown)"
    )
    
    # Reply/Thread Support
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Parent comment if this is a reply"
    )
    
    # State
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether comment has been edited"
    )
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    
    # Engagement
    likes = models.ManyToManyField(
        'user_profile.UserProfile',
        blank=True,
        related_name='liked_comments',
        help_text="Users who liked this comment"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'teams_discussion_comment'
        verbose_name = 'Discussion Comment'
        verbose_name_plural = 'Discussion Comments'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['author', '-created_at']),
            models.Index(fields=['reply_to', 'created_at']),
        ]
    
    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.author.user.username} on {self.post.title}: {preview}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Update parent post's last activity
        if is_new:
            self.post.update_activity()
    
    def mark_as_edited(self):
        """Mark comment as edited"""
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['is_edited', 'edited_at'])
    
    def soft_delete(self):
        """Soft delete comment"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    @property
    def like_count(self):
        """Get number of likes"""
        return self.likes.count()
    
    @property
    def reply_count(self):
        """Get number of replies"""
        return self.replies.filter(is_deleted=False).count()


class DiscussionSubscription(models.Model):
    """
    Track user subscriptions to discussion posts for notifications.
    Users automatically subscribe to posts they create or comment on.
    """
    
    user = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='discussion_subscriptions'
    )
    
    post = models.ForeignKey(
        TeamDiscussionPost,
        on_delete=models.CASCADE,
        related_name='subscriptions'
    )
    
    notify_on_comment = models.BooleanField(
        default=True,
        help_text="Notify when new comments are added"
    )
    
    notify_on_like = models.BooleanField(
        default=False,
        help_text="Notify when post is liked"
    )
    
    subscribed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teams_discussion_subscription'
        verbose_name = 'Discussion Subscription'
        verbose_name_plural = 'Discussion Subscriptions'
        unique_together = ['user', 'post']
        indexes = [
            models.Index(fields=['user', 'subscribed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} subscribed to {self.post.title}"
    
    @classmethod
    def subscribe(cls, user_profile, post, notify_comment=True, notify_like=False):
        """Subscribe user to post"""
        subscription, created = cls.objects.get_or_create(
            user=user_profile,
            post=post,
            defaults={
                'notify_on_comment': notify_comment,
                'notify_on_like': notify_like,
            }
        )
        return subscription
    
    @classmethod
    def unsubscribe(cls, user_profile, post):
        """Unsubscribe user from post"""
        cls.objects.filter(user=user_profile, post=post).delete()


class DiscussionNotification(models.Model):
    """
    Notifications for discussion board activity.
    Sent to subscribed users when posts/comments are updated.
    """
    
    NOTIFICATION_TYPES = [
        ('new_comment', 'New Comment'),
        ('new_reply', 'New Reply to Your Comment'),
        ('post_liked', 'Post Liked'),
        ('comment_liked', 'Comment Liked'),
        ('post_pinned', 'Post Pinned'),
        ('mentioned', 'Mentioned in Post/Comment'),
    ]
    
    recipient = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='discussion_notifications'
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES
    )
    
    post = models.ForeignKey(
        TeamDiscussionPost,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    comment = models.ForeignKey(
        TeamDiscussionComment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    
    actor = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='discussion_actions',
        help_text="User who triggered the notification"
    )
    
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'teams_discussion_notification'
        verbose_name = 'Discussion Notification'
        verbose_name_plural = 'Discussion Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.recipient.user.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @classmethod
    def create_notification(cls, recipient, notification_type, post, actor, comment=None):
        """Create a new notification (avoid duplicates)"""
        # Don't notify the actor
        if recipient == actor:
            return None
        
        # Check for recent duplicate
        recent_duplicate = cls.objects.filter(
            recipient=recipient,
            notification_type=notification_type,
            post=post,
            comment=comment,
            actor=actor,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).exists()
        
        if recent_duplicate:
            return None
        
        notification = cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            post=post,
            comment=comment,
            actor=actor
        )
        return notification
    
    @classmethod
    def get_unread_count(cls, user_profile):
        """Get count of unread notifications"""
        return cls.objects.filter(recipient=user_profile, is_read=False).count()
