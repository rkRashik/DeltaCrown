"""
Team Announcements — Posts / Announcements / Updates visible to team members.
Part of the Community section in Team Manage HQ.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class TeamAnnouncement(models.Model):
    """A team post / announcement / update created by team managers."""

    TYPE_CHOICES = [
        ('general', 'General Update'),
        ('announcement', 'Announcement'),
        ('update', 'Update'),
        ('alert', 'Alert'),
        ('match_result', 'Match Result'),
        ('roster_change', 'Roster Change'),
    ]

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='announcements',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='team_announcements',
    )
    content = models.TextField(max_length=2000)
    announcement_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='update',
    )
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'organizations'
        db_table = 'organizations_team_announcement'
        ordering = ['-pinned', '-created_at']
        indexes = [
            models.Index(fields=['team', '-created_at'], name='ann_team_created_idx'),
        ]

    def __str__(self):
        return f"[{self.team.tag}] {self.announcement_type}: {self.content[:50]}"
