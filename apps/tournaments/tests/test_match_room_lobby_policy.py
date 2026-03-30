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


def test_build_room_payload_efootball_rules_surface_platform_and_match_time(monkeypatch):
    game_tournament_config = SimpleNamespace(
        default_match_duration_minutes=12,
        allow_draws=False,
        overtime_enabled=True,
    )
    game = SimpleNamespace(tournament_config=game_tournament_config)
    game_match_config = SimpleNamespace(
        default_match_format="bo1",
        match_settings={
            "match_duration_minutes": 10,
            "extra_time": True,
            "penalties": False,
        },
    )
    tournament = SimpleNamespace(
        id=88,
        slug="sports-cup",
        name="Sports Cup",
        platform="ps5",
        mode="online",
        game=game,
        game_match_config=game_match_config,
    )
    match = SimpleNamespace(
        id=223,
        state=Match.SCHEDULED,
        get_state_display=lambda: "Scheduled",
        round_number=1,
        match_number=8,
        participant1_id=2001,
        participant1_name="Alpha",
        participant1_score=0,
        participant1_checked_in=False,
        participant2_id=2002,
        participant2_name="Bravo",
        participant2_score=0,
        participant2_checked_in=False,
        winner_id=None,
        scheduled_time=None,
        started_at=None,
        completed_at=None,
        tournament=tournament,
        tournament_id=tournament.id,
        best_of=1,
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
        "check_in_window": {"required": True},
        "presence": {"1": {}, "2": {}},
    }
    workflow = {
        "phase": "lobby_setup",
        "phase_order": runtime["phase_order"],
        "phase1_kind": "direct",
        "policy": {},
        "check_in_window": runtime["check_in_window"],
        "presence": {"1": {}, "2": {}},
        "credentials": {"lobby_code": "RM-10", "password": "pw"},
        "result_submissions": {"1": None, "2": None},
        "result_status": "pending",
    }

    monkeypatch.setattr(match_room_view, "_side_submission_map", lambda _match: {})
    monkeypatch.setattr(match_room_view, "_participant_media_map", lambda _match: {})

    payload = match_room_view._build_room_payload(
        match,
        {"user_id": 2001, "user_side": 1, "is_staff": False, "admin_mode": False},
        {"lobby_code": "RM-10", "password": "pw"},
        workflow,
        runtime,
    )

    rules = payload["game"]["match_rules"]
    rule_map = {row["title"]: row["value"] for row in rules}

    assert rule_map["Pipeline"] == "Direct Setup"
    assert rule_map["Match Format"] == "Bo1"
    assert rule_map["Platform"] == "PlayStation 5"
    assert rule_map["Tournament Mode"] == "Online"
    assert rule_map["Match Time"] == "10 min total"
    assert rule_map["Extra Time"] == "Enabled"
    assert rule_map["Penalties"] == "Disabled"
    assert rule_map["Draws"] == "Not Allowed"
    assert "Map Pool" not in rule_map


def test_build_room_payload_masks_opponent_result_until_reveal(monkeypatch):
    tournament = SimpleNamespace(id=89, slug="blind-cup", name="Blind Cup")
    match = SimpleNamespace(
        id=224,
        state=Match.PENDING_RESULT,
        get_state_display=lambda: "Pending Result",
        round_number=2,
        match_number=3,
        participant1_id=3001,
        participant1_name="Side One",
        participant1_score=0,
        participant1_checked_in=True,
        participant2_id=3002,
        participant2_name="Side Two",
        participant2_score=0,
        participant2_checked_in=True,
        winner_id=None,
        scheduled_time=None,
        started_at=None,
        completed_at=None,
        tournament=tournament,
        tournament_id=tournament.id,
        best_of=1,
    )

    runtime = {
        "game_name": "Valorant",
        "game_slug": "valorant",
        "pipeline_game_key": "valorant",
        "phase_mode": "veto",
        "credential_schema": [
            {"key": "lobby_code", "label": "Lobby Code", "kind": "text", "required": True},
            {"key": "password", "label": "Password", "kind": "text", "required": False},
        ],
        "best_of": 1,
        "map_pool": ["Ascent", "Bind"],
        "phase_order": ["coin_toss", "phase1", "lobby_setup", "live", "results", "completed"],
        "phase1_kind": "veto",
        "policy": {},
        "check_in_window": {"required": True},
        "presence": {"1": {}, "2": {}},
    }

    submissions = {
        "1": {
            "submission_id": 11,
            "status": "pending",
            "score_for": 2,
            "score_against": 1,
            "submitted_at": "2026-03-30T10:00:00Z",
        },
        "2": {
            "submission_id": 12,
            "status": "pending",
            "score_for": 1,
            "score_against": 2,
            "submitted_at": "2026-03-30T10:01:00Z",
        },
    }
    workflow = {
        "phase": "results",
        "phase_order": runtime["phase_order"],
        "phase1_kind": "veto",
        "policy": {},
        "check_in_window": runtime["check_in_window"],
        "presence": {"1": {}, "2": {}},
        "credentials": {"lobby_code": "L-10"},
        "result_submissions": submissions,
        "result_status": "pending",
    }

    monkeypatch.setattr(match_room_view, "_side_submission_map", lambda _match: {})
    monkeypatch.setattr(match_room_view, "_participant_media_map", lambda _match: {})

    hidden_payload = match_room_view._build_room_payload(
        match,
        {"user_id": 3001, "user_side": 1, "is_staff": False, "admin_mode": False},
        {"lobby_code": "L-10"},
        workflow,
        runtime,
    )

    hidden_rows = hidden_payload["workflow"]["result_submissions"]
    hidden_visibility = hidden_payload["workflow"]["result_visibility"]

    assert hidden_rows["1"]["score_for"] == 2
    assert hidden_rows["2"]["blind_masked"] is True
    assert "score_for" not in hidden_rows["2"]
    assert hidden_visibility["opponent_revealed"] is False
    assert hidden_visibility["both_submitted"] is True

    revealed_workflow = dict(workflow)
    revealed_workflow["result_status"] = "verified"

    revealed_payload = match_room_view._build_room_payload(
        match,
        {"user_id": 3001, "user_side": 1, "is_staff": False, "admin_mode": False},
        {"lobby_code": "L-10"},
        revealed_workflow,
        runtime,
    )

    revealed_rows = revealed_payload["workflow"]["result_submissions"]
    revealed_visibility = revealed_payload["workflow"]["result_visibility"]

    assert revealed_rows["2"]["score_for"] == 1
    assert revealed_rows["2"].get("blind_masked") is None
    assert revealed_visibility["opponent_revealed"] is True
