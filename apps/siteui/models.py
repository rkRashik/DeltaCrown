"""
Community and User Social Models
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from apps.user_profile.models import UserProfile

User = get_user_model()


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


# ============================================================================
# PHASE 7, EPIC 7.6: HELP & ONBOARDING MODELS
# ============================================================================

class HelpContent(models.Model):
    """
    Help content/documentation that can be displayed to users contextually.
    Supports organizer onboarding, tooltips, and help overlays.
    """
    AUDIENCE_CHOICES = [
        ('organizer', 'Organizer'),
        ('referee', 'Referee'),
        ('player', 'Player'),
        ('global', 'Global/All Users'),
    ]
    
    # Identity
    key = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Unique identifier (e.g., 'results_inbox_intro')"
    )
    scope = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Context/page where this help applies (e.g., 'organizer_results_inbox')"
    )
    
    # Content
    title = models.CharField(max_length=200)
    body = models.TextField(help_text="Markdown or plain text content")
    html_body = models.TextField(
        blank=True,
        help_text="Pre-rendered HTML (optional, for performance)"
    )
    
    # Targeting
    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default='global',
        help_text="Who should see this help content"
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this content is currently shown"
    )
    display_order = models.IntegerField(
        default=0,
        help_text="Sort order when multiple help items exist for same scope"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['scope', 'display_order', 'title']
        indexes = [
            models.Index(fields=['scope', 'is_active']),
            models.Index(fields=['audience', 'is_active']),
        ]
        verbose_name = "Help Content"
        verbose_name_plural = "Help Content Items"
    
    def __str__(self):
        return f"{self.key} ({self.scope})"


class HelpOverlay(models.Model):
    """
    Defines a specific tooltip or overlay item that should be shown on a page.
    References HelpContent and specifies visual placement.
    """
    PLACEMENT_CHOICES = [
        ('top', 'Top'),
        ('top-right', 'Top Right'),
        ('right', 'Right'),
        ('bottom-right', 'Bottom Right'),
        ('bottom', 'Bottom'),
        ('bottom-left', 'Bottom Left'),
        ('left', 'Left'),
        ('top-left', 'Top Left'),
        ('center', 'Center'),
    ]
    
    # Reference to help content
    help_content = models.ForeignKey(
        HelpContent,
        on_delete=models.CASCADE,
        related_name='overlays'
    )
    
    # Page/context where this overlay appears
    page_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Page identifier (e.g., 'results_inbox', 'scheduling')"
    )
    
    # Visual placement
    placement = models.CharField(
        max_length=20,
        choices=PLACEMENT_CHOICES,
        default='top-right',
        help_text="Where the overlay should appear on screen"
    )
    
    # Advanced config (JSON)
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Advanced configuration (trigger, animation, etc.)"
    )
    
    # Metadata
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['page_id', 'display_order']
        indexes = [
            models.Index(fields=['page_id', 'is_active']),
        ]
        verbose_name = "Help Overlay"
        verbose_name_plural = "Help Overlays"
    
    def __str__(self):
        return f"{self.help_content.key} on {self.page_id}"


class OrganizerOnboardingState(models.Model):
    """
    Tracks onboarding wizard progress for organizers.
    Stores which steps have been completed or dismissed per user (and optionally per tournament).
    """
    # User being onboarded
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organizer_onboarding_states'
    )
    
    # Optional tournament scope (if onboarding is per-tournament)
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='onboarding_states',
        help_text="If set, onboarding is tournament-specific"
    )
    
    # Step identifier
    step_key = models.CharField(
        max_length=100,
        help_text="Onboarding step identifier (e.g., 'results_inbox_intro')"
    )
    
    # State
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user completed this step"
    )
    dismissed = models.BooleanField(
        default=False,
        help_text="Whether user dismissed/skipped this step"
    )
    dismissed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user dismissed this step"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        # Unique constraint: one record per user+tournament+step
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'tournament', 'step_key'],
                name='unique_onboarding_state_per_user_tournament_step'
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'tournament']),
            models.Index(fields=['user', 'step_key']),
        ]
        verbose_name = "Organizer Onboarding State"
        verbose_name_plural = "Organizer Onboarding States"
    
    def __str__(self):
        tournament_part = f" (Tournament {self.tournament_id})" if self.tournament_id else ""
        status = "completed" if self.completed_at else ("dismissed" if self.dismissed else "pending")
        return f"{self.user.username} - {self.step_key}{tournament_part} [{status}]"
    
    @property
    def is_complete(self):
        """Check if this step has been completed."""
        return self.completed_at is not None
    
    @property
    def is_pending(self):
        """Check if this step is still pending (not completed and not dismissed)."""
        return not self.is_complete and not self.dismissed