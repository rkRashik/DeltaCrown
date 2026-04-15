from types import SimpleNamespace
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.tournaments.models import Match
from apps.tournaments.views import match_room as match_room_view
from apps.tournaments.views.match_room import _build_phase_order, _ensure_match_workflow


class _SessionStub(dict):
    modified = False


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


def test_ensure_match_workflow_exposes_match_evidence_toggle():
    match = _build_match_stub(
        slug="valorant",
        category="FPS",
        game_type="TEAM_VS_TEAM",
        policy={"require_match_evidence": True},
    )

    _lobby_info, _workflow, runtime, _changed = _ensure_match_workflow(match, persist=False)

    assert runtime["policy"]["base"]["require_match_evidence"] is True
    assert runtime["policy"]["effective"]["require_match_evidence"] is True


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


def test_build_room_payload_marks_checkin_passive_for_direct_ready_mode(monkeypatch):
    tournament = SimpleNamespace(id=77, slug="direct-cup", name="Direct Cup")
    match = SimpleNamespace(
        id=230,
        state=Match.SCHEDULED,
        get_state_display=lambda: "Scheduled",
        round_number=1,
        match_number=1,
        participant1_id=6101,
        participant1_name="Alpha",
        participant1_score=0,
        participant1_checked_in=False,
        participant2_id=6102,
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
        "game_name": "PUBG Mobile",
        "game_slug": "pubgm",
        "pipeline_game_key": "pubgm",
        "phase_mode": "direct",
        "credential_schema": [
            {"key": "lobby_code", "label": "Room Number", "kind": "text", "required": True},
        ],
        "best_of": 1,
        "map_pool": [],
        "phase_order": ["phase1", "lobby_setup", "live", "results", "completed"],
        "phase1_kind": "direct",
        "policy": {"effective": {"require_check_in": True}},
        "check_in_window": {
            "required": True,
            "is_pending": True,
            "is_open": False,
            "is_closed": False,
        },
        "presence": {"1": {}, "2": {}},
    }
    workflow = {
        "phase": "phase1",
        "phase_order": runtime["phase_order"],
        "phase1_kind": "direct",
        "policy": runtime["policy"],
        "check_in_window": runtime["check_in_window"],
        "presence": runtime["presence"],
        "credentials": {"lobby_code": "ROOM-230"},
        "result_submissions": {"1": None, "2": None},
    }

    monkeypatch.setattr(match_room_view, "_side_submission_map", lambda _match: {})
    monkeypatch.setattr(match_room_view, "_participant_media_map", lambda _match: {})

    payload = match_room_view._build_room_payload(
        match,
        {"user_id": 6101, "user_side": 1, "is_staff": False, "admin_mode": False},
        {"lobby_code": "ROOM-230"},
        workflow,
        runtime,
    )

    check_in_window = payload["workflow"]["check_in_window"]
    assert check_in_window["required"] is False
    assert check_in_window["passive"] is True
    assert check_in_window["passive_reason"] == "direct_ready_authoritative"


def test_direct_ready_progressed_room_never_re_emits_ready_confirmation_blocker():
    tournament = SimpleNamespace(id=91, slug="direct-authority-cup", name="Direct Authority Cup")
    match = SimpleNamespace(
        id=910,
        state=Match.READY,
        participant1_id=8001,
        participant2_id=8002,
        participant1_name="Alpha",
        participant2_name="Bravo",
        participant1_checked_in=False,
        participant2_checked_in=False,
        started_at=None,
        completed_at=None,
        participant1_score=0,
        participant2_score=0,
        winner_id=None,
        loser_id=None,
        tournament=tournament,
    )

    lobby_info = {}
    workflow = {
        "phase": "lobby_setup",
        "mode": "direct",
        "phase_order": ["phase1", "lobby_setup", "live", "results", "completed"],
        "policy": {"effective": {"require_check_in": True}},
        "check_in_window": {"required": True},
        "direct_ready": {"1": True, "2": True},
        "credentials": {},
        "result_submissions": {"1": None, "2": None},
    }
    runtime = {
        "phase_mode": "direct",
        "phase_order": workflow["phase_order"],
        "policy": workflow["policy"],
        "check_in_window": workflow["check_in_window"],
        "best_of": 1,
        "credential_schema": [
            {"key": "lobby_code", "label": "Room Number", "kind": "text", "required": True},
            {"key": "password", "label": "Password", "kind": "text", "required": False},
        ],
    }
    access = {
        "is_staff": False,
        "admin_mode": False,
        "user_side": 1,
        "user_id": 8001,
    }

    changed, message = match_room_view.MatchRoomWorkflowView()._apply_action(
        match=match,
        access=access,
        lobby_info=lobby_info,
        workflow=workflow,
        runtime=runtime,
        action="save_credentials",
        payload={"lobby_code": "ROOM-910", "password": "abc123"},
        files={},
    )

    assert changed is True
    assert message == "Host broadcasted lobby credentials."
    assert workflow["phase"] == "lobby_setup"
    assert lobby_info["lobby_code"] == "ROOM-910"


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


def test_build_room_payload_uses_dynamic_match_configuration_schema(monkeypatch):
    tournament = SimpleNamespace(
        id=90,
        slug="schema-cup",
        name="Schema Cup",
        match_settings={
            "game_key": "efootball",
            "schema_version": "1.0",
            "values": {
                "match_type": "Exhibition",
                "match_time": 10,
                "injuries": False,
                "extra_time": True,
                "penalties": True,
                "substitutions": "5",
                "condition_home": "Excellent",
                "condition_away": "Normal",
            },
        },
    )
    match = SimpleNamespace(
        id=225,
        state=Match.SCHEDULED,
        get_state_display=lambda: "Scheduled",
        round_number=1,
        match_number=1,
        participant1_id=4101,
        participant1_name="Team One",
        participant1_score=0,
        participant1_checked_in=False,
        participant2_id=4102,
        participant2_name="Team Two",
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
        "check_in_window": {"required": False},
        "presence": {"1": {}, "2": {}},
    }

    workflow = {
        "phase": "lobby_setup",
        "phase_order": runtime["phase_order"],
        "phase1_kind": "direct",
        "policy": {},
        "check_in_window": runtime["check_in_window"],
        "presence": {"1": {}, "2": {}},
        "credentials": {"lobby_code": "SC-10"},
        "result_submissions": {"1": None, "2": None},
        "result_status": "pending",
    }

    monkeypatch.setattr(match_room_view, "_side_submission_map", lambda _match: {})
    monkeypatch.setattr(match_room_view, "_participant_media_map", lambda _match: {})

    payload = match_room_view._build_room_payload(
        match,
        {"user_id": 4101, "user_side": 1, "is_staff": False, "admin_mode": False},
        {"lobby_code": "SC-10"},
        workflow,
        runtime,
    )

    rules = payload["game"]["match_rules"]
    rule_map = {row["title"]: row["value"] for row in rules}

    assert rule_map["Match Type"] == "Exhibition"
    assert rule_map["Match Time"] == "10 min"
    assert rule_map["Injuries"] == "Disabled"
    assert rule_map["Extra Time"] == "Enabled"
    assert rule_map["Penalties"] == "Enabled"
    assert rule_map["Substitutions"] == "5"
    assert rule_map["Condition (Home)"] == "Excellent"
    assert rule_map["Condition (Away)"] == "Normal"
    assert "Pipeline" not in rule_map


def test_build_room_payload_masks_opponent_result_for_participants_and_reveals_for_admin(monkeypatch):
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
    assert hidden_payload["me"]["can_submit_result"] is False
    assert hidden_visibility["opponent_revealed"] is False
    assert hidden_visibility["both_submitted"] is True

    participant_verified_workflow = dict(workflow)
    participant_verified_workflow["result_status"] = "verified"
    participant_verified_payload = match_room_view._build_room_payload(
        match,
        {"user_id": 3001, "user_side": 1, "is_staff": False, "admin_mode": False},
        {"lobby_code": "L-10"},
        participant_verified_workflow,
        runtime,
    )

    participant_verified_rows = participant_verified_payload["workflow"]["result_submissions"]
    participant_verified_visibility = participant_verified_payload["workflow"]["result_visibility"]

    assert participant_verified_rows["2"]["blind_masked"] is True
    assert "score_for" not in participant_verified_rows["2"]
    assert participant_verified_visibility["opponent_revealed"] is False

    admin_payload = match_room_view._build_room_payload(
        match,
        {"user_id": 9999, "user_side": None, "is_staff": True, "admin_mode": True},
        {"lobby_code": "L-10"},
        participant_verified_workflow,
        runtime,
    )

    admin_rows = admin_payload["workflow"]["result_submissions"]
    admin_visibility = admin_payload["workflow"]["result_visibility"]

    assert admin_rows["1"]["score_for"] == 2
    assert admin_rows["2"]["score_for"] == 1
    assert admin_visibility["opponent_revealed"] is True


def test_direct_ready_marks_side_ready_without_separate_match_checkin_gate():
    view = match_room_view.MatchRoomWorkflowView()
    now = timezone.now()
    match = SimpleNamespace(
        participant1_checked_in=False,
        participant2_checked_in=False,
        participant1_name="rkrashik",
        participant2_name="Nawab",
        state=Match.SCHEDULED,
        started_at=None,
    )
    access = {"is_staff": False, "admin_mode": False, "user_side": 1, "user_id": 101}
    lobby_info = {}
    workflow = {
        "phase": "phase1",
        "mode": "direct",
        "phase_order": ["phase1", "lobby_setup", "live", "results", "completed"],
        "direct_ready": {"1": False, "2": False},
        "credentials": {"lobby_code": ""},
    }
    runtime = {
        "phase_mode": "direct",
        "phase_order": ["phase1", "lobby_setup", "live", "results", "completed"],
        "phase1_kind": "direct",
        "policy": {"effective": {"require_check_in": True}},
        "check_in_window": {
            "required": True,
            "is_pending": True,
            "is_closed": False,
            "opens_at": (now + timedelta(minutes=5)).isoformat(),
            "closes_at": (now + timedelta(minutes=15)).isoformat(),
        },
    }

    changed, message = view._apply_action(
        match=match,
        access=access,
        lobby_info=lobby_info,
        workflow=workflow,
        runtime=runtime,
        action="direct_ready",
        payload={"ready": True},
        files={},
    )

    assert changed is True
    assert message == "Ready status updated."
    assert workflow["direct_ready"]["1"] is True
    assert match.participant1_checked_in is True
    assert workflow["phase"] == "phase1"


def test_start_live_after_both_direct_ready_no_longer_raises_waiting_for_checkin():
    view = match_room_view.MatchRoomWorkflowView()
    match = SimpleNamespace(
        participant1_checked_in=False,
        participant2_checked_in=False,
        participant1_name="rkrashik",
        participant2_name="Nawab",
        state=Match.SCHEDULED,
        started_at=None,
    )
    lobby_info = {}
    workflow = {
        "phase": "phase1",
        "mode": "direct",
        "phase_order": ["phase1", "lobby_setup", "live", "results", "completed"],
        "direct_ready": {"1": False, "2": False},
        "credentials": {"lobby_code": "ROOM-77"},
    }
    runtime = {
        "phase_mode": "direct",
        "phase_order": ["phase1", "lobby_setup", "live", "results", "completed"],
        "phase1_kind": "direct",
        "policy": {"effective": {"require_check_in": True}},
        "check_in_window": {"required": True, "is_pending": True, "is_closed": False},
    }

    view._apply_action(
        match=match,
        access={"is_staff": False, "admin_mode": False, "user_side": 1, "user_id": 101},
        lobby_info=lobby_info,
        workflow=workflow,
        runtime=runtime,
        action="direct_ready",
        payload={"ready": True},
        files={},
    )
    view._apply_action(
        match=match,
        access={"is_staff": False, "admin_mode": False, "user_side": 2, "user_id": 202},
        lobby_info=lobby_info,
        workflow=workflow,
        runtime=runtime,
        action="direct_ready",
        payload={"ready": True},
        files={},
    )

    changed, message = view._apply_action(
        match=match,
        access={"is_staff": False, "admin_mode": False, "user_side": 1, "user_id": 101},
        lobby_info=lobby_info,
        workflow=workflow,
        runtime=runtime,
        action="start_live",
        payload={},
        files={},
    )

    assert changed is True
    assert message == "Match marked live."
    assert match.state == Match.LIVE
    assert match.started_at is not None


def test_resolve_match_room_access_blocks_participant_before_30_minutes():
    now = timezone.now()
    match = SimpleNamespace(
        participant1_id=101,
        participant2_id=202,
        state=Match.SCHEDULED,
        scheduled_time=now + timedelta(hours=2),
        tournament=SimpleNamespace(organizer_id=999),
    )
    user = SimpleNamespace(is_authenticated=True, is_staff=False, id=101)

    access = match_room_view._resolve_match_room_access(user, match)

    assert access["allowed"] is False
    assert access["user_side"] == 1
    assert access["denied_reason"] == "lobby_not_open"
    assert access["lobby_opens_at"] is not None


def test_resolve_match_room_access_allows_participant_within_30_minutes():
    now = timezone.now()
    match = SimpleNamespace(
        participant1_id=101,
        participant2_id=202,
        state=Match.SCHEDULED,
        scheduled_time=now + timedelta(minutes=25),
        tournament=SimpleNamespace(organizer_id=999),
    )
    user = SimpleNamespace(is_authenticated=True, is_staff=False, id=101)

    access = match_room_view._resolve_match_room_access(user, match)

    assert access["allowed"] is True
    assert access["denied_reason"] is None


def test_resolve_match_room_access_allows_toc_authorized_staff_before_window():
    now = timezone.now()
    match = SimpleNamespace(
        id=901,
        tournament_id=77,
        participant1_id=101,
        participant2_id=202,
        state=Match.SCHEDULED,
        scheduled_time=now + timedelta(hours=2),
        tournament=SimpleNamespace(organizer_id=999),
    )
    staff_user = SimpleNamespace(is_authenticated=True, is_staff=True, id=500)

    access = match_room_view._resolve_match_room_access(
        staff_user,
        match,
        admin_mode_requested=True,
        admin_mode_authorized=True,
        admin_mode_token="tok-1",
    )

    assert access["allowed"] is True
    assert access["is_staff"] is True
    assert access["admin_mode"] is True
    assert access["admin_token"] == "tok-1"
    assert access["denied_reason"] is None


def test_resolve_match_room_access_organizer_participant_uses_participant_mode_without_toc_admin():
    now = timezone.now()
    match = SimpleNamespace(
        id=902,
        tournament_id=78,
        participant1_id=101,
        participant2_id=202,
        state=Match.SCHEDULED,
        scheduled_time=now + timedelta(hours=2),
        tournament=SimpleNamespace(organizer_id=101),
    )
    organizer_participant = SimpleNamespace(is_authenticated=True, is_staff=False, id=101)

    access = match_room_view._resolve_match_room_access(
        organizer_participant,
        match,
        admin_mode_requested=False,
        admin_mode_authorized=False,
    )

    assert access["allowed"] is False
    assert access["is_staff"] is False
    assert access["admin_mode"] is False
    assert access["user_side"] == 1
    assert access["denied_reason"] == "lobby_not_open"


def test_resolve_match_room_access_denies_admin_mode_without_toc_authorization():
    now = timezone.now()
    match = SimpleNamespace(
        id=903,
        tournament_id=79,
        participant1_id=101,
        participant2_id=202,
        state=Match.SCHEDULED,
        scheduled_time=now + timedelta(hours=2),
        tournament=SimpleNamespace(organizer_id=101),
    )
    organizer_participant = SimpleNamespace(is_authenticated=True, is_staff=False, id=101)

    access = match_room_view._resolve_match_room_access(
        organizer_participant,
        match,
        admin_mode_requested=True,
        admin_mode_authorized=False,
    )

    assert access["admin_mode"] is False
    assert access["is_staff"] is False
    assert access["denied_reason"] == "lobby_not_open"


def test_resolve_match_room_access_allows_admin_mode_when_toc_authorized():
    now = timezone.now()
    match = SimpleNamespace(
        id=904,
        tournament_id=80,
        participant1_id=101,
        participant2_id=202,
        state=Match.SCHEDULED,
        scheduled_time=now + timedelta(hours=2),
        tournament=SimpleNamespace(organizer_id=101),
    )
    organizer_participant = SimpleNamespace(is_authenticated=True, is_staff=False, id=101)

    access = match_room_view._resolve_match_room_access(
        organizer_participant,
        match,
        admin_mode_requested=True,
        admin_mode_authorized=True,
        admin_mode_token="tok-2",
    )

    assert access["allowed"] is True
    assert access["admin_mode"] is True
    assert access["is_staff"] is True
    assert access["admin_token"] == "tok-2"
    assert access["denied_reason"] is None


def test_resolve_admin_mode_request_rejects_non_toc_admin_query():
    request = SimpleNamespace(
        GET={"admin": "1"},
        META={"HTTP_REFERER": "https://example.com/tournaments/cup/hub/"},
        session=_SessionStub(),
        user=SimpleNamespace(id=501),
    )
    match = SimpleNamespace(id=905, tournament_id=81)

    requested, authorized, token = match_room_view._resolve_admin_mode_request(request, match)

    assert requested is True
    assert authorized is False
    assert token == ""


def test_resolve_admin_mode_request_allows_toc_flow_and_reuses_token():
    session = _SessionStub()
    match = SimpleNamespace(id=906, tournament_id=82)

    first_request = SimpleNamespace(
        GET={"admin": "1"},
        META={"HTTP_REFERER": "https://example.com/toc/cup/"},
        session=session,
        user=SimpleNamespace(id=502),
    )
    requested, authorized, issued_token = match_room_view._resolve_admin_mode_request(first_request, match)

    assert requested is True
    assert authorized is True
    assert issued_token

    follow_up_request = SimpleNamespace(
        GET={"admin": "1", "admin_token": issued_token},
        META={"HTTP_REFERER": "https://example.com/tournaments/cup/hub/"},
        session=session,
        user=SimpleNamespace(id=502),
    )
    requested_follow_up, authorized_follow_up, token_follow_up = match_room_view._resolve_admin_mode_request(
        follow_up_request,
        match,
    )

    assert requested_follow_up is True
    assert authorized_follow_up is True
    assert token_follow_up == issued_token


def test_resolve_match_room_access_blocks_participant_after_lobby_close():
    now = timezone.now()
    match = SimpleNamespace(
        participant1_id=101,
        participant2_id=202,
        state=Match.SCHEDULED,
        scheduled_time=now - timedelta(minutes=20),
        tournament=SimpleNamespace(organizer_id=999),
    )
    user = SimpleNamespace(is_authenticated=True, is_staff=False, id=101)

    access = match_room_view._resolve_match_room_access(user, match)

    assert access["allowed"] is False
    assert access["denied_reason"] == "lobby_closed"
    assert access["lobby_closes_at"] is not None


@pytest.mark.parametrize("match_state", [Match.READY, Match.LIVE, Match.PENDING_RESULT])
def test_resolve_match_room_access_allows_participant_reentry_for_forced_open_states(match_state):
    now = timezone.now()
    match = SimpleNamespace(
        participant1_id=101,
        participant2_id=202,
        state=match_state,
        scheduled_time=now - timedelta(hours=3),
        tournament=SimpleNamespace(organizer_id=999),
    )
    user = SimpleNamespace(is_authenticated=True, is_staff=False, id=101)

    access = match_room_view._resolve_match_room_access(user, match)

    assert access["allowed"] is True
    assert access["denied_reason"] is None
