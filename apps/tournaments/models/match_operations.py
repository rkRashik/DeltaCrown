"""
Sprint 6 Models — Match Operations Extensions.

S6-M1: RescheduleRequest
S6-M2: MatchMedia
S6-M3: BroadcastStation
S6-M4: MatchServerSelection

PRD: §6.4, §6.8–§6.10
"""

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class RescheduleRequest(models.Model):
    """S6-M1: Organizer/participant reschedule request for a match (§6.4)."""

    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (APPROVED, _('Approved')),
        (REJECTED, _('Rejected')),
        (CANCELLED, _('Cancelled')),
    ]

    SIDE_P1 = 1
    SIDE_P2 = 2
    SIDE_CHOICES = [
        (SIDE_P1, _('Participant 1')),
        (SIDE_P2, _('Participant 2')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='reschedule_requests',
    )
    requested_by_id = models.PositiveIntegerField(
        help_text=_('User ID who requested the reschedule'),
    )
    proposer_side = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        choices=SIDE_CHOICES,
        help_text=_('Which side (participant1/participant2) initiated the proposal'),
    )
    old_time = models.DateTimeField(null=True, blank=True)
    new_time = models.DateTimeField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING, db_index=True)
    reviewed_by_id = models.PositiveIntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    response_note = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'toc_reschedule_request'
        ordering = ['-created_at']

    def __str__(self):
        return f"Reschedule {self.match_id} → {self.new_time}"


class MatchMedia(models.Model):
    """S6-M2: Media / evidence attached to a match (§6.9)."""

    SCREENSHOT = 'screenshot'
    VIDEO = 'video'
    REPLAY = 'replay'
    OTHER = 'other'

    TYPE_CHOICES = [
        (SCREENSHOT, _('Screenshot')),
        (VIDEO, _('Video')),
        (REPLAY, _('Replay')),
        (OTHER, _('Other')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='media',
    )
    uploaded_by_id = models.PositiveIntegerField()
    media_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=SCREENSHOT)
    file = models.FileField(upload_to='match_media/', blank=True, null=True)
    url = models.URLField(max_length=500, blank=True)
    description = models.CharField(max_length=500, blank=True)
    is_evidence = models.BooleanField(default=False, help_text=_('Flagged as dispute evidence'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'toc_match_media'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_media_type_display()} — Match {self.match_id}"


class BroadcastStation(models.Model):
    """S6-M3: Broadcast/stream station that matches can be assigned to (§6.10)."""

    IDLE = 'idle'
    LIVE = 'live'
    OFFLINE = 'offline'

    STATUS_CHOICES = [
        (IDLE, _('Idle')),
        (LIVE, _('Live')),
        (OFFLINE, _('Offline')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='broadcast_stations',
    )
    name = models.CharField(max_length=200)
    stream_url = models.URLField(max_length=500, blank=True)
    assigned_match = models.ForeignKey(
        'tournaments.Match',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='broadcast_station',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=IDLE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'toc_broadcast_station'
        ordering = ['name']

    def __str__(self):
        return self.name


class MatchServerSelection(models.Model):
    """S6-M4: Server selection for a match (§6.8)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.OneToOneField(
        'tournaments.Match',
        on_delete=models.CASCADE,
        related_name='server_selection',
    )
    region = models.CharField(max_length=50)
    server_ip = models.GenericIPAddressField(null=True, blank=True)
    server_name = models.CharField(max_length=200, blank=True)
    selected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'toc_match_server_selection'

    def __str__(self):
        return f"{self.region} — Match {self.match_id}"


class MatchCenterConfig(models.Model):
    """Public Match Center presentation controls authored from TOC."""

    THEME_CYBER = 'cyber'
    THEME_TACTICAL = 'tactical'
    THEME_ARENA = 'arena'

    THEME_CHOICES = [
        (THEME_CYBER, _('Cyber')),
        (THEME_TACTICAL, _('Tactical')),
        (THEME_ARENA, _('Arena')),
    ]

    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='match_center_config',
    )
    enabled = models.BooleanField(default=True)
    show_timeline = models.BooleanField(default=True)
    show_media = models.BooleanField(default=True)
    show_stats = models.BooleanField(default=True)
    show_fan_pulse = models.BooleanField(default=True)
    theme = models.CharField(max_length=24, choices=THEME_CHOICES, default=THEME_CYBER)
    poll_question = models.CharField(max_length=180, default='Who takes the series?')
    poll_option_a = models.CharField(max_length=80, default='Team A')
    poll_option_b = models.CharField(max_length=80, default='Team B')
    auto_refresh_seconds = models.PositiveSmallIntegerField(
        default=20,
        validators=[MinValueValidator(10), MaxValueValidator(120)],
    )
    match_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Per-match overrides keyed by match id as string.'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'toc_match_center_config'
        verbose_name = 'Match Center Configuration'
        verbose_name_plural = 'Match Center Configurations'

    def __str__(self):
        return f"Match Center Config - {self.tournament_id}"
