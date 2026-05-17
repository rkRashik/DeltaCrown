"""
Celery tasks for Riot API Game Passport verification (P7-B).

verify_game_passport_task   — verify a single passport by ID
retry_pending_riot_passports_task — bulk-retry passports stuck in non-VERIFIED states
"""
from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger("games.riot_tasks")


@shared_task(
    bind=True,
    name="games.verify_game_passport",
    max_retries=2,
    default_retry_delay=60,
    ignore_result=True,
)
def verify_game_passport_task(self, passport_id: int, *, force: bool = False) -> None:
    """
    Verify a single GameProfile (passport) against the Riot Account API.

    Parameters
    ----------
    passport_id : int
        Primary key of the GameProfile to verify.
    force : bool
        If True, re-verify even if already VERIFIED (used by admin retry action).
    """
    from apps.user_profile.models_main import GameProfile
    from apps.games.services.riot_verification_service import (
        apply_verification_result,
        is_valorant_passport,
        parse_riot_id,
        verify_riot_id,
    )

    try:
        passport = GameProfile.objects.select_related("game").get(pk=passport_id)
    except GameProfile.DoesNotExist:
        logger.warning("verify_game_passport_task: passport_id=%s not found", passport_id)
        return

    # Skip already-verified unless forced.
    if not force and passport.verification_status == GameProfile.VERIFICATION_VERIFIED:
        logger.debug("verify_game_passport_task: passport_id=%s already VERIFIED — skip", passport_id)
        return

    game_slug = getattr(passport.game, "slug", "") if passport.game else ""
    if not is_valorant_passport(game_slug):
        logger.debug("verify_game_passport_task: passport_id=%s game=%s not Valorant — skip", passport_id, game_slug)
        return

    raw_id = f"{passport.ign or ''}#{passport.discriminator or ''}".strip("#")
    game_name, tag_line = parse_riot_id(raw_id)
    if not game_name or not tag_line:
        logger.warning(
            "verify_game_passport_task: passport_id=%s has unparseable Riot ID %r", passport_id, raw_id
        )
        return

    result = verify_riot_id(game_name, tag_line)
    apply_verification_result(passport, result)

    logger.info(
        "verify_game_passport_task: passport_id=%s status=%s", passport_id, result["status"]
    )


@shared_task(
    name="games.retry_pending_riot_passports",
    ignore_result=True,
)
def retry_pending_riot_passports_task() -> None:
    """
    Bulk-retry Valorant passports that are not yet VERIFIED.
    Designed to be triggered manually (admin action) or scheduled after
    a RIOT_API_KEY rotation. Skips already-verified passports.

    Enqueues individual verify_game_passport_task per passport to avoid
    holding a single long-running task and to respect Celery rate limits.
    """
    from apps.user_profile.models_main import GameProfile

    # Only retry passports where verification hasn't succeeded yet.
    retryable_statuses = [
        GameProfile.VERIFICATION_PENDING,
        GameProfile.VERIFICATION_API_UNAVAILABLE,
        GameProfile.VERIFICATION_RATE_LIMITED,
        GameProfile.VERIFICATION_FAILED,  # also retry failures in case of data-entry correction
    ]

    qs = GameProfile.objects.filter(
        verification_status__in=retryable_statuses,
        game__slug__in=["valorant", "val"],
    ).values_list("id", flat=True)

    count = 0
    for pid in qs.iterator():
        verify_game_passport_task.delay(pid)
        count += 1

    logger.info("retry_pending_riot_passports_task: enqueued %d passports for re-verification", count)
