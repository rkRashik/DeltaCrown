"""
Daily Reward system models.

Three tables:
  DailyRewardConfig    — singleton admin-controlled schedule (XP + DC per day, milestones)
  DailyRewardMilestone — streak milestone bonuses
  DailyRewardClaim     — immutable audit log; unique per (user, platform_date)
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone

# Platform week: Thu=0, Fri=1, Sat=2, Sun=3, Mon=4, Tue=5, Wed=6
# Python weekday(): Mon=0 … Sun=6 → platform_day = (weekday - 3) % 7
_DEFAULT_SCHEDULE = [
    {"day": "Thu", "xp": 25,  "dc": 0},
    {"day": "Fri", "xp": 30,  "dc": 0},
    {"day": "Sat", "xp": 40,  "dc": 2},
    {"day": "Sun", "xp": 50,  "dc": 0},
    {"day": "Mon", "xp": 60,  "dc": 3},
    {"day": "Tue", "xp": 75,  "dc": 0},
    {"day": "Wed", "xp": 100, "dc": 10},
]

_DEFAULT_MILESTONES = [
    {"days": 7,   "xp": 100,  "dc": 10,  "label": "1-Week Warrior"},
    {"days": 14,  "xp": 200,  "dc": 20,  "label": "Fortnight Grinder"},
    {"days": 30,  "xp": 500,  "dc": 50,  "label": "Monthly Legend"},
    {"days": 60,  "xp": 1000, "dc": 100, "label": "Two-Month Elite"},
    {"days": 100, "xp": 2000, "dc": 200, "label": "Century Crown"},
    {"days": 365, "xp": 5000, "dc": 500, "label": "Eternal Champion"},
]


def _platform_day_index(date) -> int:
    """Thu=0, Fri=1, Sat=2, Sun=3, Mon=4, Tue=5, Wed=6."""
    return (date.weekday() - 3) % 7


class DailyRewardConfig(models.Model):
    """
    Singleton config for the daily reward schedule.
    Only one row should be active at a time (enforced in admin clean).
    week_schedule: list of 7 dicts [{day, xp, dc}] indexed Thu=0 … Wed=6.
    """
    name = models.CharField(max_length=100, default="Default")
    is_active = models.BooleanField(default=True, db_index=True)
    week_schedule = models.JSONField(
        default=list,
        help_text="7-element list [{day, xp, dc}] — Thu=0 through Wed=6.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Daily Reward Config"
        verbose_name_plural = "Daily Reward Configs"

    def __str__(self):
        status = "ACTIVE" if self.is_active else "inactive"
        return f"{self.name} [{status}]"

    @classmethod
    def get_active(cls) -> "DailyRewardConfig":
        row = cls.objects.filter(is_active=True).first()
        if row:
            return row
        dummy = cls(name="Default (fallback)")
        dummy.week_schedule = _DEFAULT_SCHEDULE
        return dummy

    def get_day(self, platform_day_index: int) -> dict:
        """Return {xp, dc} for a given day index (0=Thu…6=Wed)."""
        schedule = self.week_schedule
        if isinstance(schedule, list) and 0 <= platform_day_index < len(schedule):
            entry = schedule[platform_day_index]
            return {"xp": int(entry.get("xp", 0)), "dc": int(entry.get("dc", 0))}
        return {"xp": 25, "dc": 0}

    def week_with_state(self, claimed_dates: set, platform_today=None) -> list[dict]:
        """
        Return 7-day schedule dicts with accurate per-day state.

        claimed_dates: set of date objects for days actually claimed this week
                       (queried from DailyRewardClaim records).
        States (mutually exclusive, priority order):
          claimed → user claimed this day
          is_today → today (claimable or already claimed)
          missed → past day with no claim (can no longer be claimed)
          locked → future day
        """
        from datetime import timedelta
        if platform_today is None:
            platform_today = timezone.now().date()

        days_since_thu = (platform_today.weekday() - 3) % 7
        this_thursday = platform_today - timedelta(days=days_since_thu)
        schedule = self.week_schedule if isinstance(self.week_schedule, list) else _DEFAULT_SCHEDULE

        result = []
        for i, entry in enumerate(schedule):
            d = this_thursday + timedelta(days=i)
            is_claimed = d in claimed_dates
            is_today = d == platform_today
            is_past = d < platform_today
            result.append({
                "day": entry.get("day", ""),
                "xp": int(entry.get("xp", 0)),
                "dc": int(entry.get("dc", 0)),
                "claimed": is_claimed,
                "is_today": is_today,
                "missed": is_past and not is_claimed,
                "locked": d > platform_today,
            })
        return result


class DailyRewardMilestone(models.Model):
    """Bonus awarded when current_streak reaches streak_days."""
    streak_days = models.PositiveIntegerField(unique=True, db_index=True)
    bonus_xp = models.PositiveIntegerField(default=0)
    bonus_dc = models.PositiveIntegerField(default=0)
    label = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Daily Reward Milestone"
        verbose_name_plural = "Daily Reward Milestones"
        ordering = ["streak_days"]

    def __str__(self):
        return f"{self.label} ({self.streak_days}d) +{self.bonus_xp}XP +{self.bonus_dc}DC"

    @classmethod
    def for_streak(cls, streak_day: int) -> "DailyRewardMilestone | None":
        """Return active milestone for this exact streak_day, or None."""
        return cls.objects.filter(streak_days=streak_day, is_active=True).first()


class DailyRewardClaim(models.Model):
    """
    Immutable claim log. Never delete rows.
    Unique on (user, platform_date) enforces one claim per calendar day.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="daily_reward_claims",
        db_index=True,
    )
    claimed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    platform_date = models.DateField(db_index=True, help_text="Calendar date (server TZ) of this claim.")
    streak_day = models.PositiveIntegerField(help_text="User's streak count at time of claim.")
    day_index = models.SmallIntegerField(help_text="Platform day index 0=Thu…6=Wed.")
    base_xp = models.PositiveIntegerField(default=0)
    base_dc = models.PositiveIntegerField(default=0)
    milestone_bonus_xp = models.PositiveIntegerField(default=0)
    milestone_bonus_dc = models.PositiveIntegerField(default=0)
    total_xp = models.PositiveIntegerField()
    total_dc = models.PositiveIntegerField()
    milestone = models.ForeignKey(
        DailyRewardMilestone, null=True, blank=True, on_delete=models.SET_NULL,
    )
    config = models.ForeignKey(
        DailyRewardConfig, null=True, blank=True, on_delete=models.SET_NULL,
    )

    class Meta:
        verbose_name = "Daily Reward Claim"
        verbose_name_plural = "Daily Reward Claims"
        unique_together = [("user", "platform_date")]
        ordering = ["-claimed_at"]

    def __str__(self):
        return f"{self.user.username} · {self.platform_date} · +{self.total_xp}XP +{self.total_dc}DC"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("DailyRewardClaim is immutable — do not update existing rows.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("DailyRewardClaim rows must not be deleted.")
