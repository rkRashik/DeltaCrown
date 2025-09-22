# apps/teams/models/social.py
"""
Team Social Features Models
==========================
Models for team posts, blogs, photos, comments, and social interactions.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid
from PIL import Image
import os

User = get_user_model()


def team_media_upload_path(instance, filename):
    """Generate upload path for team media files."""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Safety check - handle both direct team access and post->team access
    try:
        if hasattr(instance, 'team'):
            team = instance.team
        elif hasattr(instance, 'post') and hasattr(instance.post, 'team'):
            team = instance.post.team
        else:
            # Fallback to a generic path
            return f"teams/unknown/media/{filename}"
        
        return f"teams/{team.slug or team.id}/media/{filename}"
    except:
        # Ultimate fallback
        return f"teams/fallback/media/{filename}"


def team_banner_upload_path(instance, filename):
    """Generate upload path for team banner images."""
    ext = filename.split('.')[-1]
    filename = f"banner_{uuid.uuid4().hex}.{ext}"
    return f"teams/{instance.slug or instance.id}/banner/{filename}"


class TeamPost(models.Model):
    """Model for team posts (status updates, announcements, etc.)"""
    
    POST_TYPE_CHOICES = [
        ('status', 'Status Update'),
        ('announcement', 'Announcement'),
        ('achievement', 'Achievement'),
        ('media', 'Media Post'),
        ('blog', 'Blog Post'),
        ('match_result', 'Match Result'),
        ('recruitment', 'Recruitment'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('followers', 'Followers Only'),
        ('members', 'Team Members Only'),
        ('private', 'Private'),
    ]
    
    team = models.ForeignKey(
        'Team',
        on_delete=models.CASCADE,
        related_name='posts'
    )
    author = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='team_posts'
    )
    post_type = models.CharField(
        max_length=20,
        choices=POST_TYPE_CHOICES,
        default='status'
    )
    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional title for the post"
    )
    content = models.TextField(
        max_length=5000,
        help_text="Post content (supports markdown)"
    )
    visibility = models.CharField(
        max_length=20,
        choices=VISIBILITY_CHOICES,
        default='public'
    )
    is_pinned = models.BooleanField(
        default=False,
        help_text="Pin this post to the top of team feed"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Feature this post in community hub"
    )
    
    # Engagement metrics
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    views_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(
        default=False,
        help_text="Indicates if this post has been edited after creation"
    )
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at']),
            models.Index(fields=['visibility', '-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.team.name} - {self.get_post_type_display()} by {self.author}"
    
    def get_absolute_url(self):
        return reverse('teams:post_detail', kwargs={
            'slug': self.team.slug,
            'post_id': self.id
        })
    
    @property
    def is_published(self):
        return self.published_at is not None and self.published_at <= timezone.now()
    
    def publish(self):
        """Publish the post."""
        if not self.published_at:
            self.published_at = timezone.now()
            self.save(update_fields=['published_at'])
    
    def get_excerpt(self, length=150):
        """Get excerpt of the content."""
        if len(self.content) <= length:
            return self.content
        return self.content[:length].rsplit(' ', 1)[0] + '...'
    
    def can_user_view(self, user_profile):
        """Check if a user can view this post based on visibility settings."""
        if self.visibility == 'public':
            return True
        elif self.visibility == 'followers':
            return self.team.is_followed_by(user_profile) or self.team.is_member(user_profile)
        elif self.visibility == 'members':
            return self.team.is_member(user_profile)
        return False


class TeamPostMedia(models.Model):
    """Model for media attachments to team posts."""
    
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
    ]
    
    post = models.ForeignKey(
        TeamPost,
        on_delete=models.CASCADE,
        related_name='media'
    )
    media_type = models.CharField(
        max_length=20,
        choices=MEDIA_TYPE_CHOICES,
        default='image'
    )
    file = models.FileField(
        upload_to=team_media_upload_path,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'mp4', 'mov', 'pdf', 'doc', 'docx']
            )
        ]
    )
    caption = models.CharField(
        max_length=500,
        blank=True,
        help_text="Optional caption for the media"
    )
    alt_text = models.CharField(
        max_length=200,
        blank=True,
        help_text="Alternative text for accessibility"
    )
    file_size = models.PositiveIntegerField(null=True, blank=True)
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds for videos"
    )
    
    # Image dimensions (for images)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.get_media_type_display()} for {self.post}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Extract metadata for images
        if self.media_type == 'image' and self.file:
            try:
                with Image.open(self.file.path) as img:
                    self.width, self.height = img.size
                    TeamPostMedia.objects.filter(id=self.id).update(
                        width=self.width,
                        height=self.height
                    )
            except Exception:
                pass


class TeamPostComment(models.Model):
    """Model for comments on team posts."""
    
    post = models.ForeignKey(
        TeamPost,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='team_post_comments'
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies'
    )
    content = models.TextField(
        max_length=1000,
        help_text="Comment content"
    )
    
    # Engagement
    likes_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['parent', 'created_at']),
        ]
    
    def __str__(self):
        return f"Comment by {self.author} on {self.post}"
    
    @property
    def is_reply(self):
        return self.parent is not None
    
    def get_replies(self):
        return self.replies.select_related('author__user').order_by('created_at')


class TeamPostLike(models.Model):
    """Model for likes on team posts and comments."""
    
    CONTENT_TYPE_CHOICES = [
        ('post', 'Post'),
        ('comment', 'Comment'),
    ]
    
    user = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='team_post_likes'
    )
    content_type = models.CharField(
        max_length=10,
        choices=CONTENT_TYPE_CHOICES
    )
    post = models.ForeignKey(
        TeamPost,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    comment = models.ForeignKey(
        TeamPostComment,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [
            ('user', 'post'),
            ('user', 'comment'),
        ]
        indexes = [
            models.Index(fields=['content_type', 'created_at']),
        ]
    
    def __str__(self):
        if self.post:
            return f"{self.user} likes post {self.post.id}"
        return f"{self.user} likes comment {self.comment.id}"


class TeamFollower(models.Model):
    """Model for team followers/fans."""
    
    team = models.ForeignKey(
        'Team',
        on_delete=models.CASCADE,
        related_name='followers'
    )
    follower = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='following_teams'
    )
    
    # Notification preferences
    notify_posts = models.BooleanField(default=True)
    notify_matches = models.BooleanField(default=True)
    notify_achievements = models.BooleanField(default=False)
    
    followed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['team', 'follower']
        indexes = [
            models.Index(fields=['team', '-followed_at']),
            models.Index(fields=['follower', '-followed_at']),
        ]
    
    def __str__(self):
        return f"{self.follower} follows {self.team}"


class TeamActivity(models.Model):
    """Model for tracking team activities and generating activity feed."""
    
    ACTIVITY_TYPE_CHOICES = [
        ('team_created', 'Team Created'),
        ('member_joined', 'Member Joined'),
        ('member_left', 'Member Left'),
        ('captain_changed', 'Captain Changed'),
        ('post_published', 'Post Published'),
        ('match_scheduled', 'Match Scheduled'),
        ('match_completed', 'Match Completed'),
        ('achievement_earned', 'Achievement Earned'),
        ('tournament_joined', 'Tournament Joined'),
        ('tournament_won', 'Tournament Won'),
    ]
    
    team = models.ForeignKey(
        'Team',
        on_delete=models.CASCADE,
        related_name='activities'
    )
    activity_type = models.CharField(
        max_length=30,
        choices=ACTIVITY_TYPE_CHOICES
    )
    actor = models.ForeignKey(
        'user_profile.UserProfile',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='team_activities'
    )
    description = models.CharField(
        max_length=500,
        help_text="Human-readable description of the activity"
    )
    
    # Optional references to related objects
    related_post = models.ForeignKey(
        TeamPost,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )
    related_user = models.ForeignKey(
        'user_profile.UserProfile',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='mentioned_in_activities'
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional activity data"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_public = models.BooleanField(
        default=True,
        help_text="Whether this activity is visible to public"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
            models.Index(fields=['is_public', '-created_at']),
        ]
        verbose_name_plural = 'Team Activities'
    
    def __str__(self):
        return f"{self.team.name}: {self.description}"