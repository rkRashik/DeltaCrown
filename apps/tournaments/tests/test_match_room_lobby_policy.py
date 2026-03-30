from types import SimpleNamespace

import pytest

from apps.tournaments.models import Match
from apps.tournaments.views import match_room as match_room_view
from apps.tournaments.views.match_room import _build_phase_order, _ensure_match_workflow


def _build_match_stub(*, slug, category, game_type, policy=None):
    game = SimpleNamespace(
        slug=slug,
        category=category,
        game_type=game_type,
        display_name=slug,
        name=slug,
    )
    tournament = SimpleNamespace(
        game=game,
        config={"lobby_policy": policy or {}},
        enable_check_in=False,
        auto_forfeit_no_shows=False,
        enable_no_show_timer=False,
        no_show_timeout_minutes=10,
    )
    return SimpleNamespace(
        tournament=tournament,
        best_of=1,
        state=Match.SCHEDULED,
        lobby_info={},
        round_number=1,
        scheduled_time=None,
        check_in_deadline=None,
        participant1_checked_in=False,
        participant2_checked_in=False,
    )


@pytest.mark.parametrize(
    "slug,category,game_type,expected_mode",
    [
        ("r6siege", "FPS", "TEAM_VS_TEAM", "veto"),
        ("dota2", "MOBA", "TEAM_VS_TEAM", "draft"),
        ("pubgm", "BR", "BATTLE_ROYALE", "direct"),
    ],
)
def test_ensure_match_workflow_uses_game_mode_matrix(slug, category, game_type, expected_mode):
    match = _build_match_stub(slug=slug, category=category, game_type=game_type)

    _lobby_info, _workflow, runtime, _changed = _ensure_match_workflow(match, persist=False)

    assert runtime["phase_mode"] == expected_mode


def test_ensure_match_workflow_uses_r6_default_map_pool():
    match = _build_match_stub(slug="r6siege", category="FPS", game_type="TEAM_VS_TEAM")

    _lobby_info, _workflow, runtime, _changed = _ensure_match_workflow(match, persist=False)

    assert "Clubhouse" in runtime["map_pool"]
    assert runtime["map_pool"] != ["Map 1", "Map 2", "Map 3", "Map 4", "Map 5"]


def test_ensure_match_workflow_clamps_direct_policy_toggles():
    match = _build_match_stub(
        slug="pubgm",
        category="BR",
        game_type="BATTLE_ROYALE",
        policy={
            "require_coin_toss": True,
            "require_map_veto": True,
            "per_round_overrides": {"1": {"require_coin_toss": True, "require_map_veto": True}},
        },
    )

    _lobby_info, _workflow, runtime, _changed = _ensure_match_workflow(match, persist=False)

    policy = runtime["policy"]
    assert policy["effective"]["require_coin_toss"] is False
    assert policy["effective"]["require_map_veto"] is False
    assert policy["round_overrides"]["1"]["require_coin_toss"] is False
    assert policy["round_overrides"]["1"]["require_map_veto"] is False


def test_ensure_match_workflow_global_coin_toss_disable_wins_over_round_override():
    match = _build_match_stub(
        slug="valorant",
        category="FPS",
        game_type="TEAM_VS_TEAM",
        policy={
            "require_coin_toss": False,
            "require_map_veto": True,
            "per_round_overrides": {"1": {"require_coin_toss": True}},
        },
    )

    _lobby_info, _workflow, runtime, _changed = _ensure_match_workflow(match, persist=False)

    assert runtime["policy"]["base"]["require_coin_toss"] is False
    assert runtime["policy"]["effective"]["require_coin_toss"] is False
    assert "coin_toss" not in runtime["phase_order"]


def test_build_phase_order_never_includes_coin_toss_in_direct_mode():
    phase_order, phase1_kind = _build_phase_order(
        "direct",
        {
            "require_coin_toss": True,
            "require_map_veto": False,
        },
    )

    assert phase1_kind == "direct"
    assert "coin_toss" not in phase_order
    assert phase_order[0] == "phase1"


def test_ensure_match_workflow_uses_efootball_room_number_schema():
    match = _build_match_stub(slug="efootball", category="SPORTS", game_type="1V1")

    _lobby_info, _workflow, runtime, _changed = _ensure_match_workflow(match, persist=False)

    schema = runtime["credential_schema"]
    keys = [row["key"] for row in schema]
    labels = [row["label"] for row in schema]

    assert keys == ["lobby_code", "password"]
    assert labels == ["Room Number", "Password"]


def test_build_room_payload_sets_is_host(monkeypatch):
    tournament = SimpleNamespace(id=77, slug="test-cup", name="Test Cup")
    match = SimpleNamespace(
        id=222,
        state=Match.SCHEDULED,
        get_state_display=lambda: "Scheduled",
        round_number=1,
        match_number=4,
        participant1_id=1001,
        participant1_name="Host Team",
        participant1_score=0,
        participant1_checked_in=False,
        participant2_id=1002,
        participant2_name="Guest Team",
        participant2_score=0,
        participant2_checked_in=False,
        winner_id=None,
        scheduled_time=None,
        started_at=None,
        completed_at=None,
        tournament=tournament,
        tournament_id=tournament.id,
    )

    runtime = {
        "game_name": "eFootball",
        "game_slug": "efootball",
        "pipeline_game_key": "efootball",
        "phase_mode": "direct",
        "credential_schema": [
            {"key": "lobby_code", "label": "Room Number", "kind": "text", "required": True},
            {"key": "password", "label": "Password", "kind": "text", "required": False},
        ],
        "best_of": 1,
        "map_pool": [],
        "phase_order": ["phase1", "lobby_setup", "live", "results", "completed"],
        "phase1_kind": "direct",
        "policy": {},
        "check_in_window": {},
        "presence": {"1": {}, "2": {}},
    }
    workflow = {
        "phase": "lobby_setup",
        "phase_order": runtime["phase_order"],
        "phase1_kind": "direct",
        "policy": {},
        "check_in_window": {},
        "presence": {"1": {}, "2": {}},
        "credentials": {"lobby_code": "R-12", "password": "abc123"},
        "result_submissions": {"1": None, "2": None},
    }
    lobby_info = {"lobby_code": "R-12", "password": "abc123"}

    monkeypatch.setattr(match_room_view, "_side_submission_map", lambda _match: {})
    monkeypatch.setattr(match_room_view, "_participant_media_map", lambda _match: {})

    host_payload = match_room_view._build_room_payload(
        match,
        {"user_id": 1001, "user_side": 1, "is_staff": False, "admin_mode": False},
        lobby_info,
        workflow,
        runtime,
    )
    guest_payload = match_room_view._build_room_payload(
        match,
        {"user_id": 1002, "user_side": 2, "is_staff": False, "admin_mode": False},
        lobby_info,
        workflow,
        runtime,
    )

    assert host_payload["me"]["is_host"] is True
    assert guest_payload["me"]["is_host"] is False
