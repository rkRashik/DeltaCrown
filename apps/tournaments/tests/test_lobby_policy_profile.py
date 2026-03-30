import pytest

from apps.tournaments.services.lobby_policy_profile import (
    apply_lobby_policy_capabilities,
    clamp_lobby_round_overrides,
    resolve_lobby_game_profile,
)


@pytest.mark.parametrize(
    "slug,category,game_type,phase_mode,supports_coin_toss,supports_map_veto",
    [
        ("valorant", "FPS", "TEAM_VS_TEAM", "veto", True, True),
        ("cs2", "FPS", "TEAM_VS_TEAM", "veto", True, True),
        ("codm", "FPS", "TEAM_VS_TEAM", "veto", True, True),
        ("r6siege", "FPS", "TEAM_VS_TEAM", "veto", True, True),
        ("dota2", "MOBA", "TEAM_VS_TEAM", "draft", True, False),
        ("mlbb", "MOBA", "TEAM_VS_TEAM", "draft", True, False),
        ("pubgm", "BR", "BATTLE_ROYALE", "direct", False, False),
        ("freefire", "BR", "BATTLE_ROYALE", "direct", False, False),
        ("ea-fc", "SPORTS", "1V1", "direct", False, False),
        ("efootball", "SPORTS", "1V1", "direct", False, False),
        ("rocketleague", "SPORTS", "TEAM_VS_TEAM", "direct", False, False),
    ],
)
def test_resolve_lobby_game_profile_platform_matrix(
    slug,
    category,
    game_type,
    phase_mode,
    supports_coin_toss,
    supports_map_veto,
):
    profile = resolve_lobby_game_profile(slug=slug, category=category, game_type=game_type)

    assert profile["phase_mode"] == phase_mode
    assert profile["supports_coin_toss"] is supports_coin_toss
    assert profile["supports_map_veto"] is supports_map_veto


def test_aliases_resolve_to_canonical_keys():
    assert resolve_lobby_game_profile(slug="r6")["canonical_game_key"] == "r6siege"
    assert resolve_lobby_game_profile(slug="pubg-mobile")["canonical_game_key"] == "pubgm"
    assert resolve_lobby_game_profile(slug="fifa")["canonical_game_key"] == "eafc"


def test_apply_lobby_policy_capabilities_clamps_unsupported_fields():
    direct_capabilities = resolve_lobby_game_profile(slug="pubgm", category="BR", game_type="BATTLE_ROYALE")

    normalized = apply_lobby_policy_capabilities(
        {
            "require_check_in": True,
            "require_coin_toss": True,
            "require_map_veto": True,
        },
        direct_capabilities,
    )

    assert normalized == {
        "require_check_in": True,
        "require_coin_toss": False,
        "require_map_veto": False,
    }


def test_clamp_lobby_round_overrides_disables_unsupported_enablements():
    draft_capabilities = resolve_lobby_game_profile(slug="dota2", category="MOBA", game_type="TEAM_VS_TEAM")

    normalized = clamp_lobby_round_overrides(
        {
            "*": {"require_coin_toss": True, "require_map_veto": True},
            "2": {"require_check_in": True, "require_map_veto": True},
        },
        draft_capabilities,
    )

    assert normalized["*"]["require_coin_toss"] is True
    assert normalized["*"]["require_map_veto"] is False
    assert normalized["2"]["require_check_in"] is True
    assert normalized["2"]["require_map_veto"] is False
