from types import SimpleNamespace

import pytest

from apps.tournaments.models import Match
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
