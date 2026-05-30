"""
Daily Reward Service — claim and status logic.

One claim per calendar day, per user.
Suspension check via ModerationSanction.
XP credited to UserProfile.xp.
DC credited to DeltaCrownWallet via DeltaCrownTransaction.
"""
from __future__ import annotations

import logging
from django.db import transaction, IntegrityError
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_platform_date():
    """
    Platform day starts at 06:00 Bangladesh Standard Time (UTC+6).
    BST 06:00 == UTC 00:00, so for a UTC server this is just today's UTC date.
    For non-UTC servers we convert explicitly.
    """
    import zoneinfo
    from datetime import timedelta
    BD_TZ = zoneinfo.ZoneInfo("Asia/Dhaka")
    now_bd = timezone.now().astimezone(BD_TZ)
    if now_bd.hour < 6:
        return (now_bd - timedelta(days=1)).date()
    return now_bd.date()


class AlreadyClaimed(Exception):
    pass


class UserSuspended(Exception):
    pass


class NoWallet(Exception):
    pass


class DailyRewardService:

    # ── Public API ────────────────────────────────────────────────────────

    @staticmethod
    def get_status(user: object) -> dict:
        """
        Return current reward status for a user — used by the dashboard
        widget and the GET /api/daily-reward/status/ endpoint.
        """
        from apps.economy.models import DailyLoginStreak, DailyRewardConfig
        from apps.user_profile.models import UserProfile

        try:
            from datetime import timedelta
            profile = UserProfile.objects.filter(user=user).first()
            streak = DailyLoginStreak.objects.filter(profile=profile).first() if profile else None
            config = DailyRewardConfig.get_active()

            current_streak = streak.current_streak if streak else 0
            platform_today = get_platform_date()
            today_claimable = (streak.last_claim_date != platform_today) if streak else True

            # Query actual claim records for this week
            days_since_thu = (platform_today.weekday() - 3) % 7
            week_start = platform_today - timedelta(days=days_since_thu)
            week_end = week_start + timedelta(days=7)
            claimed_dates: set = set(
                DailyRewardClaim.objects.filter(
                    user=user,
                    platform_date__gte=week_start,
                    platform_date__lt=week_end,
                ).values_list("platform_date", flat=True)
            )

            week = config.week_with_state(claimed_dates, platform_today)
            today_entry = config.get_day(_platform_day_index(platform_today))

            # Next milestone
            from apps.economy.models import DailyRewardMilestone
            next_milestone = (
                DailyRewardMilestone.objects.filter(
                    streak_days__gt=current_streak, is_active=True
                ).order_by("streak_days").values("streak_days", "bonus_xp", "bonus_dc", "label").first()
            )

            return {
                "today_claimable": today_claimable,
                "current_streak": current_streak,
                "best_streak": streak.best_streak if streak else 0,
                "today_xp": today_entry["xp"],
                "today_dc": today_entry["dc"],
                "week_schedule": week,
                "next_milestone": next_milestone,
            }
        except Exception:
            logger.exception("DailyRewardService.get_status failed for %s", user)
            return {"today_claimable": False, "current_streak": 0, "week_schedule": []}

    @staticmethod
    @transaction.atomic
    def claim(user: object) -> dict:
        """
        Claim today's daily reward.
        Returns: {xp_earned, dc_earned, streak, milestone}
        Raises: AlreadyClaimed, UserSuspended, NoWallet
        """
        from apps.economy.models import (
            DailyLoginStreak, DailyRewardConfig, DailyRewardMilestone, DailyRewardClaim,
            DeltaCrownWallet, DeltaCrownTransaction,
        )
        from apps.user_profile.models import UserProfile

        today = get_platform_date()

        # ── 1. User must be active and not banned/suspended ───────────────
        if not user.is_active:
            raise UserSuspended("Account is inactive.")
        if _is_suspended(user):
            raise UserSuspended("Account is currently suspended or banned.")

        # ── 2. Get or create streak record ───────────────────────────────
        profile = UserProfile.objects.select_for_update().filter(user=user).first()
        if not profile:
            raise ValueError("UserProfile not found.")

        streak, _ = DailyLoginStreak.objects.select_for_update().get_or_create(profile=profile)

        # ── 3. One claim per calendar day ────────────────────────────────
        if not streak.today_claimable:
            raise AlreadyClaimed("Already claimed today.")

        # ── 4. Load config and compute rewards ───────────────────────────
        config = DailyRewardConfig.get_active()
        day_index = _platform_day_index(today)
        day_entry = config.get_day(day_index)
        base_xp = day_entry["xp"]
        base_dc = day_entry["dc"]

        # ── 5. Advance streak (reset to 1 if gap ≥ 2 days) ───────────────
        if streak.streak_broken:
            streak.current_streak = 0
        streak.current_streak += 1
        streak.best_streak = max(streak.best_streak, streak.current_streak)
        streak.last_claim_date = today

        # ── 6. Milestone bonus ────────────────────────────────────────────
        milestone_obj = DailyRewardMilestone.for_streak(streak.current_streak)
        bonus_xp = milestone_obj.bonus_xp if milestone_obj else 0
        bonus_dc = milestone_obj.bonus_dc if milestone_obj else 0

        total_xp = base_xp + bonus_xp
        total_dc = base_dc + bonus_dc

        # ── 7. Credit XP to UserProfile ───────────────────────────────────
        profile.xp = (profile.xp or 0) + total_xp
        profile.save(update_fields=["xp"])
        streak.total_xp_earned += total_xp
        streak.total_claimed += total_dc
        streak.save(update_fields=[
            "current_streak", "best_streak", "last_claim_date",
            "total_xp_earned", "total_claimed",
        ])

        # ── 8. Credit DC to wallet (if any DC to give) ───────────────────
        new_balance = None
        if total_dc > 0:
            wallet = DeltaCrownWallet.objects.filter(profile=profile).first()
            if not wallet:
                raise NoWallet("User has no DeltaCoin wallet.")
            from django.db.models import F
            DeltaCrownWallet.objects.filter(pk=wallet.pk).update(
                cached_balance=F("cached_balance") + total_dc
            )
            DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=total_dc,
                reason=DeltaCrownTransaction.Reason.DAILY_REWARD,
                note=f"Day {streak.current_streak} login streak reward",
            )
            wallet.refresh_from_db()
            new_balance = int(wallet.cached_balance or 0)

        # ── 9. Immutable claim log ────────────────────────────────────────
        config_id = config.pk if config.pk else None
        try:
            DailyRewardClaim.objects.create(
                user=user,
                platform_date=today,
                streak_day=streak.current_streak,
                day_index=day_index,
                base_xp=base_xp,
                base_dc=base_dc,
                milestone_bonus_xp=bonus_xp,
                milestone_bonus_dc=bonus_dc,
                total_xp=total_xp,
                total_dc=total_dc,
                milestone=milestone_obj,
                config_id=config_id,
            )
        except IntegrityError:
            # Race condition — another request claimed in the same instant
            raise AlreadyClaimed("Claim already recorded for today.")

        result = {
            "xp_earned": total_xp,
            "dc_earned": total_dc,
            "streak": streak.current_streak,
            "balance": new_balance,
            "milestone": (
                {"label": milestone_obj.label, "bonus_xp": bonus_xp, "bonus_dc": bonus_dc}
                if milestone_obj else None
            ),
        }
        logger.info(
            "DailyReward claimed: user=%s streak=%d xp=%d dc=%d",
            user.username, streak.current_streak, total_xp, total_dc,
        )
        return result


# ── Helpers ───────────────────────────────────────────────────────────────

def _platform_day_index(date) -> int:
    """Thu=0, Fri=1, Sat=2, Sun=3, Mon=4, Tue=5, Wed=6."""
    return (date.weekday() - 3) % 7


def _is_suspended(user) -> bool:
    """Return True if the user has an active ban or suspend sanction."""
    try:
        from apps.moderation.models import ModerationSanction
        from django.db.models import Q
        now = timezone.now()
        return ModerationSanction.objects.filter(
            subject_profile__user=user,
            type__in=["ban", "suspend"],
            is_deleted=False,
            revoked_at__isnull=True,
            starts_at__lte=now,
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gt=now)
        ).exists()
    except Exception:
        return False
