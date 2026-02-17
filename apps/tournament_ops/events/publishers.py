"""
Core EventBus publishing helpers for TournamentOps.

Bridges tournament_ops domain to the canonical apps.core.events EventBus,
which is where notification, leaderboard, and analytics handlers subscribe.

NOTE: Existing services (match_service, dispute_service, etc.) still publish
via common.events / apps.common.events EventBus — a separate singleton.
New code should use these helpers so events reach all cross-app handlers.

Usage:
    from apps.tournament_ops.events.publishers import publish_match_result_verified
    publish_match_result_verified(match_id=42, tournament_id=7, winner_id=100)
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_core_bus():
    """Lazy import of the canonical core EventBus singleton."""
    from apps.core.events import event_bus
    return event_bus


# ──────────────────────────────────────────────────────────────────────
#  Tournament lifecycle
# ──────────────────────────────────────────────────────────────────────

def publish_tournament_created(*, tournament_id: int, created_by: int, source: str = "tournament_ops"):
    """Publish tournament.created via core EventBus."""
    from apps.core.events.events import TournamentCreatedEvent
    try:
        _get_core_bus().publish(TournamentCreatedEvent(
            data={"tournament_id": tournament_id, "created_by": created_by},
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish tournament.created: %s", exc)


def publish_tournament_published(*, tournament_id: int, source: str = "tournament_ops"):
    """Publish tournament.published via core EventBus."""
    from apps.core.events.events import TournamentPublishedEvent
    try:
        _get_core_bus().publish(TournamentPublishedEvent(
            data={"tournament_id": tournament_id},
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish tournament.published: %s", exc)


def publish_tournament_started(*, tournament_id: int, source: str = "tournament_ops"):
    """Publish tournament.started via core EventBus."""
    from apps.core.events.events import TournamentStartedEvent
    try:
        _get_core_bus().publish(TournamentStartedEvent(
            data={"tournament_id": tournament_id},
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish tournament.started: %s", exc)


def publish_tournament_completed(
    *, tournament_id: int, winner_id: Optional[int] = None, source: str = "tournament_ops"
):
    """Publish tournament.completed via core EventBus."""
    from apps.core.events.events import TournamentCompletedEvent
    try:
        _get_core_bus().publish(TournamentCompletedEvent(
            data={"tournament_id": tournament_id, "winner_id": winner_id},
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish tournament.completed: %s", exc)


# ──────────────────────────────────────────────────────────────────────
#  Registration lifecycle
# ──────────────────────────────────────────────────────────────────────

def publish_registration_created(
    *, registration_id: int, tournament_id: int,
    team_id: Optional[int] = None, user_id: Optional[int] = None,
    source: str = "tournament_ops"
):
    """Publish registration.created via core EventBus."""
    from apps.core.events.events import RegistrationCreatedEvent
    try:
        _get_core_bus().publish(RegistrationCreatedEvent(
            data={
                "registration_id": registration_id,
                "tournament_id": tournament_id,
                "team_id": team_id,
                "user_id": user_id,
            },
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish registration.created: %s", exc)


def publish_registration_confirmed(
    *, registration_id: int, tournament_id: int,
    team_id: Optional[int] = None, user_id: Optional[int] = None,
    source: str = "tournament_ops"
):
    """Publish registration.confirmed via core EventBus."""
    from apps.core.events.events import RegistrationConfirmedEvent
    try:
        _get_core_bus().publish(RegistrationConfirmedEvent(
            data={
                "registration_id": registration_id,
                "tournament_id": tournament_id,
                "team_id": team_id,
                "user_id": user_id,
            },
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish registration.confirmed: %s", exc)


# ──────────────────────────────────────────────────────────────────────
#  Match lifecycle
# ──────────────────────────────────────────────────────────────────────

def publish_match_scheduled(*, match_id: int, tournament_id: int, source: str = "tournament_ops"):
    """Publish match.scheduled via core EventBus."""
    from apps.core.events.events import MatchScheduledEvent
    try:
        _get_core_bus().publish(MatchScheduledEvent(
            data={"match_id": match_id, "tournament_id": tournament_id},
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish match.scheduled: %s", exc)


def publish_match_completed(
    *, match_id: int, tournament_id: Optional[int] = None,
    winner_id: Optional[int] = None, source: str = "tournament_ops"
):
    """Publish match.completed via core EventBus."""
    from apps.core.events.events import MatchCompletedEvent
    try:
        _get_core_bus().publish(MatchCompletedEvent(
            data={
                "match_id": match_id,
                "tournament_id": tournament_id,
                "winner_id": winner_id,
            },
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish match.completed: %s", exc)


def publish_match_result_verified(
    *, match_id: int, tournament_id: int,
    winner_id: Optional[int] = None, source: str = "tournament_ops"
):
    """Publish match.result_verified via core EventBus."""
    from apps.core.events.events import MatchResultVerifiedEvent
    try:
        _get_core_bus().publish(MatchResultVerifiedEvent(
            data={
                "match_id": match_id,
                "tournament_id": tournament_id,
                "winner_id": winner_id,
            },
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish match.result_verified: %s", exc)


# ──────────────────────────────────────────────────────────────────────
#  Payment lifecycle
# ──────────────────────────────────────────────────────────────────────

def publish_payment_verified(
    *, payment_id: int, registration_id: int,
    amount: float = 0.0, source: str = "tournament_ops"
):
    """Publish payment.verified via core EventBus."""
    from apps.core.events.events import PaymentVerifiedEvent
    try:
        _get_core_bus().publish(PaymentVerifiedEvent(
            data={
                "payment_id": payment_id,
                "registration_id": registration_id,
                "amount": amount,
            },
            source=source,
        ))
    except Exception as exc:
        logger.error("Failed to publish payment.verified: %s", exc)
