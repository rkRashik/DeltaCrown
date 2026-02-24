"""
Domain Events for TournamentOps.

Events published by services to enable event-driven integration.
"""

from .match_ops_events import (
    MatchWentLiveEvent,
    MatchPausedEvent,
    MatchResumedEvent,
    MatchForceCompletedEvent,
    MatchOperatorNoteAddedEvent,
    MatchResultOverriddenEvent,
)
from .staffing_events import (
    StaffAssignedToTournamentEvent,
    StaffRemovedFromTournamentEvent,
    RefereeAssignedToMatchEvent,
    RefereeUnassignedFromMatchEvent,
)
from .scheduling_events import (
    MatchScheduledManuallyEvent,
    MatchRescheduledEvent,
    BulkMatchesShiftedEvent,
)
from .publishers import (
    publish_tournament_created,
    publish_tournament_published,
    publish_tournament_started,
    publish_tournament_completed,
    publish_registration_created,
    publish_registration_confirmed,
    publish_match_scheduled,
    publish_match_completed,
    publish_match_result_verified,
    publish_payment_verified,
)

__all__ = [
    # Domain events (DTOBase)
    "MatchWentLiveEvent",
    "MatchPausedEvent",
    "MatchResumedEvent",
    "MatchForceCompletedEvent",
    "MatchOperatorNoteAddedEvent",
    "MatchResultOverriddenEvent",
    "StaffAssignedToTournamentEvent",
    "StaffRemovedFromTournamentEvent",
    "RefereeAssignedToMatchEvent",
    "RefereeUnassignedFromMatchEvent",
    "MatchScheduledManuallyEvent",
    "MatchRescheduledEvent",
    "BulkMatchesShiftedEvent",
    # Core EventBus publishers
    "publish_tournament_created",
    "publish_tournament_published",
    "publish_tournament_started",
    "publish_tournament_completed",
    "publish_registration_created",
    "publish_registration_confirmed",
    "publish_match_scheduled",
    "publish_match_completed",
    "publish_match_result_verified",
    "publish_payment_verified",
]
