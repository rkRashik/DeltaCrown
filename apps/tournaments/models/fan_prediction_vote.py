"""
Tournament fan prediction vote model.

Stores one vote per user per poll question for detail-page fan prediction widgets.
"""

from django.conf import settings
from django.db import models

from apps.common.models import TimestampedModel


class TournamentFanPredictionVote(TimestampedModel):
    """A single fan prediction vote for a poll question."""

    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='fan_prediction_votes',
        help_text='Tournament this vote belongs to.',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tournament_fan_prediction_votes',
        help_text='Viewer who submitted this prediction.',
    )
    poll_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text='Stable poll question identifier from widget config.',
    )
    option_id = models.CharField(
        max_length=64,
        help_text='Selected option identifier within the poll question.',
    )

    class Meta:
        db_table = 'tournaments_fan_prediction_vote'
        verbose_name = 'Tournament Fan Prediction Vote'
        verbose_name_plural = 'Tournament Fan Prediction Votes'
        unique_together = [('tournament', 'user', 'poll_id')]
        indexes = [
            models.Index(fields=['tournament', 'poll_id'], name='idx_fanvote_t_poll'),
            models.Index(fields=['tournament', 'poll_id', 'option_id'], name='idx_fanvote_t_poll_opt'),
        ]

    def __str__(self):
        return f'Vote(user={self.user_id}, tournament={self.tournament_id}, poll={self.poll_id}, option={self.option_id})'
