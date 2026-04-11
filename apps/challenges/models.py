"""
Challenge Hub Models  (DEPRECATED — compatibility shim)

The canonical Challenge model now lives at apps.competition.models.Challenge.
This module preserves the legacy DB table for migration continuity and
re-exports the Competition Challenge as ``CompetitionChallenge`` for new code.

All **new** features should target ``apps.competition.models.Challenge``.
"""
import warnings

from django.db import models
from django.conf import settings
from django.utils import timezone

# Re-export the canonical model so callers can migrate gradually.
try:
    from apps.competition.models.challenge import (  # noqa: F401
        Challenge as CompetitionChallenge,
    )
except ImportError:
    CompetitionChallenge = None  # competition app might not be installed


class Challenge(models.Model):
    """
    DEPRECATED — Legacy challenge issued by or to a team.

    Prefer ``apps.competition.models.Challenge`` for all new code.
    This model is kept for backward-compatible reads on the existing
    ``challenges_challenge`` DB table.
    """

    class ChallengeType(models.TextChoices):
        WAGER = 'wager', 'Wager Match'
        BOUNTY = 'bounty', 'Community Bounty'
        SCRIM = 'scrim', 'Scrim Challenge'
        DUEL = 'duel', '1v1 Duel'

    class ChallengeStatus(models.TextChoices):
        OPEN = 'open', 'Open'
        ACCEPTED = 'accepted', 'Accepted'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    # Issuing team
    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='challenges_issued',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='challenges_created',
    )

    # Challenge details
    title = models.CharField(max_length=120)
    description = models.TextField(max_length=500, blank=True, default='')
    challenge_type = models.CharField(
        max_length=20,
        choices=ChallengeType.choices,
        default=ChallengeType.WAGER,
    )
    status = models.CharField(
        max_length=20,
        choices=ChallengeStatus.choices,
        default=ChallengeStatus.OPEN,
    )

    # Match configuration
    format = models.CharField(max_length=30, default='BO3', help_text='e.g. BO1, BO3, BO5, 1v1')
    match_type = models.CharField(max_length=50, blank=True, default='', help_text='e.g. Scrim, Aim Duel, Ranked')

    # Prize / reward
    prize_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prize_currency = models.CharField(max_length=10, default='USD', help_text='USD or CP (Crown Points)')
    prize_description = models.CharField(max_length=200, blank=True, default='')

    # Opponent (accepted by)
    opponent_team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='challenges_accepted',
    )

    # For bounty/duel: specific player target
    target_player = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='bounties_targeted',
    )
    target_player_name = models.CharField(max_length=100, blank=True, default='')

    # Stats
    attempts = models.PositiveIntegerField(default=0)
    wins_by_challenger = models.PositiveIntegerField(default=0)

    # Timing
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'challenges'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', 'status']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_challenge_type_display()}) — {self.get_status_display()}"

    def save(self, *args, **kwargs):
        warnings.warn(
            "Writing to challenges.Challenge is deprecated — "
            "use apps.competition.models.Challenge instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    @property
    def time_remaining(self):
        if self.expires_at:
            delta = self.expires_at - timezone.now()
            if delta.total_seconds() > 0:
                return delta
        return None
