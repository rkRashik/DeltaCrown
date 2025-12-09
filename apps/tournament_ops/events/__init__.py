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

__all__ = [
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
]
