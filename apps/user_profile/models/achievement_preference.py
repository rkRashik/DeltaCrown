"""
UserAchievementPreference — per-user control over which tournament achievements
appear publicly and which are highlighted in the sidebar Trophy Cabinet.

Keyed by tournament registration ID (the actual source of achievement data).
"""

from django.db import models


class UserAchievementPreference(models.Model):
    user_profile = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='achievement_preferences',
    )
    # Source reference — tournament registration that produced this achievement
    registration_id = models.PositiveIntegerField(
        help_text="ID of the Tournament Registration that produced this achievement",
    )
    # Denormalised game slug for quick lookup without joins
    game_slug = models.CharField(max_length=50, blank=True, default='')

    is_hidden   = models.BooleanField(default=False, help_text="Hide from public profile")
    is_featured = models.BooleanField(default=False, help_text="Show in sidebar Trophy Cabinet")
    display_order = models.PositiveSmallIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_profile_user_achievement_preference'
        unique_together = [('user_profile', 'registration_id')]
        ordering = ['display_order', '-created_at']
        verbose_name = 'Achievement Preference'

    def __str__(self):
        status = 'hidden' if self.is_hidden else ('featured' if self.is_featured else 'normal')
        return f"{self.user_profile} — reg #{self.registration_id} [{status}]"
