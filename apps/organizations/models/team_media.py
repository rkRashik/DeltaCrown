"""
Team Media — Gallery images, videos, and highlight reels.
Part of the Community & Media section in Team Manage HQ.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class TeamMedia(models.Model):
    """A gallery image or video uploaded by team staff."""

    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('match', 'Match Screenshot'),
        ('event', 'Event'),
        ('roster', 'Roster Photo'),
        ('meme', 'Meme / Fun'),
        ('artwork', 'Artwork'),
    ]

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='media_gallery',
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='team_media_uploads',
    )
    title = models.CharField(max_length=200, default='Untitled')
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default='general',
    )
    file = models.FileField(upload_to='teams/gallery/')
    file_url = models.URLField(max_length=500, blank=True, default='')
    file_type = models.CharField(
        max_length=20, blank=True, default='image',
        help_text='image or video',
    )
    file_size = models.PositiveIntegerField(default=0, help_text='Size in bytes')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'organizations'
        db_table = 'organizations_team_media'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at'], name='media_team_created_idx'),
        ]

    def __str__(self):
        return f"[{self.team.tag}] {self.title}"

    @property
    def url(self):
        if self.file:
            return self.file.url
        return self.file_url


class TeamHighlight(models.Model):
    """A highlight reel link (YouTube / Twitch clip) added by team staff."""

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='highlights',
    )
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='team_highlights_added',
    )
    title = models.CharField(max_length=200)
    url = models.URLField(max_length=500)
    description = models.TextField(max_length=500, blank=True, default='')
    thumbnail_url = models.URLField(max_length=500, blank=True, default='')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        app_label = 'organizations'
        db_table = 'organizations_team_highlight'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at'], name='highlight_team_created_idx'),
        ]

    def __str__(self):
        return f"[{self.team.tag}] {self.title}"
