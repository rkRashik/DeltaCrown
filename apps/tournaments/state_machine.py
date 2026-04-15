"""Canonical match state-transition validation.

P0 scope note:
- This validator focuses on correctness and race-condition safety.
- It preserves current product behavior paths used by existing MatchService
  organizer/admin operations to avoid broad policy changes in this phase.
"""

from __future__ import annotations

from typing import Dict, FrozenSet

from django.core.exceptions import ValidationError

from apps.tournaments.models import Match


MATCH_TRANSITIONS: Dict[str, FrozenSet[str]] = {
    # Core lifecycle + existing organizer completion/cancel pathways.
    Match.SCHEDULED: frozenset({
        Match.CHECK_IN,
        Match.READY,
        Match.FORFEIT,
        Match.CANCELLED,
        Match.COMPLETED,
    }),
    Match.CHECK_IN: frozenset({
        Match.CHECK_IN,
        Match.READY,
        Match.FORFEIT,
        Match.CANCELLED,
        Match.COMPLETED,
    }),
    Match.READY: frozenset({
        Match.LIVE,
        Match.FORFEIT,
        Match.CANCELLED,
        Match.COMPLETED,
    }),
    Match.LIVE: frozenset({
        Match.PENDING_RESULT,
        Match.FORFEIT,
        Match.CANCELLED,
        Match.COMPLETED,
    }),
    Match.PENDING_RESULT: frozenset({
        Match.PENDING_RESULT,
        Match.COMPLETED,
        Match.DISPUTED,
        Match.FORFEIT,
        Match.CANCELLED,
    }),
    Match.DISPUTED: frozenset({
        Match.PENDING_RESULT,
        Match.COMPLETED,
        Match.FORFEIT,
        Match.CANCELLED,
    }),
    Match.FORFEIT: frozenset({
        Match.CANCELLED,
        Match.COMPLETED,
    }),
    Match.CANCELLED: frozenset({
        Match.COMPLETED,
    }),
    Match.COMPLETED: frozenset({
        Match.DISPUTED,
    }),
}


def validate_state_transition(current_state: str, new_state: str) -> str:
    """Validate a match transition and return normalized new state.

    Raises ValidationError when transition is not allowed.
    """
    current = str(current_state or "").strip().lower()
    target = str(new_state or "").strip().lower()

    if not current:
        raise ValidationError("Cannot validate transition from empty match state")
    if not target:
        raise ValidationError("Cannot transition to empty match state")

    if current == target:
        return target

    allowed = MATCH_TRANSITIONS.get(current, frozenset())
    if target not in allowed:
        raise ValidationError(f"Invalid match state transition: {current} -> {target}")

    return target


def validate_transition(match: Match, new_state: str) -> str:
    """Validate state transition for a Match instance."""
    return validate_state_transition(getattr(match, "state", ""), new_state)
