from types import SimpleNamespace

from apps.tournaments.api.toc.settings_service import TOCSettingsService
from apps.tournaments.services.lobby_policy_profile import resolve_lobby_game_profile


def _build_tournament_stub(*, slug, category, game_type, config=None, enable_check_in=False):
    game = SimpleNamespace(slug=slug, category=category, game_type=game_type)
    return SimpleNamespace(
        game=game,
        config=config or {},
        enable_check_in=enable_check_in,
    )


def test_get_lobby_policy_config_clamps_direct_game_flags():
    tournament = _build_tournament_stub(
        slug="pubgm",
        category="BR",
        game_type="BATTLE_ROYALE",
        config={
            "lobby_policy": {
                "require_coin_toss": True,
                "require_map_veto": True,
                "per_round_overrides": {
                    "*": {"require_coin_toss": True, "require_map_veto": True},
                },
            },
        },
    )

    policy = TOCSettingsService._get_lobby_policy_config(tournament)

    assert policy["require_coin_toss"] is False
    assert policy["require_map_veto"] is False
    assert policy["lobby_round_overrides"]["*"]["require_coin_toss"] is False
    assert policy["lobby_round_overrides"]["*"]["require_map_veto"] is False
    assert policy["lobby_capabilities"]["phase_mode"] == "direct"


def test_get_lobby_policy_config_coerces_string_booleans():
    tournament = _build_tournament_stub(
        slug="valorant",
        category="FPS",
        game_type="TEAM_VS_TEAM",
        config={
            "lobby_policy": {
                "require_coin_toss": "false",
                "require_map_veto": "0",
            },
        },
    )

    policy = TOCSettingsService._get_lobby_policy_config(tournament)

    assert policy["require_coin_toss"] is False
    assert policy["require_map_veto"] is False


def test_validate_settings_payload_rejects_unsupported_lobby_enables():
    direct_capabilities = resolve_lobby_game_profile(slug="efootball", category="SPORTS", game_type="1V1")

    field_errors, section_errors = TOCSettingsService._validate_settings_payload(
        {
            "require_coin_toss": True,
            "require_map_veto": True,
            "lobby_round_overrides": {
                "2": {"require_coin_toss": True, "require_map_veto": True},
            },
        },
        lobby_capabilities=direct_capabilities,
    )

    assert "require_coin_toss" in field_errors
    assert "require_map_veto" in field_errors
    assert "lobby_round_overrides" in field_errors
    assert "settings-features" in section_errors
