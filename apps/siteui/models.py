"""
Community and User Social Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from apps.user_profile.models import UserProfile


class CommunityPost(models.Model):
    """
    Community posts that can be created by individual users
    """
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]
    
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_posts')
    title = models.CharField(max_length=200, blank=True)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    
    # Game association (optional)
    game = models.CharField(max_length=100, blank=True, help_text="Game this post is related to")
    
    # Engagement
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    is_pinned = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['visibility', '-created_at']),
            models.Index(fields=['game', '-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.author.user.username}: {self.title or self.content[:50]}"
    
    def get_absolute_url(self):
        return reverse('siteui:community_post_detail', kwargs={'pk': self.pk})
    
    @property
    def excerpt(self):
        """Return a short excerpt of the content"""
        if self.title:
            return self.title
        return self.content[:100] + '...' if len(self.content) > 100 else self.content


class CommunityPostMedia(models.Model):
    """
    Media attachments for community posts
    """
    MEDIA_TYPES = [
        ('image', 'Image'),
        ('video', 'Video'),
        ('gif', 'GIF'),
    ]
    
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPES, default='image')
    file = models.FileField(upload_to='community/posts/%Y/%m/%d/')
    thumbnail = models.ImageField(upload_to='community/thumbnails/%Y/%m/%d/', blank=True)
    alt_text = models.CharField(max_length=200, blank=True)
    
    # File info
    file_size = models.PositiveIntegerField(default=0)  # in bytes
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Media for {self.post.author.user.username}'s post"


class CommunityPostComment(models.Model):
    """
    Comments on community posts
    """
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_comments')
    content = models.TextField()
    
    # Reply system
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Moderation
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.author.user.username} on {self.post}"
    
    @property
    def is_reply(self):
        return self.parent is not None


class CommunityPostLike(models.Model):
    """
    Likes on community posts
    """
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_likes')
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['post', 'user']
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} likes {self.post}"


class CommunityPostShare(models.Model):
    """
    Shares/reposts of community posts
    """
    original_post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='shares')
    shared_by = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='community_shares')
    comment = models.TextField(blank=True, help_text="Optional comment when sharing")
    
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        unique_together = ['original_post', 'shared_by']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shared_by.user.username} shared {self.original_post}"


# Signal handlers to update counters
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=CommunityPostLike)
def increment_like_count(sender, instance, created, **kwargs):
    if created:
        instance.post.likes_count = instance.post.likes.count()
        instance.post.save(update_fields=['likes_count'])

@receiver(post_delete, sender=CommunityPostLike)
def decrement_like_count(sender, instance, **kwargs):
    instance.post.likes_count = instance.post.likes.count()
    instance.post.save(update_fields=['likes_count'])

@receiver(post_save, sender=CommunityPostComment)
def increment_comment_count(sender, instance, created, **kwargs):
    if created:
        instance.post.comments_count = instance.post.comments.count()
        instance.post.save(update_fields=['comments_count'])

@receiver(post_delete, sender=CommunityPostComment)
def decrement_comment_count(sender, instance, **kwargs):
    instance.post.comments_count = instance.post.comments.count()
    instance.post.save(update_fields=['comments_count'])

@receiver(post_save, sender=CommunityPostShare)
def increment_share_count(sender, instance, created, **kwargs):
    if created:
        instance.original_post.shares_count = instance.original_post.shares.count()
        instance.original_post.save(update_fields=['shares_count'])

@receiver(post_delete, sender=CommunityPostShare)
def decrement_share_count(sender, instance, **kwargs):
    instance.original_post.shares_count = instance.original_post.shares.count()
    instance.original_post.save(update_fields=['shares_count'])