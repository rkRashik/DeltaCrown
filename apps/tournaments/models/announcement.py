"""
Tournament Announcement Model

Allows organizers to broadcast important updates to tournament participants.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

User = get_user_model()


class TournamentAnnouncement(models.Model):
    """
    Tournament announcements for broadcasting updates to participants.
    """
    
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name=_('Tournament')
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )
    
    message = models.TextField(
        verbose_name=_('Message')
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tournament_announcements_created',
        verbose_name=_('Created By')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created At')
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated At')
    )
    
    is_pinned = models.BooleanField(
        default=False,
        verbose_name=_('Pinned'),
        help_text=_('Pinned announcements appear at the top')
    )
    
    is_important = models.BooleanField(
        default=False,
        verbose_name=_('Important'),
        help_text=_('Important announcements are highlighted')
    )
    
    class Meta:
        db_table = 'tournament_announcements'
        verbose_name = _('Tournament Announcement')
        verbose_name_plural = _('Tournament Announcements')
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['tournament', '-created_at']),
            models.Index(fields=['is_pinned', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.tournament.name} - {self.title}"
