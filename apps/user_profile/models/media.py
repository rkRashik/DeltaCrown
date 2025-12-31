"""
User Profile Media Models - P0 Implementation
StreamConfig, HighlightClip, PinnedHighlight with URL validation.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings
from apps.user_profile.services.url_validator import (
    validate_highlight_url,
    validate_stream_url
)


class StreamConfig(models.Model):
    """
    User's live stream configuration (Twitch, YouTube, Facebook).
    
    Security:
    - URL validated via url_validator service
    - Only whitelisted platforms allowed
    - embed_url generated server-side
    
    Rules:
    - One stream config per user (enforced via unique constraint)
    - stream_url must pass validate_stream_url() check
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stream_config'
    )
    
    # Raw user-provided URL (validated on save)
    stream_url = models.URLField(
        max_length=500,
        help_text="Twitch, YouTube, or Facebook stream URL"
    )
    
    # Platform detected from URL
    platform = models.CharField(
        max_length=20,
        choices=[
            ('twitch', 'Twitch'),
            ('youtube', 'YouTube'),
            ('facebook', 'Facebook Gaming'),
        ],
        editable=False
    )
    
    # Channel ID extracted from URL
    channel_id = models.CharField(
        max_length=200,
        editable=False,
        help_text="Username or channel identifier"
    )
    
    # Server-side generated embed URL (NEVER user-provided)
    embed_url = models.URLField(
        max_length=500,
        editable=False,
        help_text="Safe iframe embed URL (auto-generated)"
    )
    
    # Stream title/description
    title = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text="Optional stream title"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Show stream on profile"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_stream_config'
        verbose_name = 'Stream Configuration'
        verbose_name_plural = 'Stream Configurations'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['platform']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.platform} stream"
    
    def clean(self):
        """Validate stream URL using url_validator service."""
        if not self.stream_url:
            raise ValidationError({'stream_url': 'Stream URL is required'})
        
        # Validate URL via service
        result = validate_stream_url(self.stream_url)
        
        if not result['valid']:
            raise ValidationError({'stream_url': result.get('error', 'Invalid stream URL')})
        
        # Populate fields from validation result
        self.platform = result['platform']
        self.channel_id = result['channel_id']
        self.embed_url = result['embed_url']
    
    def save(self, *args, **kwargs):
        """Run validation before save."""
        self.full_clean()
        super().save(*args, **kwargs)


class HighlightClip(models.Model):
    """
    User's highlight video clips (YouTube, Twitch, Medal.tv).
    
    Security:
    - URL validated via url_validator service
    - Only whitelisted platforms allowed
    - embed_url generated server-side
    
    Rules:
    - Multiple clips per user allowed
    - clip_url must pass validate_highlight_url() check
    - Maximum 20 clips per user (enforced in admin/views)
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='highlight_clips'
    )
    
    # Raw user-provided URL (validated on save)
    clip_url = models.URLField(
        max_length=500,
        help_text="YouTube, Twitch clip, or Medal.tv URL"
    )
    
    # Platform detected from URL
    platform = models.CharField(
        max_length=20,
        choices=[
            ('youtube', 'YouTube'),
            ('twitch', 'Twitch'),
            ('medal', 'Medal.tv'),
        ],
        editable=False
    )
    
    # Video ID extracted from URL
    video_id = models.CharField(
        max_length=200,
        editable=False,
        help_text="Video/clip identifier"
    )
    
    # Server-side generated embed URL (NEVER user-provided)
    embed_url = models.URLField(
        max_length=500,
        editable=False,
        help_text="Safe iframe embed URL (auto-generated)"
    )
    
    # Thumbnail URL (optional, auto-generated if available)
    # UP-PHASE2E-HOTFIX: null=True added to prevent IntegrityError when platform
    # doesn't provide immediate thumbnails (e.g., Facebook, private videos)
    thumbnail_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        editable=False,
        help_text="Video thumbnail (auto-generated, may be NULL if unavailable)"
    )
    
    # Clip metadata
    title = models.CharField(
        max_length=200,
        help_text="Clip title/description"
    )
    
    game = models.ForeignKey(
        'games.Game',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='highlight_clips',
        help_text="Game featured in this clip"
    )
    
    # Display order (lower = shown first)
    display_order = models.IntegerField(
        default=0,
        help_text="Display order on profile (lower = first)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile_highlight_clip'
        verbose_name = 'Highlight Clip'
        verbose_name_plural = 'Highlight Clips'
        ordering = ['display_order', '-created_at']
        indexes = [
            models.Index(fields=['user', 'display_order']),
            models.Index(fields=['platform']),
            models.Index(fields=['game']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    def clean(self):
        """Validate clip URL using url_validator service."""
        if not self.clip_url:
            raise ValidationError({'clip_url': 'Clip URL is required'})
        
        # Validate URL via service
        result = validate_highlight_url(self.clip_url)
        
        if not result['valid']:
            raise ValidationError({'clip_url': result.get('error', 'Invalid clip URL')})
        
        # Populate fields from validation result
        self.platform = result['platform']
        self.video_id = result['video_id']
        self.embed_url = result['embed_url']
        self.thumbnail_url = result.get('thumbnail_url') or None
    
    def save(self, *args, **kwargs):
        """Run validation before save."""
        self.full_clean()
        super().save(*args, **kwargs)


class PinnedHighlight(models.Model):
    """
    User's pinned highlight clip (shown prominently on profile).
    
    Rules:
    - ONE pinned clip per user (enforced via unique constraint)
    - Must reference an existing HighlightClip
    
    Design:
    - Separate model (not boolean on HighlightClip) for flexibility
    - Easy to query "get user's pinned clip"
    - Can add pin metadata (pinned_at, reason) without cluttering HighlightClip
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pinned_highlight',
        help_text="User who pinned this clip"
    )
    
    clip = models.ForeignKey(
        HighlightClip,
        on_delete=models.CASCADE,
        related_name='pinned_by',
        help_text="The highlighted clip being pinned"
    )
    
    pinned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this clip was pinned"
    )
    
    class Meta:
        db_table = 'user_profile_pinned_highlight'
        verbose_name = 'Pinned Highlight'
        verbose_name_plural = 'Pinned Highlights'
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.user.username} pinned: {self.clip.title}"
    
    def clean(self):
        """Validate that clip belongs to the user."""
        if self.clip and self.clip.user_id != self.user_id:
            raise ValidationError({
                'clip': 'Cannot pin a clip from another user'
            })
    
    def save(self, *args, **kwargs):
        """Run validation before save."""
        self.full_clean()
        super().save(*args, **kwargs)
