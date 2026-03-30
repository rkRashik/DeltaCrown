"""
Game-aware lobby policy profile helpers.

This module centralizes how lobby flow is derived from game metadata so
match-room runtime and TOC settings use the exact same compatibility matrix.
"""

from __future__ import annotations

from typing import Any, Dict


KNOWN_DRAFT_GAME_KEYS = {
    "dota2",
    "mlbb",
}

KNOWN_DIRECT_GAME_KEYS = {
    "pubgm",
    "freefire",
    "eafc",
    "efootball",
    "rocketleague",
}

GAME_KEY_ALIASES = {
    "r6": "r6siege",
    "rainbowsix": "r6siege",
    "rainbowsixsiege": "r6siege",
    "pubgmobile": "pubgm",
    "pubg": "pubgm",
    "fifa": "eafc",
    "fc26": "eafc",
    "easportsfc": "eafc",
    "callofdutymobile": "codm",
    "codmobile": "codm",
    "mobilelegends": "mlbb",
    "leagueoflegends": "lol",
}


def normalize_game_slug(raw_slug: Any) -> str:
    return str(raw_slug or "").strip().lower().replace("_", "-")


def compact_game_key(raw_slug: Any) -> str:
    return normalize_game_slug(raw_slug).replace("-", "")


def canonical_game_key(raw_slug: Any) -> str:
    return GAME_KEY_ALIASES.get(compact_game_key(raw_slug), compact_game_key(raw_slug))


def resolve_lobby_game_profile(
    game: Any | None = None,
    *,
    slug: Any = "",
    category: Any = "",
    game_type: Any = "",
) -> Dict[str, Any]:
    if game is not None:
        slug = slug or getattr(game, "slug", "")
        category = category or getattr(game, "category", "")
        game_type = game_type or getattr(game, "game_type", "")

    normalized_slug = normalize_game_slug(slug)
    normalized_category = str(category or "").upper()
    normalized_game_type = str(game_type or "").upper()
    key = compact_game_key(normalized_slug)
    canonical_key = GAME_KEY_ALIASES.get(key, key)

    phase_mode = "veto"
    if canonical_key in KNOWN_DRAFT_GAME_KEYS or normalized_category == "MOBA":
        phase_mode = "draft"
    elif (
        canonical_key in KNOWN_DIRECT_GAME_KEYS
        or normalized_category in {"BR", "SPORTS"}
        or normalized_game_type in {"BATTLE_ROYALE", "FREE_FOR_ALL", "1V1"}
    ):
        phase_mode = "direct"

    supports_coin_toss = phase_mode in {"veto", "draft"}
    supports_map_veto = phase_mode == "veto"

    reference = "General tournament defaults"
    if canonical_key == "cs2":
        reference = "Valve CS Major Supplemental Rulebook"
    elif phase_mode == "draft":
        reference = "MOBA captain's mode style draft flow"
    elif phase_mode == "direct":
        reference = "Battle Royale / sports direct lobby flow"
    elif phase_mode == "veto":
        reference = "FPS map veto flow"

    return {
        "game_slug": normalized_slug,
        "game_key": key,
        "canonical_game_key": canonical_key,
        "phase_mode": phase_mode,
        "supports_coin_toss": supports_coin_toss,
        "supports_map_veto": supports_map_veto,
        "default_require_coin_toss": supports_coin_toss,
        "default_require_map_veto": supports_map_veto,
        "reference": reference,
    }


def apply_lobby_policy_capabilities(policy_flags: Dict[str, Any], capabilities: Dict[str, Any]) -> Dict[str, bool]:
    flags = dict(policy_flags or {})

    normalized = {
        "require_check_in": bool(flags.get("require_check_in", False)),
        "require_coin_toss": bool(flags.get("require_coin_toss", capabilities.get("default_require_coin_toss", True))),
        "require_map_veto": bool(flags.get("require_map_veto", capabilities.get("default_require_map_veto", True))),
    }

    if not bool(capabilities.get("supports_coin_toss", True)):
        normalized["require_coin_toss"] = False

    if not bool(capabilities.get("supports_map_veto", True)):
        normalized["require_map_veto"] = False

    return normalized


def clamp_lobby_round_overrides(
    round_overrides: Dict[str, Dict[str, Any]] | None,
    capabilities: Dict[str, Any],
) -> Dict[str, Dict[str, bool]]:
    if not isinstance(round_overrides, dict):
        return {}

    supports_coin_toss = bool(capabilities.get("supports_coin_toss", True))
    supports_map_veto = bool(capabilities.get("supports_map_veto", True))

    normalized: Dict[str, Dict[str, bool]] = {}
    for round_key, payload in round_overrides.items():
        if not isinstance(payload, dict):
            continue

        row: Dict[str, bool] = {}
        if "require_check_in" in payload:
            row["require_check_in"] = bool(payload.get("require_check_in"))

        if "require_coin_toss" in payload:
            row["require_coin_toss"] = bool(payload.get("require_coin_toss")) and supports_coin_toss

        if "require_map_veto" in payload:
            row["require_map_veto"] = bool(payload.get("require_map_veto")) and supports_map_veto

        if row:
            normalized[str(round_key)] = row

    return normalized
