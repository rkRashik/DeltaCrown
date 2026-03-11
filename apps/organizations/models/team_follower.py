"""
TeamFollower model — tracks users who follow a team.

Database Table: organizations_team_follower
"""

from django.conf import settings
from django.db import models


class TeamFollower(models.Model):
    """A user following a team for updates."""

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='followers',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='followed_teams',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organizations_team_follower'
        unique_together = ('team', 'user')
        indexes = [
            models.Index(fields=['team'], name='teamfollower_team_idx'),
            models.Index(fields=['user'], name='teamfollower_user_idx'),
        ]

    def __str__(self):
        return f'{self.user} → {self.team}'
