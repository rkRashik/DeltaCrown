"""User daily login streak tracking (data only — business logic in DailyRewardService)."""
from datetime import timedelta

from django.db import models
from django.utils import timezone


class DailyLoginStreak(models.Model):
    """
    One row per UserProfile.
    Tracks the current streak, last claim date, and lifetime totals.
    Business logic lives in apps.economy.services.daily_reward_service.
    """
    profile = models.OneToOneField(
        "user_profile.UserProfile",
        on_delete=models.CASCADE,
        related_name="daily_streak",
    )
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    last_claim_date = models.DateField(null=True, blank=True)
    total_claimed = models.PositiveIntegerField(default=0, help_text="Lifetime DC earned via daily reward.")
    total_xp_earned = models.PositiveIntegerField(default=0, help_text="Lifetime XP earned via daily reward.")

    class Meta:
        verbose_name = "Daily Login Streak"

    def __str__(self):
        return f"{self.profile} — streak {self.current_streak}"

    @property
    def today_claimable(self) -> bool:
        """True if no claim has been recorded for today's platform date (6 AM BST start)."""
        if self.last_claim_date is None:
            return True
        from apps.economy.services.daily_reward_service import get_platform_date
        return self.last_claim_date < get_platform_date()

    @property
    def streak_broken(self) -> bool:
        """True if the last claim was ≥2 platform days ago (streak resets to 1 on next claim)."""
        if self.last_claim_date is None:
            return False
        from apps.economy.services.daily_reward_service import get_platform_date
        yesterday = get_platform_date() - timedelta(days=1)
        return self.last_claim_date < yesterday
