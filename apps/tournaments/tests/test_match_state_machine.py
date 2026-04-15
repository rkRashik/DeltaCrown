from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from apps.tournaments.models import Match
from apps.tournaments.state_machine import validate_state_transition, validate_transition


def test_validate_state_transition_allows_core_path():
    target = validate_state_transition(Match.SCHEDULED, Match.CHECK_IN)
    assert target == Match.CHECK_IN


def test_validate_transition_allows_noop_state_assignment():
    match = SimpleNamespace(state=Match.CHECK_IN)
    target = validate_transition(match, Match.CHECK_IN)
    assert target == Match.CHECK_IN


def test_validate_state_transition_allows_result_submission_path():
    assert validate_state_transition(Match.LIVE, Match.PENDING_RESULT) == Match.PENDING_RESULT
    assert validate_state_transition(Match.PENDING_RESULT, Match.COMPLETED) == Match.COMPLETED


def test_validate_state_transition_rejects_invalid_transition():
    with pytest.raises(ValidationError, match="Invalid match state transition"):
        validate_state_transition(Match.COMPLETED, Match.LIVE)
