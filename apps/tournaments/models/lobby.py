"""
Tournament Lobby & Check-In Models

Source Documents:
- Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md (Section 2.1: FE-T-007)
- Documents/Planning/PART_4.3_CHECK_IN_FLOW.md

Models:
- TournamentLobby: Central hub for participants before tournament starts
- CheckIn: Tracks participant check-in status
- LobbyAnnouncement: Real-time announcements to participants

Purpose:
- Provide participant hub with check-in countdown
- Track who has checked in vs who hasn't
- Display roster with check-in status
- Show organizer announcements
"""

from django.db import models
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Q, CheckConstraint
from datetime import timedelta

from apps.common.models import TimestampedModel


class TournamentLobby(TimestampedModel):
    """
    Central hub/lobby for tournament participants.
    
    Displayed to registered participants in pre-tournament phase.
    Shows check-in countdown, roster, announcements, and brackets.
    """
    
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='lobby',
        verbose_name=_('Tournament')
    )
    
    check_in_opens_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Check-In Opens At'),
        help_text=_('When check-in becomes available')
    )
    
    check_in_closes_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Check-In Closes At'),
        help_text=_('Check-in deadline (typically tournament start time)')
    )
    
    check_in_required = models.BooleanField(
        default=True,
        verbose_name=_('Check-In Required'),
        help_text=_('Whether participants must check in to compete')
    )
    
    auto_forfeit_no_show = models.BooleanField(
        default=True,
        verbose_name=_('Auto-Forfeit No-Shows'),
        help_text=_('Automatically forfeit participants who don\'t check in')
    )
    
    lobby_message = models.TextField(
        blank=True,
        verbose_name=_('Lobby Message'),
        help_text=_('Welcome message shown to participants in lobby')
    )
    
    bracket_visibility = models.CharField(
        max_length=20,
        choices=[
            ('hidden', _('Hidden')),
            ('seeded_only', _('Seeded Only')),
            ('full', _('Full Bracket')),
        ],
        default='seeded_only',
        verbose_name=_('Bracket Visibility'),
        help_text=_('What participants can see before tournament starts')
    )
    
    roster_visibility = models.CharField(
        max_length=20,
        choices=[
            ('hidden', _('Hidden')),
            ('count_only', _('Count Only')),
            ('full', _('Full Roster')),
        ],
        default='full',
        verbose_name=_('Roster Visibility'),
        help_text=_('Whether participants can see full roster')
    )
    
    rules_url = models.URLField(
        blank=True,
        verbose_name=_('Rules URL'),
        help_text=_('Link to detailed rules document')
    )
    
    discord_server_url = models.URLField(
        blank=True,
        verbose_name=_('Discord Server'),
        help_text=_('Optional Discord server for communication')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active'),
        help_text=_('Whether lobby is currently accessible')
    )
    
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Lobby Configuration'),
        help_text=_('Additional lobby settings')
    )
    
    # Example config:
    # {
    #     "announcement_refresh_seconds": 30,
    #     "roster_refresh_seconds": 10,
    #     "check_in_reminder_minutes": [60, 30, 15, 5],
    #     "show_seed_assignments": true,
    #     "show_match_schedule": false
    # }
    
    class Meta:
        db_table = 'tournament_lobbies'
        verbose_name = _('Tournament Lobby')
        verbose_name_plural = _('Tournament Lobbies')
    
    def __str__(self):
        return f"Lobby: {self.tournament.name}"
    
    @property
    def is_check_in_open(self):
        """Check if check-in is currently open."""
        if not self.check_in_required:
            return False
        
        now = timezone.now()
        
        if self.check_in_opens_at and now < self.check_in_opens_at:
            return False
        
        if self.check_in_closes_at and now > self.check_in_closes_at:
            return False
        
        return True
    
    @property
    def check_in_status(self):
        """Get human-readable check-in status."""
        if not self.check_in_required:
            return 'not_required'
        
        now = timezone.now()
        
        if self.check_in_opens_at and now < self.check_in_opens_at:
            return 'not_open'
        
        if self.check_in_closes_at and now > self.check_in_closes_at:
            return 'closed'
        
        return 'open'
    
    @property
    def check_in_countdown_seconds(self):
        """Get seconds until check-in closes."""
        if not self.check_in_closes_at:
            return None
        
        now = timezone.now()
        if now > self.check_in_closes_at:
            return 0
        
        delta = self.check_in_closes_at - now
        return int(delta.total_seconds())
    
    def get_checked_in_count(self):
        """Get count of participants who have checked in."""
        return CheckIn.objects.filter(
            tournament=self.tournament,
            is_checked_in=True,
            is_deleted=False
        ).count()
    
    def get_total_participants_count(self):
        """Get total registered participant count."""
        return self.tournament.registrations.filter(
            status='confirmed',
            is_deleted=False
        ).count()


class CheckIn(TimestampedModel):
    """
    Tracks participant check-in status.
    
    Participants must check in before tournament starts to confirm attendance.
    No-shows can be automatically forfeited.
    """
    
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='check_ins',
        verbose_name=_('Tournament')
    )
    
    registration = models.OneToOneField(
        'tournaments.Registration',
        on_delete=models.CASCADE,
        related_name='check_in',
        verbose_name=_('Registration')
    )
    
    # Either user OR team (matches registration)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='tournament_check_ins',
        verbose_name=_('User')
    )
    
    team_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        db_column='team_id',
        verbose_name=_('Team ID')
    )
    
    is_checked_in = models.BooleanField(
        default=False,
        verbose_name=_('Is Checked In'),
        help_text=_('Whether participant has checked in')
    )
    
    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Checked In At'),
        help_text=_('Timestamp of check-in')
    )
    
    checked_in_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Checked In By'),
        help_text=_('User who performed check-in (may be captain for teams)')
    )
    
    is_forfeited = models.BooleanField(
        default=False,
        verbose_name=_('Is Forfeited'),
        help_text=_('Whether participant was forfeited for not checking in')
    )
    
    forfeited_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Forfeited At')
    )
    
    forfeit_reason = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Forfeit Reason'),
        help_text=_('Why participant was forfeited')
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notes'),
        help_text=_('Admin notes about check-in')
    )
    
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('Is Deleted')
    )
    
    class Meta:
        db_table = 'tournament_check_ins'
        verbose_name = _('Check-In')
        verbose_name_plural = _('Check-Ins')
        indexes = [
            models.Index(fields=['tournament', 'is_checked_in']),
            models.Index(fields=['tournament', 'is_forfeited']),
            models.Index(fields=['registration']),
            models.Index(fields=['user', 'tournament']),
            models.Index(fields=['team_id', 'tournament']),
        ]
        constraints = [
            CheckConstraint(
                check=(Q(user__isnull=False) & Q(team_id__isnull=True)) | 
                      (Q(user__isnull=True) & Q(team_id__isnull=False)),
                name='check_in_user_or_team_xor'
            ),
        ]
    
    def __str__(self):
        participant = self.team.name if self.team else self.user.username
        status = "✓" if self.is_checked_in else "✗"
        return f"{self.tournament.name} - {participant} {status}"
    
    @property
    def participant_name(self):
        """Get participant display name."""
        return self.team.name if self.team else self.user.username
    
    def perform_check_in(self, user):
        """Mark participant as checked in."""
        self.is_checked_in = True
        self.checked_in_at = timezone.now()
        self.checked_in_by = user
        self.save()
    
    def perform_forfeit(self, reason='Did not check in'):
        """Mark participant as forfeited."""
        self.is_forfeited = True
        self.forfeited_at = timezone.now()
        self.forfeit_reason = reason
        
        # Also update registration status
        if self.registration:
            self.registration.status = 'forfeited'
            self.registration.save()
        
        self.save()


class LobbyAnnouncement(TimestampedModel):
    """
    Real-time announcements shown to participants in lobby.
    
    Organizers can post updates, reminders, and important info.
    """
    
    lobby = models.ForeignKey(
        TournamentLobby,
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name=_('Lobby')
    )
    
    posted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='+',
        verbose_name=_('Posted By')
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )
    
    message = models.TextField(
        verbose_name=_('Message')
    )
    
    announcement_type = models.CharField(
        max_length=20,
        choices=[
            ('info', _('Information')),
            ('warning', _('Warning')),
            ('urgent', _('Urgent')),
            ('success', _('Success')),
        ],
        default='info',
        verbose_name=_('Type')
    )
    
    is_pinned = models.BooleanField(
        default=False,
        verbose_name=_('Is Pinned'),
        help_text=_('Pinned announcements appear at top')
    )
    
    display_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Display Until'),
        help_text=_('Auto-hide after this time (optional)')
    )
    
    is_visible = models.BooleanField(
        default=True,
        verbose_name=_('Is Visible')
    )
    
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('Is Deleted')
    )
    
    class Meta:
        db_table = 'tournament_lobby_announcements'
        verbose_name = _('Lobby Announcement')
        verbose_name_plural = _('Lobby Announcements')
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['lobby', 'is_visible', 'is_deleted']),
            models.Index(fields=['lobby', '-is_pinned', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.lobby.tournament.name} - {self.title}"
    
    @property
    def is_expired(self):
        """Check if announcement should be hidden."""
        if not self.display_until:
            return False
        return timezone.now() > self.display_until
