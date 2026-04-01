"""
Phase 9.3 Match Lobby Rebuild.

This module provides a clean room implementation for the participant match lobby:
- Valorant pipeline: coin toss -> map veto -> lobby setup -> live -> result
- eFootball pipeline: direct ready -> lobby setup -> live -> result

The implementation keeps existing URL/view class names stable while replacing the
legacy multi-mode workflow internals.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
import json
import logging
import random
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_protect
from django.views.generic import DetailView

from apps.tournaments.models import Match, MatchResultSubmission
from apps.tournaments.services.lobby_policy_profile import (
    apply_lobby_policy_capabilities,
    clamp_lobby_round_overrides,
    resolve_lobby_game_profile,
)

logger = logging.getLogger(__name__)

WORKFLOW_KEY = "match_lobby_workflow"
LEGACY_WORKFLOW_KEY = "premium_lobby_workflow"

PHASES = {
    "coin_toss",
    "phase1",
    "lobby_setup",
    "live",
    "results",
    "completed",
}
PHASE_FALLBACK_ORDER = ["coin_toss", "phase1", "lobby_setup", "live", "results", "completed"]

PIPELINE_OVERRIDES = {
    "valorant": "veto",
    "efootball": "direct",
}

DEFAULT_MAP_POOLS = {
    "valorant": ["Ascent", "Bind", "Haven", "Split", "Icebox", "Lotus", "Sunset"],
    "r6siege": ["Clubhouse", "Coastline", "Border", "Kafe", "Villa", "Chalet"],
    "r6": ["Clubhouse", "Coastline", "Border", "Kafe", "Villa", "Chalet"],
    "cs2": ["Mirage", "Inferno", "Dust II", "Nuke", "Ancient", "Anubis", "Vertigo"],
}

DEFAULT_CREDENTIAL_SCHEMA = [
    {"key": "lobby_code", "label": "Lobby Code", "kind": "text", "required": True},
    {"key": "password", "label": "Password", "kind": "text", "required": False},
    {"key": "map", "label": "Map", "kind": "text", "required": False},
    {"key": "server", "label": "Server", "kind": "text", "required": False},
    {"key": "game_mode", "label": "Game Mode", "kind": "text", "required": False},
    {"key": "notes", "label": "Notes", "kind": "textarea", "required": False},
]

EFOOTBALL_CREDENTIAL_SCHEMA = [
    {"key": "lobby_code", "label": "Room Number", "kind": "text", "required": True},
    {"key": "password", "label": "Password", "kind": "text", "required": False},
]

PRESENCE_STALE_SECONDS = 45

TOURNAMENT_PLATFORM_LABELS = {
    "pc": "PC",
    "mobile": "Mobile",
    "ps5": "PlayStation 5",
    "xbox": "Xbox Series X/S",
    "switch": "Nintendo Switch",
}

TOURNAMENT_MODE_LABELS = {
    "online": "Online",
    "lan": "LAN",
    "hybrid": "Hybrid",
}

MATCH_CONFIGURATION_SCHEMAS = {
    "efootball": [
        ("match_type", "Match Type"),
        ("match_time", "Match Time"),
        ("injuries", "Injuries"),
        ("extra_time", "Extra Time"),
        ("penalties", "Penalties"),
        ("substitutions", "Substitutions"),
        ("condition_home", "Condition (Home)"),
        ("condition_away", "Condition (Away)"),
    ],
    "valorant": [
        ("mode", "Mode"),
        ("cheats", "Cheats"),
        ("tournament_mode", "Tournament Mode"),
        ("overtime_win_by_two", "Overtime Win by Two"),
        ("server_region", "Server Region"),
    ],
}

MATCH_CONFIGURATION_SCHEMA_SIGNAL_KEYS = {
    "efootball": {
        "match_type",
        "match_time",
        "injuries",
        "substitutions",
        "condition_home",
        "condition_away",
    },
    "valorant": {
        "mode",
        "cheats",
        "tournament_mode",
        "overtime_win_by_two",
        "server_region",
    },
}

MATCH_CONFIGURATION_META_KEYS = {
    "game_key",
    "schema_version",
    "values",
    "fields",
    "veto_sequence",
}

PARTICIPANT_LOBBY_OPEN_LEAD_MINUTES = 30
PARTICIPANT_LOBBY_ALWAYS_OPEN_STATES = {
    "live",
    "pending_result",
    "completed",
    "forfeit",
    "disputed",
    "cancelled",
}


def _is_truthy(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token in {"1", "true", "yes", "y", "on"}


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return list(value)
    return []


def _safe_string_list(value: Any) -> List[str]:
    result: List[str] = []
    for item in _safe_list(value):
        text = str(item or "").strip()
        if text:
            result.append(text)
    return result


def _coerce_optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off", ""}:
        return False
    return None


def _draws_allowed_for_match(match: Match) -> bool:
    """Resolve whether a tied completed score can be finalized as draw."""
    try:
        from apps.tournaments.services.match_service import MatchService

        return bool(MatchService.draws_allowed_for_match(match))
    except Exception:
        pass

    tournament = getattr(match, "tournament", None)
    if tournament is None:
        return False

    format_token = str(getattr(tournament, "format", "") or "").strip().lower()
    if format_token in {
        str(Tournament.ROUND_ROBIN).lower(),
        str(Tournament.GROUP_PLAYOFF).lower(),
        "group_stage",
        "league",
    }:
        return True

    return False


def _coerce_positive_int(value: Any) -> Optional[int]:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _setting_value(settings: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key not in settings:
            continue
        value = settings.get(key)
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _format_match_format(raw_format: str, best_of: int) -> str:
    token = str(raw_format or "").strip().upper()
    display_map = {
        "BO1": "Bo1",
        "BO3": "Bo3",
        "BO5": "Bo5",
        "BO7": "Bo7",
        "RR": "Round Robin",
        "ROUND_ROBIN": "Round Robin",
        "FFA": "Free For All",
        "SINGLE": "Single Match",
        "SERIES": "Series",
    }

    if token in display_map:
        return display_map[token]

    if token.startswith("BO") and token[2:].isdigit():
        return f"Bo{int(token[2:])}"

    if best_of > 0:
        return f"Bo{best_of}"

    return "Standard"


def _format_match_duration(match_settings: Dict[str, Any], *, fallback_minutes: Optional[int]) -> str:
    half_length = _coerce_positive_int(
        _setting_value(
            match_settings,
            "half_length",
            "half_length_minutes",
            "minutes_per_half",
        )
    )
    if half_length:
        return f"{half_length} min per half"

    duration = _coerce_positive_int(
        _setting_value(
            match_settings,
            "match_duration_minutes",
            "duration_minutes",
            "match_time_minutes",
            "time_limit_minutes",
        )
    )
    if not duration:
        duration = fallback_minutes

    if duration:
        return f"{duration} min total"

    return ""


def _tournament_platform_label(tournament: Any) -> str:
    display = ""
    getter = getattr(tournament, "get_platform_display", None)
    if callable(getter):
        try:
            display = str(getter() or "").strip()
        except Exception:
            display = ""

    if display:
        return display

    token = str(getattr(tournament, "platform", "") or "").strip().lower()
    if not token:
        return "Any"
    return TOURNAMENT_PLATFORM_LABELS.get(token, token.replace("_", " ").title())


def _tournament_mode_label(tournament: Any) -> str:
    display = ""
    getter = getattr(tournament, "get_mode_display", None)
    if callable(getter):
        try:
            display = str(getter() or "").strip()
        except Exception:
            display = ""

    if display:
        return display

    token = str(getattr(tournament, "mode", "") or "").strip().lower()
    if not token:
        return "Standard"
    return TOURNAMENT_MODE_LABELS.get(token, token.replace("_", " ").title())


def _build_check_in_rule_text(match: Match, check_in_window: Dict[str, Any]) -> str:
    if not bool(check_in_window.get("required")):
        return "Not required"

    p1_text = "P1 ready" if bool(match.participant1_checked_in) else "P1 pending"
    p2_text = "P2 ready" if bool(match.participant2_checked_in) else "P2 pending"
    return f"{p1_text} / {p2_text}"


def _canonical_match_configuration_game_key(value: Any) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return ""
    if "efootball" in token or token == "pes":
        return "efootball"
    if "valorant" in token:
        return "valorant"
    return token


def _dynamic_match_configuration_values(
    match_settings: Dict[str, Any],
    *,
    runtime_game_key: str,
    runtime_game_slug: str,
) -> Tuple[str, Dict[str, Any]]:
    schema_key = _canonical_match_configuration_game_key(
        _setting_value(match_settings, "game_key", "game", "game_slug")
        or runtime_game_key
        or runtime_game_slug
    )

    values = _safe_dict(match_settings.get("values"))
    if not values:
        values = _safe_dict(match_settings.get("fields"))
    if not values:
        values = {
            key: value
            for key, value in match_settings.items()
            if key not in MATCH_CONFIGURATION_META_KEYS
        }

    return schema_key, values


def _format_dynamic_match_configuration_value(field_key: str, value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, bool):
        return "Enabled" if value else "Disabled"

    if isinstance(value, (list, tuple)):
        text_list = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(text_list)

    text = str(value).strip()
    if not text:
        return ""

    if field_key == "match_time":
        minutes = _coerce_positive_int(text)
        if minutes:
            return f"{minutes} min"

    return text


def _build_dynamic_match_configuration_rules(
    match_settings: Dict[str, Any],
    *,
    runtime_game_key: str,
    runtime_game_slug: str,
) -> List[Dict[str, str]]:
    schema_key, values = _dynamic_match_configuration_values(
        match_settings,
        runtime_game_key=runtime_game_key,
        runtime_game_slug=runtime_game_slug,
    )
    schema = MATCH_CONFIGURATION_SCHEMAS.get(schema_key, [])
    if not schema or not values:
        return []

    signal_keys = MATCH_CONFIGURATION_SCHEMA_SIGNAL_KEYS.get(schema_key, set())
    has_schema_signal = any(key in values for key in signal_keys)
    if not has_schema_signal:
        return []

    cards: List[Dict[str, str]] = []
    for field_key, label in schema:
        if field_key not in values:
            continue
        formatted = _format_dynamic_match_configuration_value(field_key, values.get(field_key))
        if not formatted:
            continue
        cards.append({"title": label, "value": formatted})

    return cards


def _build_match_rules(match: Match, runtime: Dict[str, Any]) -> List[Dict[str, str]]:
    tournament = match.tournament
    game_key = str(runtime.get("pipeline_game_key") or runtime.get("game_slug") or "").lower()
    is_efootball = game_key == "efootball"

    phase_mode = str(runtime.get("phase_mode") or "").lower()
    best_of = int(runtime.get("best_of") or getattr(match, "best_of", 1) or 1)
    map_pool = _safe_string_list(runtime.get("map_pool"))
    check_in_window = _safe_dict(runtime.get("check_in_window"))
    evidence_required = bool(
        _safe_dict(_safe_dict(runtime.get("policy")).get("effective")).get("require_match_evidence")
    )

    tournament_match_settings = _safe_dict(getattr(tournament, "match_settings", {}))
    match_settings: Dict[str, Any] = dict(tournament_match_settings)
    default_match_format = ""
    try:
        cfg = tournament.game_match_config
    except Exception:
        cfg = None

    if cfg:
        if not match_settings:
            match_settings = _safe_dict(getattr(cfg, "match_settings", {}))
        default_match_format = str(getattr(cfg, "default_match_format", "") or "").strip()

    dynamic_rules = _build_dynamic_match_configuration_rules(
        match_settings,
        runtime_game_key=game_key,
        runtime_game_slug=str(runtime.get("game_slug") or ""),
    )
    if dynamic_rules:
        dynamic_rules.append(
            {
                "title": "Result Evidence",
                "value": "Required (image upload)" if evidence_required else "Optional",
            }
        )
        return dynamic_rules

    fallback_duration = None
    allow_draws = None
    overtime_enabled = None
    try:
        game_tournament_cfg = getattr(getattr(tournament, "game", None), "tournament_config", None)
    except Exception:
        game_tournament_cfg = None

    if game_tournament_cfg:
        fallback_duration = _coerce_positive_int(getattr(game_tournament_cfg, "default_match_duration_minutes", None))
        allow_draws = _coerce_optional_bool(getattr(game_tournament_cfg, "allow_draws", None))
        overtime_enabled = _coerce_optional_bool(getattr(game_tournament_cfg, "overtime_enabled", None))

    match_duration = _format_match_duration(match_settings, fallback_minutes=fallback_duration)
    extra_time = _coerce_optional_bool(
        _setting_value(
            match_settings,
            "extra_time",
            "extra_time_enabled",
            "allow_extra_time",
        )
    )
    penalties = _coerce_optional_bool(
        _setting_value(
            match_settings,
            "penalties",
            "penalty_shootout",
            "penalty_shootouts",
            "allow_penalties",
        )
    )
    draws_allowed = _coerce_optional_bool(
        _setting_value(
            match_settings,
            "allow_draws",
            "draw_allowed",
            "draws_allowed",
        )
    )
    if draws_allowed is None:
        draws_allowed = allow_draws

    if extra_time is None:
        extra_time = _coerce_optional_bool(
            _setting_value(
                match_settings,
                "overtime",
                "overtime_enabled",
                "allow_overtime",
            )
        )
    if extra_time is None:
        extra_time = overtime_enabled

    cards: List[Dict[str, str]] = []

    def _append_rule(title: str, value: Any) -> None:
        text = str(value or "").strip()
        if not text:
            return
        cards.append({"title": title, "value": text})

    pipeline_label = "Direct Setup" if phase_mode == "direct" else "Coin Toss -> Veto -> Lobby"
    _append_rule("Pipeline", pipeline_label)
    _append_rule("Match Format", _format_match_format(default_match_format, best_of))
    _append_rule("Check-In", _build_check_in_rule_text(match, check_in_window))
    _append_rule("Result Evidence", "Required (image upload)" if evidence_required else "Optional")

    if is_efootball:
        _append_rule("Platform", _tournament_platform_label(tournament))
        _append_rule("Tournament Mode", _tournament_mode_label(tournament))
        if match_duration:
            _append_rule("Match Time", match_duration)
        if extra_time is not None:
            _append_rule("Extra Time", "Enabled" if extra_time else "Disabled")
        if penalties is not None:
            _append_rule("Penalties", "Enabled" if penalties else "Disabled")
        if draws_allowed is not None:
            _append_rule("Draws", "Allowed" if draws_allowed else "Not Allowed")
    else:
        _append_rule("Map Pool", ", ".join(map_pool) if map_pool else "Managed in lobby")
        if match_duration:
            _append_rule("Match Time", match_duration)

    if match.scheduled_time:
        try:
            scheduled_label = timezone.localtime(match.scheduled_time).strftime("%b %d, %I:%M %p")
        except Exception:
            scheduled_label = match.scheduled_time.isoformat()
    else:
        scheduled_label = "TBD"
    _append_rule("Scheduled", scheduled_label)

    return cards


def _blind_mask_submission(submission: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "submission_id": submission.get("submission_id"),
        "status": submission.get("status"),
        "submitted_at": submission.get("submitted_at"),
        "blind_masked": True,
    }


def _mask_result_submissions_for_view(
    *,
    submissions: Dict[str, Any],
    access: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    normalized_submissions: Dict[str, Optional[Dict[str, Any]]] = {
        "1": _safe_dict(submissions.get("1")) if isinstance(submissions.get("1"), dict) else None,
        "2": _safe_dict(submissions.get("2")) if isinstance(submissions.get("2"), dict) else None,
    }

    is_admin_view = bool(access.get("admin_mode"))
    viewer_side = access.get("user_side") if access.get("user_side") in (1, 2) else None
    both_submitted = isinstance(normalized_submissions.get("1"), dict) and isinstance(normalized_submissions.get("2"), dict)

    masked: Dict[str, Any] = {"1": None, "2": None}

    for side_key in ("1", "2"):
        row = normalized_submissions.get(side_key)
        if not isinstance(row, dict):
            masked[side_key] = None
            continue

        try:
            side_value = int(side_key)
        except (TypeError, ValueError):
            side_value = None

        row_visible = bool(is_admin_view or (viewer_side and viewer_side == side_value))
        masked[side_key] = _safe_dict(row) if row_visible else _blind_mask_submission(row)

    viewer_submission = normalized_submissions.get(str(viewer_side)) if viewer_side in (1, 2) else None
    visibility = {
        "blind_enabled": True,
        "viewer_side": viewer_side,
        "viewer_submitted": bool(isinstance(viewer_submission, dict)),
        "both_submitted": bool(both_submitted),
        "opponent_revealed": bool(is_admin_view),
    }

    return masked, visibility


def _credential_schema_for_game(*, game_key: str, game_slug: str, phase_mode: str) -> List[Dict[str, Any]]:
    if game_key == "efootball" or game_slug == "efootball":
        return deepcopy(EFOOTBALL_CREDENTIAL_SCHEMA)

    if phase_mode == "direct" and game_key in {"eafc", "fc", "fifa"}:
        return deepcopy(EFOOTBALL_CREDENTIAL_SCHEMA)

    return deepcopy(DEFAULT_CREDENTIAL_SCHEMA)


def _credential_schema_keys(schema: Any) -> List[str]:
    keys: List[str] = []
    for row in _safe_list(schema):
        key = str(_safe_dict(row).get("key") or "").strip()
        if key and key not in keys:
            keys.append(key)
    if keys:
        return keys
    return [row["key"] for row in DEFAULT_CREDENTIAL_SCHEMA]


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    token = str(value).strip().lower()
    if token in {"1", "true", "yes", "y", "on"}:
        return True
    if token in {"0", "false", "no", "n", "off", ""}:
        return False
    return bool(default)


def _deep_merge_dict(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge_dict(base[key], value)
        else:
            base[key] = value
    return base


def _default_veto_sequence(best_of: int) -> List[Dict[str, Any]]:
    if best_of >= 3:
        return [
            {"side": 1, "action": "ban"},
            {"side": 2, "action": "ban"},
            {"side": 1, "action": "pick"},
            {"side": 2, "action": "pick"},
            {"side": 1, "action": "ban"},
            {"side": 2, "action": "ban"},
        ]
    return [
        {"side": 1, "action": "ban"},
        {"side": 2, "action": "ban"},
        {"side": 1, "action": "ban"},
        {"side": 2, "action": "ban"},
        {"side": 1, "action": "pick"},
    ]


def _normalize_round_overrides(raw_overrides: Any) -> Dict[str, Dict[str, bool]]:
    if not isinstance(raw_overrides, dict):
        return {}

    normalized: Dict[str, Dict[str, bool]] = {}
    for raw_round, raw_payload in raw_overrides.items():
        round_key = str(raw_round or "").strip()
        if not round_key:
            continue

        if round_key != "*":
            try:
                if int(round_key) < 1:
                    continue
            except (TypeError, ValueError):
                continue

        payload = _safe_dict(raw_payload)
        if not payload:
            continue

        row: Dict[str, bool] = {}
        for field in ("require_check_in", "require_coin_toss", "require_map_veto"):
            if field in payload:
                row[field] = _coerce_bool(payload.get(field), default=False)

        if row:
            normalized[round_key] = row

    return normalized


def _resolve_lobby_policy(match: Match) -> Dict[str, Any]:
    tournament = match.tournament
    game_profile = resolve_lobby_game_profile(getattr(tournament, "game", None))

    config = tournament.config if isinstance(getattr(tournament, "config", None), dict) else {}
    checkin_cfg = config.get("checkin") if isinstance(config.get("checkin"), dict) else {}
    raw_policy = config.get("lobby_policy") if isinstance(config.get("lobby_policy"), dict) else {}

    defaults = {
        "require_check_in": _coerce_bool(getattr(tournament, "enable_check_in", False), default=False),
        "require_coin_toss": bool(game_profile.get("default_require_coin_toss", True)),
        "require_map_veto": bool(game_profile.get("default_require_map_veto", True)),
        "require_match_evidence": False,
    }

    base = apply_lobby_policy_capabilities(
        {
            "require_check_in": _coerce_bool(raw_policy.get("require_check_in"), defaults["require_check_in"]),
            "require_coin_toss": _coerce_bool(raw_policy.get("require_coin_toss"), defaults["require_coin_toss"]),
            "require_map_veto": _coerce_bool(raw_policy.get("require_map_veto"), defaults["require_map_veto"]),
        },
        game_profile,
    )
    base["require_match_evidence"] = _coerce_bool(
        raw_policy.get("require_match_evidence"),
        defaults["require_match_evidence"],
    )

    round_overrides = clamp_lobby_round_overrides(
        _normalize_round_overrides(raw_policy.get("per_round_overrides", {})),
        game_profile,
    )
    per_round = _coerce_bool(raw_policy.get("require_check_in_per_round"), _coerce_bool(checkin_cfg.get("per_round"), False))

    effective = dict(base)
    wildcard = _safe_dict(round_overrides.get("*"))
    exact = _safe_dict(round_overrides.get(str(getattr(match, "round_number", 1))))
    if wildcard:
        effective.update({k: bool(v) for k, v in wildcard.items()})
    if exact:
        effective.update({k: bool(v) for k, v in exact.items()})

    if per_round:
        effective["require_check_in"] = True

    # Base toggles are authoritative disables.
    if not bool(base.get("require_coin_toss")):
        effective["require_coin_toss"] = False
    if not bool(base.get("require_map_veto")):
        effective["require_map_veto"] = False
    effective["require_match_evidence"] = bool(base.get("require_match_evidence"))

    effective = apply_lobby_policy_capabilities(effective, game_profile)
    effective["require_match_evidence"] = bool(base.get("require_match_evidence"))

    return {
        "base": base,
        "effective": effective,
        "check_in_per_round": per_round,
        "round_overrides": round_overrides,
        "capabilities": {
            "phase_mode": str(game_profile.get("phase_mode") or "veto"),
            "supports_coin_toss": bool(game_profile.get("supports_coin_toss", True)),
            "supports_map_veto": bool(game_profile.get("supports_map_veto", True)),
            "canonical_game_key": str(game_profile.get("canonical_game_key") or ""),
            "reference": str(game_profile.get("reference") or ""),
        },
    }


def _resolve_phase_mode(match: Match, game_profile: Dict[str, Any]) -> str:
    canonical_key = str(game_profile.get("canonical_game_key") or "")
    if canonical_key in PIPELINE_OVERRIDES:
        return PIPELINE_OVERRIDES[canonical_key]
    return str(game_profile.get("phase_mode") or "direct")


def _build_phase_order(phase_mode: str, effective_policy: Dict[str, Any]) -> Tuple[List[str], str]:
    phase_order: List[str] = []

    allow_coin_toss = phase_mode in {"veto", "draft"} and bool(effective_policy.get("require_coin_toss"))
    if allow_coin_toss:
        phase_order.append("coin_toss")

    phase1_kind = "none"
    include_phase1 = False

    if phase_mode == "draft":
        include_phase1 = True
        phase1_kind = "draft"
    elif phase_mode == "veto":
        include_phase1 = bool(effective_policy.get("require_map_veto"))
        phase1_kind = "veto" if include_phase1 else "none"
    elif phase_mode == "direct":
        include_phase1 = True
        phase1_kind = "direct"

    if include_phase1:
        phase_order.append("phase1")

    phase_order.extend(["lobby_setup", "live", "results", "completed"])
    normalized = [phase for phase in phase_order if phase in PHASES]
    if not normalized:
        normalized = list(PHASE_FALLBACK_ORDER)

    return normalized, phase1_kind


def _phase_for_match_state(match: Match, phase_order: List[str]) -> str:
    state = str(getattr(match, "state", Match.SCHEDULED))
    if state == Match.LIVE:
        return "live" if "live" in phase_order else phase_order[-1]
    if state == Match.PENDING_RESULT:
        return "results" if "results" in phase_order else phase_order[-1]
    if state in (Match.COMPLETED, Match.FORFEIT, Match.CANCELLED, Match.DISPUTED):
        return "completed" if "completed" in phase_order else phase_order[-1]
    return phase_order[0] if phase_order else "coin_toss"


def _resolve_check_in_window(match: Match, effective_policy: Dict[str, Any]) -> Dict[str, Any]:
    required = bool(effective_policy.get("require_check_in"))
    scheduled_time = getattr(match, "scheduled_time", None)

    opens_at = None
    closes_at = None
    if required:
        closes_at = getattr(match, "check_in_deadline", None)
        if scheduled_time:
            tournament = match.tournament
            open_offset = int(getattr(tournament, "check_in_minutes_before", 0) or 0)
            close_offset = int(getattr(tournament, "check_in_closes_minutes_before", 0) or 0)
            opens_at = scheduled_time - timedelta(minutes=max(0, open_offset))
            if closes_at is None:
                closes_at = scheduled_time - timedelta(minutes=max(0, close_offset))
        if closes_at and opens_at and closes_at < opens_at:
            closes_at = opens_at

    now = timezone.now()
    is_open = bool(required and opens_at and closes_at and opens_at <= now <= closes_at)
    is_pending = bool(required and opens_at and now < opens_at)
    is_closed = bool(required and closes_at and now > closes_at)

    both_checked_in = bool(
        getattr(match, "participant1_checked_in", False)
        and getattr(match, "participant2_checked_in", False)
    )

    return {
        "required": required,
        "opens_at": opens_at.isoformat() if opens_at else None,
        "closes_at": closes_at.isoformat() if closes_at else None,
        "is_open": is_open,
        "is_pending": is_pending,
        "is_closed": is_closed,
        "both_checked_in": both_checked_in,
    }


def _resolve_presence_snapshot(workflow: Dict[str, Any], match: Match) -> Dict[str, Dict[str, Any]]:
    presence_blob = _safe_dict(workflow.get("presence"))
    now = timezone.now()

    result: Dict[str, Dict[str, Any]] = {}
    for side in (1, 2):
        side_key = str(side)
        row = _safe_dict(presence_blob.get(side_key))
        last_seen_raw = str(row.get("last_seen") or "")
        last_seen_dt = parse_datetime(last_seen_raw) if last_seen_raw else None

        is_online = False
        if last_seen_dt:
            try:
                is_online = (now - last_seen_dt).total_seconds() <= PRESENCE_STALE_SECONDS
            except Exception:
                is_online = False

        raw_status = str(row.get("status") or "").strip().lower()
        if not is_online:
            status = "offline"
        elif raw_status == "away":
            status = "away"
        else:
            status = "online"

        checked_in = bool(match.participant1_checked_in if side == 1 else match.participant2_checked_in)
        result[side_key] = {
            "status": status,
            "online": bool(status != "offline"),
            "last_seen": last_seen_raw or None,
            "user_id": row.get("user_id"),
            "checked_in": checked_in,
        }

    return result


def _load_config_map_pool(match: Match) -> List[str]:
    cfg = None
    try:
        cfg = match.tournament.game_match_config
    except Exception:
        cfg = None

    if not cfg:
        return []

    try:
        return [
            row[0]
            for row in cfg.map_pool.filter(is_active=True).order_by("order", "map_name").values_list("map_name")
            if str(row[0] or "").strip()
        ]
    except Exception:
        return []


def _build_default_workflow(
    *,
    match: Match,
    phase_mode: str,
    phase_order: List[str],
    phase1_kind: str,
    policy: Dict[str, Any],
    map_pool: List[str],
    best_of: int,
    lobby_info: Dict[str, Any],
) -> Dict[str, Any]:
    credentials = {
        "lobby_code": str(lobby_info.get("lobby_code") or lobby_info.get("room_number") or lobby_info.get("code") or ""),
        "password": str(lobby_info.get("password") or ""),
        "map": str(lobby_info.get("map") or ""),
        "server": str(lobby_info.get("server") or ""),
        "game_mode": str(lobby_info.get("game_mode") or ""),
        "notes": str(lobby_info.get("notes") or ""),
    }

    return {
        "phase": _phase_for_match_state(match, phase_order),
        "phase_order": list(phase_order),
        "phase1_kind": phase1_kind,
        "mode": phase_mode,
        "policy": policy,
        "coin_toss": {
            "winner_side": None,
            "performed_at": None,
        },
        "veto": {
            "sequence": _default_veto_sequence(best_of),
            "step": 0,
            "pool": list(map_pool),
            "bans": [],
            "picks": [],
            "selected_map": credentials["map"],
            "last_action": None,
        },
        "direct_ready": {"1": False, "2": False},
        "presence": {"1": {}, "2": {}},
        "credentials": credentials,
        "announcements": [],
        "result_submissions": {"1": None, "2": None},
        "result_status": "pending",
        "final_result": None,
    }


def _ensure_match_workflow(match: Match, persist: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], bool]:
    game = getattr(match.tournament, "game", None)
    game_profile = resolve_lobby_game_profile(game)
    game_slug = str(game_profile.get("game_slug") or getattr(game, "slug", "") or "").lower()
    game_key = str(game_profile.get("canonical_game_key") or "")
    phase_mode = _resolve_phase_mode(match, game_profile)

    best_of = int(getattr(match, "best_of", 1) or 1)
    map_pool = _load_config_map_pool(match)
    if not map_pool:
        map_pool = deepcopy(DEFAULT_MAP_POOLS.get(game_key, DEFAULT_MAP_POOLS.get(game_slug, [])))
    if not map_pool:
        map_pool = ["Map 1", "Map 2", "Map 3", "Map 4", "Map 5"]

    policy = _resolve_lobby_policy(match)
    effective_policy = _safe_dict(policy.get("effective"))
    phase_order, phase1_kind = _build_phase_order(phase_mode, effective_policy)

    # Override with GameMatchPipeline if one exists for this game
    pipeline_phases = None
    if game:
        try:
            pipeline = game.match_pipeline
            pipeline_phases = pipeline.get_phase_order()
        except Exception:
            pass
    if pipeline_phases:
        # Map pipeline keys to the legacy phase1 system:
        # "direct_ready" and "map_veto" become "phase1" internally
        mapped = []
        for p in pipeline_phases:
            if p == "direct_ready":
                mapped.append("phase1")
                phase1_kind = "direct"
            elif p == "map_veto":
                mapped.append("phase1")
                phase1_kind = "veto"
            elif p in PHASES:
                mapped.append(p)
        if mapped:
            phase_order = mapped

    check_in_window = _resolve_check_in_window(match, effective_policy)
    credential_schema = _credential_schema_for_game(
        game_key=game_key,
        game_slug=game_slug,
        phase_mode=phase_mode,
    )

    lobby_info = _safe_dict(getattr(match, "lobby_info", {}))
    defaults = _build_default_workflow(
        match=match,
        phase_mode=phase_mode,
        phase_order=phase_order,
        phase1_kind=phase1_kind,
        policy=policy,
        map_pool=map_pool,
        best_of=best_of,
        lobby_info=lobby_info,
    )

    existing = _safe_dict(lobby_info.get(WORKFLOW_KEY))
    # Migration bridge: absorb old key once, then write under new key.
    if not existing and isinstance(lobby_info.get(LEGACY_WORKFLOW_KEY), dict):
        existing = _safe_dict(lobby_info.get(LEGACY_WORKFLOW_KEY))

    workflow = deepcopy(defaults)
    if existing:
        _deep_merge_dict(workflow, existing)

    workflow["mode"] = phase_mode
    workflow["phase_order"] = list(phase_order)
    workflow["phase1_kind"] = phase1_kind
    workflow["policy"] = policy

    presence = _safe_dict(workflow.get("presence"))
    presence.setdefault("1", {})
    presence.setdefault("2", {})
    workflow["presence"] = presence

    current_phase = str(workflow.get("phase") or "")
    state_phase = _phase_for_match_state(match, phase_order)
    if getattr(match, "state", Match.SCHEDULED) in (
        Match.LIVE,
        Match.PENDING_RESULT,
        Match.COMPLETED,
        Match.FORFEIT,
        Match.CANCELLED,
        Match.DISPUTED,
    ):
        workflow["phase"] = state_phase
    elif current_phase not in phase_order:
        workflow["phase"] = state_phase

    changed = False
    if lobby_info.get(WORKFLOW_KEY) != workflow:
        lobby_info[WORKFLOW_KEY] = workflow
        changed = True

    if LEGACY_WORKFLOW_KEY in lobby_info:
        lobby_info.pop(LEGACY_WORKFLOW_KEY, None)
        changed = True

    credentials = _safe_dict(workflow.get("credentials"))
    credentials.setdefault("lobby_code", str(lobby_info.get("lobby_code") or lobby_info.get("room_number") or lobby_info.get("code") or ""))
    credentials.setdefault("password", str(lobby_info.get("password") or ""))
    workflow["credentials"] = credentials
    top_level_pairs = {
        "lobby_code": credentials.get("lobby_code", ""),
        "room_number": credentials.get("lobby_code", ""),
        "code": credentials.get("lobby_code", ""),
        "password": credentials.get("password", ""),
        "map": credentials.get("map", ""),
        "server": credentials.get("server", ""),
        "game_mode": credentials.get("game_mode", ""),
        "notes": credentials.get("notes", ""),
    }
    for key, value in top_level_pairs.items():
        normalized = str(value or "")
        if str(lobby_info.get(key) or "") != normalized:
            lobby_info[key] = normalized
            changed = True

    if persist and changed and hasattr(match, "save"):
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info", "updated_at"])

    presence_snapshot = _resolve_presence_snapshot(workflow, match)
    runtime = {
        "game_name": getattr(game, "display_name", "") or getattr(game, "name", "Game"),
        "game_slug": game_slug,
        "pipeline_game_key": game_key,
        "pipeline_phases": pipeline_phases,
        "phase_mode": phase_mode,
        "credential_schema": credential_schema,
        "best_of": best_of,
        "map_pool": map_pool,
        "phase_order": phase_order,
        "phase1_kind": phase1_kind,
        "policy": policy,
        "check_in_window": check_in_window,
        "presence": presence_snapshot,
    }

    return lobby_info, workflow, runtime, changed


def _resolve_match_room_access(user, match: Match, *, admin_mode_requested: bool = False) -> Dict[str, Any]:
    if not user or not getattr(user, "is_authenticated", False):
        return {
            "allowed": False,
            "is_staff": False,
            "admin_mode": False,
            "user_side": None,
            "user_id": None,
            "denied_reason": "not_authenticated",
            "lobby_opens_at": None,
        }

    is_staff = bool(getattr(user, "is_staff", False) or match.tournament.organizer_id == user.id)
    user_side = None

    if match.participant1_id == user.id:
        user_side = 1
    elif match.participant2_id == user.id:
        user_side = 2
    else:
        try:
            from apps.organizations.models import TeamMembership

            user_team_ids = set(
                TeamMembership.objects.filter(
                    user=user,
                    status=TeamMembership.Status.ACTIVE,
                ).values_list("team_id", flat=True)
            )
            if match.participant1_id in user_team_ids:
                user_side = 1
            elif match.participant2_id in user_team_ids:
                user_side = 2
        except Exception:
            user_side = None

    denied_reason = None
    lobby_opens_at = None
    is_participant = user_side in (1, 2)

    if is_participant and not is_staff:
        state = str(getattr(match, "state", "") or "").lower()
        scheduled_time = getattr(match, "scheduled_time", None)
        if state not in PARTICIPANT_LOBBY_ALWAYS_OPEN_STATES and scheduled_time:
            lobby_opens_at = scheduled_time - timedelta(minutes=PARTICIPANT_LOBBY_OPEN_LEAD_MINUTES)
            if timezone.now() < lobby_opens_at:
                denied_reason = "lobby_not_open"

    return {
        "allowed": bool(is_staff or (is_participant and denied_reason is None)),
        "is_staff": is_staff,
        "admin_mode": bool(is_staff and admin_mode_requested),
        "user_side": user_side,
        "user_id": user.id,
        "denied_reason": denied_reason,
        "lobby_opens_at": lobby_opens_at,
    }


def _fallback_avatar_url(seed: str) -> str:
    token = str(seed or "?").strip()[:2] or "??"
    return f"https://ui-avatars.com/api/?name={token}&background=0A0A0E&color=fff&size=64"


def _normalize_media_url(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if raw.startswith('/media/media/'):
        return '/media/' + raw[len('/media/media/'):]
    if raw.startswith('media/media/'):
        return '/media/' + raw[len('media/media/'):]
    if raw.startswith('media/'):
        return '/media/' + raw[len('media/'):]
    return raw


def _participant_media_map(match: Match) -> Dict[int, str]:
    participant_ids = {int(pid) for pid in (match.participant1_id, match.participant2_id) if pid}
    if not participant_ids:
        return {}

    media_map: Dict[int, str] = {}
    tournament = match.tournament

    if getattr(tournament, "participation_type", "") == "team":
        from apps.organizations.models import Team

        for team in Team.objects.filter(id__in=participant_ids).only("id", "logo"):
            logo_url = ""
            try:
                if team.logo:
                    logo_url = _normalize_media_url(str(team.logo.url or ""))
            except Exception:
                logo_url = ""
            media_map[team.id] = logo_url
        return media_map

    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = User.objects.filter(id__in=participant_ids).select_related("profile")
    for user in users:
        avatar_url = ""
        try:
            profile = getattr(user, "profile", None)
            if profile and profile.avatar:
                avatar_url = _normalize_media_url(str(profile.avatar.url or ""))
        except Exception:
            avatar_url = ""
        media_map[user.id] = avatar_url or _fallback_avatar_url(getattr(user, "username", ""))

    return media_map


def _serialize_match_snapshot(match: Match) -> Dict[str, Any]:
    return {
        "id": match.id,
        "state": match.state,
        "state_display": match.get_state_display(),
        "participant1_score": match.participant1_score,
        "participant2_score": match.participant2_score,
        "winner_id": match.winner_id,
        "loser_id": match.loser_id,
        "participant1_checked_in": bool(match.participant1_checked_in),
        "participant2_checked_in": bool(match.participant2_checked_in),
        "scheduled_time": match.scheduled_time.isoformat() if match.scheduled_time else None,
    }


def _submission_team_id_for_side(match: Match, side: int) -> Optional[int]:
    if side == 1:
        return match.participant1_id
    if side == 2:
        return match.participant2_id
    return None


def _safe_submission_proof_url(submission: MatchResultSubmission) -> str:
    proof = getattr(submission, "proof_screenshot", None)
    if proof:
        try:
            return _normalize_media_url(str(proof.url or ""))
        except Exception:
            pass
    return _normalize_media_url(str(submission.proof_screenshot_url or ""))


def _serialize_side_submission(submission: MatchResultSubmission, side: int) -> Dict[str, Any]:
    payload = _safe_dict(submission.raw_result_payload)
    score_p1 = payload.get("score_p1")
    score_p2 = payload.get("score_p2")

    if score_p1 is None or score_p2 is None:
        score_for = payload.get("score_for")
        score_against = payload.get("score_against")
        if side == 1:
            score_p1 = score_for
            score_p2 = score_against
        else:
            score_p1 = score_against
            score_p2 = score_for

    if side == 1:
        score_for = score_p1
        score_against = score_p2
    else:
        score_for = score_p2
        score_against = score_p1

    return {
        "submission_id": submission.id,
        "status": submission.status,
        "score_for": score_for,
        "score_against": score_against,
        "score_p1": score_p1,
        "score_p2": score_p2,
        "note": str(submission.submitter_notes or ""),
        "proof_screenshot_url": _safe_submission_proof_url(submission),
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
    }


def _side_submission_map(match: Match) -> Dict[int, MatchResultSubmission]:
    teams = {1: match.participant1_id, 2: match.participant2_id}
    team_ids = [tid for tid in teams.values() if tid]
    if not team_ids:
        return {}

    rows = MatchResultSubmission.objects.filter(match=match, submitted_by_team_id__in=team_ids).order_by("-submitted_at")
    resolved: Dict[int, MatchResultSubmission] = {}

    for row in rows:
        for side, team_id in teams.items():
            if team_id and row.submitted_by_team_id == team_id and side not in resolved:
                resolved[side] = row
                break
        if len(resolved) == 2:
            break

    return resolved


def _build_room_payload(
    match: Match,
    access: Dict[str, Any],
    lobby_info: Dict[str, Any],
    workflow: Dict[str, Any],
    runtime: Dict[str, Any],
) -> Dict[str, Any]:
    user_side = access.get("user_side")
    is_host = user_side == 1
    workflow_payload = _safe_dict(workflow)
    workflow_payload["phase_order"] = _safe_list(runtime.get("phase_order"))
    workflow_payload["phase1_kind"] = str(runtime.get("phase1_kind") or workflow_payload.get("phase1_kind") or "none")
    workflow_payload["policy"] = _safe_dict(runtime.get("policy"))
    workflow_payload["check_in_window"] = _safe_dict(runtime.get("check_in_window"))
    workflow_payload["presence"] = _safe_dict(runtime.get("presence"))

    merged_submissions = _safe_dict(workflow_payload.get("result_submissions"))
    for side, submission in _side_submission_map(match).items():
        merged_submissions[str(side)] = _serialize_side_submission(submission, side)
    viewer_submission = merged_submissions.get(str(user_side)) if user_side in (1, 2) else None
    can_submit_result = bool(user_side in (1, 2) and not isinstance(viewer_submission, dict))

    masked_submissions, result_visibility = _mask_result_submissions_for_view(
        submissions=merged_submissions,
        access=access,
    )

    workflow_payload["result_submissions"] = masked_submissions
    workflow_payload["result_visibility"] = result_visibility

    participant_media = _participant_media_map(match)
    match_rules = _build_match_rules(match, runtime)
    admin_suffix = "?admin=1" if access.get("admin_mode") else ""

    return {
        "match": {
            "id": match.id,
            "state": match.state,
            "state_display": match.get_state_display(),
            "round_number": match.round_number,
            "match_number": match.match_number,
            "participant1": {
                "id": match.participant1_id,
                "name": match.participant1_name or "TBD",
                "score": match.participant1_score,
                "checked_in": bool(match.participant1_checked_in),
                "logo_url": participant_media.get(match.participant1_id, ""),
            },
            "participant2": {
                "id": match.participant2_id,
                "name": match.participant2_name or "TBD",
                "score": match.participant2_score,
                "checked_in": bool(match.participant2_checked_in),
                "logo_url": participant_media.get(match.participant2_id, ""),
            },
            "winner_id": match.winner_id,
            "best_of": runtime["best_of"],
            "scheduled_time": match.scheduled_time.isoformat() if match.scheduled_time else None,
            "started_at": match.started_at.isoformat() if match.started_at else None,
            "completed_at": match.completed_at.isoformat() if match.completed_at else None,
        },
        "tournament": {
            "id": match.tournament_id,
            "slug": match.tournament.slug,
            "name": match.tournament.name,
        },
        "game": {
            "name": runtime["game_name"],
            "slug": runtime["game_slug"],
            "pipeline_game_key": runtime.get("pipeline_game_key", ""),
            "pipeline_phases": runtime.get("pipeline_phases") or [],
            "phase_mode": runtime["phase_mode"],
            "map_pool": runtime["map_pool"],
            "credentials_schema": _safe_list(runtime.get("credential_schema")),
            "match_rules": match_rules,
        },
        "lobby": {
            "lobby_code": str(lobby_info.get("lobby_code") or ""),
            "room_number": str(lobby_info.get("lobby_code") or lobby_info.get("room_number") or ""),
            "password": str(lobby_info.get("password") or ""),
            "map": str(lobby_info.get("map") or ""),
            "server": str(lobby_info.get("server") or ""),
            "game_mode": str(lobby_info.get("game_mode") or ""),
            "notes": str(lobby_info.get("notes") or ""),
        },
        "pipeline": {
            "phase_order": workflow_payload.get("phase_order"),
            "phase1_kind": workflow_payload.get("phase1_kind"),
            "policy": workflow_payload.get("policy"),
        },
        "check_in": workflow_payload.get("check_in_window"),
        "presence": workflow_payload.get("presence"),
        "workflow": workflow_payload,
        "me": {
            "user_id": access.get("user_id"),
            "side": user_side,
            "is_host": bool(is_host),
            "is_staff": bool(access.get("is_staff")),
            "admin_mode": bool(access.get("admin_mode")),
            "can_edit_credentials": bool(access.get("is_staff") or is_host),
            "can_submit_result": can_submit_result,
            "can_force_phase": bool(access.get("admin_mode")),
            "can_override_result": bool(access.get("admin_mode")),
            "can_broadcast_system": bool(access.get("admin_mode")),
        },
        "urls": {
            "workflow": reverse("tournaments:match_room_workflow", kwargs={"slug": match.tournament.slug, "match_id": match.id}) + admin_suffix,
            "check_in": reverse("tournaments:match_room_checkin", kwargs={"slug": match.tournament.slug, "match_id": match.id}) + admin_suffix,
            "submit_result": reverse("tournaments:submit_result", kwargs={"slug": match.tournament.slug, "match_id": match.id}),
            "report_dispute": reverse("tournaments:report_dispute", kwargs={"slug": match.tournament.slug, "match_id": match.id}),
            "match_detail": reverse("tournaments:match_detail", kwargs={"slug": match.tournament.slug, "match_id": match.id}),
            "hub": reverse("tournaments:tournament_hub", kwargs={"slug": match.tournament.slug}),
            "bracket": reverse("tournaments:bracket", kwargs={"slug": match.tournament.slug}),
            "support": reverse("tournaments:hub_support_api", kwargs={"slug": match.tournament.slug}),
        },
        "websocket": {
            "path": f"/ws/match/{match.id}/",
        },
    }


def _broadcast_match_room_event(match: Match, event_name: str, payload: Dict[str, Any]) -> None:
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    event = {
        "event": event_name,
        "payload": payload,
        "match_id": match.id,
        "timestamp": timezone.now().isoformat(),
    }

    try:
        async_to_sync(channel_layer.group_send)(
            f"match_{match.id}",
            {
                "type": "match_room_event",
                "data": event,
            },
        )
    except Exception:
        logger.exception("Failed broadcasting match room event", extra={"match_id": match.id, "event": event_name})


class MatchRoomView(LoginRequiredMixin, DetailView):
    """Participant/staff match room."""

    model = Match
    template_name = "tournaments/match_room/room.html"
    context_object_name = "match"
    pk_url_kwarg = "match_id"

    def get_queryset(self):
        tournament_slug = self.kwargs.get("slug")
        return Match.objects.filter(
            tournament__slug=tournament_slug,
            is_deleted=False,
        ).select_related(
            "tournament",
            "tournament__game",
            "tournament__organizer",
        )

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        match_id = self.kwargs.get(self.pk_url_kwarg)
        try:
            return queryset.get(pk=match_id)
        except Match.DoesNotExist as exc:
            raise Http404("Match not found.") from exc

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        admin_mode_requested = _is_truthy(request.GET.get("admin"))
        self.access = _resolve_match_room_access(
            request.user,
            self.object,
            admin_mode_requested=admin_mode_requested,
        )

        if not self.access["allowed"]:
            if self.access.get("denied_reason") == "lobby_not_open":
                opens_at = self.access.get("lobby_opens_at")
                if opens_at:
                    try:
                        opens_at_label = timezone.localtime(opens_at).strftime("%b %d, %I:%M %p")
                    except Exception:
                        opens_at_label = str(opens_at)
                    messages.info(
                        request,
                        f"Match lobby opens at {opens_at_label} (30 minutes before kickoff).",
                    )
                else:
                    messages.info(request, "Match lobby opens 30 minutes before kickoff.")
            else:
                messages.warning(request, "Only match participants and staff can access the match lobby.")
            return redirect(
                "tournaments:match_detail",
                slug=self.object.tournament.slug,
                match_id=self.object.id,
            )

        self.user_side = self.access.get("user_side")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.object

        lobby_info, workflow, runtime, _changed = _ensure_match_workflow(match, persist=True)
        room_payload = _build_room_payload(match, self.access, lobby_info, workflow, runtime)

        context["tournament"] = match.tournament
        context["user_side"] = self.user_side
        context["is_staff_view"] = bool(self.access.get("is_staff"))
        context["room_payload"] = room_payload

        return context


class MatchCheckInView(LoginRequiredMixin, View):
    """POST endpoint for match check-in."""

    def post(self, request, slug, match_id):
        match = get_object_or_404(
            Match,
            id=match_id,
            tournament__slug=slug,
            is_deleted=False,
        )

        if match.state not in (Match.CHECK_IN, Match.SCHEDULED):
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "check_in_unavailable"}, status=400)
            messages.error(request, "Check-in is not available for this match.")
            return redirect("tournaments:match_room", slug=slug, match_id=match_id)

        access = _resolve_match_room_access(request.user, match)
        if not access["allowed"]:
            if access.get("denied_reason") == "lobby_not_open":
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": "lobby_not_open"}, status=403)
                opens_at = access.get("lobby_opens_at")
                if opens_at:
                    try:
                        opens_at_label = timezone.localtime(opens_at).strftime("%b %d, %I:%M %p")
                    except Exception:
                        opens_at_label = str(opens_at)
                    messages.error(request, f"Match lobby opens at {opens_at_label}.")
                else:
                    messages.error(request, "Match lobby opens 30 minutes before kickoff.")
                return redirect("tournaments:match_detail", slug=slug, match_id=match_id)
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": False, "error": "forbidden"}, status=403)
            messages.error(request, "Only participants can check in for this match.")
            return redirect("tournaments:match_detail", slug=slug, match_id=match_id)

        _lobby_info, _workflow, runtime, _changed = _ensure_match_workflow(match, persist=False)
        check_in_window = _safe_dict(runtime.get("check_in_window"))
        if check_in_window.get("required"):
            if check_in_window.get("is_pending"):
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": "check_in_not_open"}, status=400)
                messages.error(request, "Check-in window is not open yet.")
                return redirect("tournaments:match_room", slug=slug, match_id=match_id)

            if check_in_window.get("is_closed"):
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse({"success": False, "error": "check_in_closed"}, status=400)
                messages.error(request, "Check-in window is closed for this match.")
                return redirect("tournaments:match_room", slug=slug, match_id=match_id)

        updated = False
        if access["user_side"] == 1 and not match.participant1_checked_in:
            match.participant1_checked_in = True
            updated = True
        elif access["user_side"] == 2 and not match.participant2_checked_in:
            match.participant2_checked_in = True
            updated = True

        if updated:
            if match.participant1_checked_in and match.participant2_checked_in and match.state in (Match.SCHEDULED, Match.CHECK_IN):
                match.state = Match.READY

            match.save(
                update_fields=[
                    "participant1_checked_in",
                    "participant2_checked_in",
                    "state",
                    "updated_at",
                ]
            )

            lobby_info, workflow, runtime, _ = _ensure_match_workflow(match, persist=True)
            payload = _build_room_payload(match, access, lobby_info, workflow, runtime)
            _broadcast_match_room_event(match, "checkin_updated", {"room": payload})

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "checked_in": True,
                        "both_ready": bool(match.participant1_checked_in and match.participant2_checked_in),
                        "match_state": match.state,
                        "room": payload,
                    }
                )

            messages.success(request, "Check-in successful!")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "checked_in": False, "already_checked_in": True})
            messages.info(request, "Already checked in.")

        return redirect("tournaments:match_room", slug=slug, match_id=match_id)


@method_decorator(csrf_protect, name='dispatch')
class MatchRoomWorkflowView(LoginRequiredMixin, View):
    """JSON API for match lobby workflow actions."""

    def _load_match(self, slug: str, match_id: int) -> Match:
        return get_object_or_404(
            Match.objects.select_related("tournament", "tournament__game", "tournament__organizer"),
            id=match_id,
            tournament__slug=slug,
            is_deleted=False,
        )

    @staticmethod
    def _parse_side(value: Any) -> Optional[int]:
        try:
            side = int(value)
        except (TypeError, ValueError):
            return None
        return side if side in (1, 2) else None

    def _resolve_actor_side(self, access: Dict[str, Any], payload: Dict[str, Any]) -> Optional[int]:
        if access.get("is_staff"):
            explicit_side = self._parse_side(payload.get("acting_side") or payload.get("side"))
            if explicit_side in (1, 2):
                return explicit_side
        return self._parse_side(access.get("user_side"))

    @staticmethod
    def _parse_int(raw_value: Any, field_name: str) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be a number") from exc
        if value < 0:
            raise ValueError(f"{field_name} must be >= 0")
        return value

    def get(self, request, slug, match_id):
        match = self._load_match(slug, match_id)
        access = _resolve_match_room_access(
            request.user,
            match,
            admin_mode_requested=_is_truthy(request.GET.get("admin")),
        )
        if not access["allowed"]:
            if access.get("denied_reason") == "lobby_not_open":
                return JsonResponse({"success": False, "error": "lobby_not_open"}, status=403)
            return JsonResponse({"success": False, "error": "forbidden"}, status=403)

        lobby_info, workflow, runtime, _ = _ensure_match_workflow(match, persist=True)
        payload = _build_room_payload(match, access, lobby_info, workflow, runtime)
        return JsonResponse({"success": True, "room": payload})

    def post(self, request, slug, match_id):
        body: Dict[str, Any] = {}
        files = request.FILES

        content_type = str(request.content_type or "").lower()
        if "application/json" in content_type:
            try:
                parsed = json.loads(request.body or "{}")
                if isinstance(parsed, dict):
                    body = parsed
            except json.JSONDecodeError:
                return JsonResponse({"success": False, "error": "invalid_json"}, status=400)
        else:
            body = dict(request.POST.items())

        action = str(body.get("action") or "").strip().lower()
        if not action:
            return JsonResponse({"success": False, "error": "action_required"}, status=400)

        event_message = "Workflow updated."

        with transaction.atomic():
            match = self._load_match(slug, match_id)
            match = Match.objects.select_for_update().get(pk=match.pk)

            access = _resolve_match_room_access(
                request.user,
                match,
                admin_mode_requested=_is_truthy(request.GET.get("admin")),
            )
            if not access["allowed"]:
                if access.get("denied_reason") == "lobby_not_open":
                    return JsonResponse({"success": False, "error": "lobby_not_open"}, status=403)
                return JsonResponse({"success": False, "error": "forbidden"}, status=403)

            lobby_info, workflow, runtime, _ = _ensure_match_workflow(match, persist=False)

            try:
                changed, event_message = self._apply_action(
                    match=match,
                    access=access,
                    lobby_info=lobby_info,
                    workflow=workflow,
                    runtime=runtime,
                    action=action,
                    payload=body,
                    files=files,
                )
            except ValueError as exc:
                return JsonResponse({"success": False, "error": str(exc)}, status=400)

            if changed:
                match.lobby_info = lobby_info
                match.save(
                    update_fields=[
                        "lobby_info",
                        "state",
                        "started_at",
                        "completed_at",
                        "participant1_score",
                        "participant2_score",
                        "winner_id",
                        "loser_id",
                        "updated_at",
                    ]
                )

        match = self._load_match(slug, match_id)
        access = _resolve_match_room_access(
            request.user,
            match,
            admin_mode_requested=_is_truthy(request.GET.get("admin")),
        )
        lobby_info, workflow, runtime, _ = _ensure_match_workflow(match, persist=False)
        room_payload = _build_room_payload(match, access, lobby_info, workflow, runtime)

        if changed:
            _broadcast_match_room_event(match, "workflow_updated", {"room": room_payload, "message": event_message})

        return JsonResponse(
            {
                "success": True,
                "updated": bool(changed),
                "message": event_message,
                "room": room_payload,
            }
        )

    def _apply_action(
        self,
        *,
        match: Match,
        access: Dict[str, Any],
        lobby_info: Dict[str, Any],
        workflow: Dict[str, Any],
        runtime: Dict[str, Any],
        action: str,
        payload: Dict[str, Any],
        files,
    ) -> Tuple[bool, str]:
        phase = str(workflow.get("phase") or "coin_toss")
        mode = str(workflow.get("mode") or runtime["phase_mode"])
        phase_order = workflow.get("phase_order") if isinstance(workflow.get("phase_order"), list) else runtime.get("phase_order")
        if not isinstance(phase_order, list) or not phase_order:
            phase_order = list(PHASE_FALLBACK_ORDER)

        if phase not in phase_order:
            phase = phase_order[0]
            workflow["phase"] = phase

        policy_effective = _safe_dict(_safe_dict(runtime.get("policy")).get("effective"))
        check_in_window = _safe_dict(runtime.get("check_in_window"))
        actor_side = self._resolve_actor_side(access, payload)
        is_staff = bool(access.get("is_staff"))
        is_admin_mode = bool(access.get("admin_mode"))

        def _next_phase(current_phase: str, fallback: str = "lobby_setup") -> str:
            if current_phase in phase_order:
                idx = phase_order.index(current_phase)
                if idx + 1 < len(phase_order):
                    return str(phase_order[idx + 1])
            if fallback in phase_order:
                return fallback
            return str(phase_order[-1])

        def _assert_checkin_gate() -> None:
            if not bool(policy_effective.get("require_check_in")):
                return
            if is_staff and is_admin_mode:
                return
            if match.participant1_checked_in and match.participant2_checked_in:
                return
            if check_in_window.get("is_pending"):
                raise ValueError("Check-in window has not opened yet.")
            if check_in_window.get("is_closed"):
                raise ValueError("Check-in window is closed and both teams are not checked in.")
            raise ValueError("Both teams must check in before continuing lobby actions.")

        def _latest_submission_for_side(side: int) -> Optional[MatchResultSubmission]:
            team_id = _submission_team_id_for_side(match, side)
            if not team_id:
                return None
            return (
                MatchResultSubmission.objects.filter(match=match, submitted_by_team_id=team_id)
                .order_by("-submitted_at")
                .first()
            )

        def _persist_side_submission(
            *,
            side: int,
            score_for: int,
            score_against: int,
            note: str,
            proof_file,
            proof_url: str,
        ) -> MatchResultSubmission:
            team_id = _submission_team_id_for_side(match, side)
            if not team_id:
                raise ValueError("Unable to resolve participant team for submission.")

            score_p1 = score_for if side == 1 else score_against
            score_p2 = score_against if side == 1 else score_for

            submission_payload = {
                "side": side,
                "score_for": score_for,
                "score_against": score_against,
                "score_p1": score_p1,
                "score_p2": score_p2,
                "submitted_at": timezone.now().isoformat(),
            }

            if _latest_submission_for_side(side):
                raise ValueError("Result already submitted for this side. Contact admin for correction.")

            submission = MatchResultSubmission(
                match=match,
                submitted_by_user_id=access.get("user_id"),
                submitted_by_team_id=team_id,
                source=MatchResultSubmission.SOURCE_MANUAL,
            )

            submission.raw_result_payload = submission_payload
            submission.submitter_notes = note
            submission.status = MatchResultSubmission.STATUS_PENDING
            submission.source = MatchResultSubmission.SOURCE_MANUAL

            if proof_url:
                submission.proof_screenshot_url = proof_url
            if proof_file is not None:
                submission.proof_screenshot = proof_file

            submission.save()
            return submission

        changed = False
        message = "Workflow updated."

        if action in {"presence_ping", "sync_presence"}:
            if actor_side not in (1, 2):
                raise ValueError("Unable to resolve acting side for presence update.")

            presence = _safe_dict(workflow.get("presence"))
            row = _safe_dict(presence.get(str(actor_side)))

            next_status = str(payload.get("status") or "online").strip().lower()
            if next_status not in {"online", "away"}:
                next_status = "online"

            now_iso = timezone.now().isoformat()
            row["user_id"] = access.get("user_id")
            row["status"] = next_status
            row["last_seen"] = now_iso
            presence[str(actor_side)] = row
            workflow["presence"] = presence

            changed = True
            message = "Presence updated."

        elif action == "coin_toss":
            _assert_checkin_gate()
            if mode != "veto":
                raise ValueError("Coin toss is available only for Valorant veto pipeline.")
            if "coin_toss" not in phase_order:
                raise ValueError("Coin toss is disabled by lobby policy.")

            winner_side = self._parse_side(payload.get("winner_side"))
            if winner_side not in (1, 2):
                winner_side = random.choice([1, 2])

            toss = _safe_dict(workflow.get("coin_toss"))
            toss["winner_side"] = winner_side
            toss["performed_at"] = timezone.now().isoformat()
            workflow["coin_toss"] = toss

            if phase == "coin_toss":
                workflow["phase"] = _next_phase("coin_toss")

            changed = True
            message = f"Coin toss resolved. Side {winner_side} won first control."

        elif action == "veto_action":
            _assert_checkin_gate()
            if mode != "veto":
                raise ValueError("This match does not use map veto flow.")
            if str(workflow.get("phase")) == "coin_toss":
                workflow["phase"] = _next_phase("coin_toss")
            if str(workflow.get("phase")) != "phase1":
                raise ValueError("Veto actions are not available in the current phase.")
            if actor_side not in (1, 2):
                raise ValueError("Unable to resolve acting side for veto action.")

            item = str(payload.get("item") or "").strip()
            if not item:
                raise ValueError("Map selection is required.")

            veto = _safe_dict(workflow.get("veto"))
            sequence = veto.get("sequence")
            if not isinstance(sequence, list) or not sequence:
                sequence = _default_veto_sequence(int(runtime["best_of"]))
                veto["sequence"] = sequence

            step = int(veto.get("step") or 0)
            if step >= len(sequence):
                raise ValueError("Veto sequence is already complete.")

            step_info = _safe_dict(sequence[step])
            expected_side = self._parse_side(step_info.get("side")) or 1
            expected_action = str(step_info.get("action") or "ban").strip().lower()
            if expected_action not in {"ban", "pick"}:
                expected_action = "ban"

            if actor_side != expected_side and not is_staff:
                raise ValueError("It is not your turn to act in veto.")

            pool = _safe_string_list(veto.get("pool")) or _safe_string_list(runtime.get("map_pool"))
            bans = _safe_string_list(veto.get("bans"))
            picks = _safe_string_list(veto.get("picks"))
            used = set(bans + picks)
            available = [token for token in pool if token not in used]

            if item not in available:
                raise ValueError("Selected map is not available.")

            if expected_action == "ban":
                bans.append(item)
            else:
                picks.append(item)
                veto["selected_map"] = item

            veto["bans"] = bans
            veto["picks"] = picks
            veto["step"] = step + 1
            veto["last_action"] = {
                "side": actor_side,
                "action": expected_action,
                "item": item,
                "at": timezone.now().isoformat(),
            }

            if not veto.get("selected_map") and veto["step"] >= len(sequence):
                remaining = [token for token in pool if token not in set(bans + picks)]
                if remaining:
                    veto["selected_map"] = remaining[0]
                    if remaining[0] not in picks:
                        picks.append(remaining[0])

            workflow["veto"] = veto

            selected_map = str(veto.get("selected_map") or "")
            if selected_map:
                workflow["phase"] = "lobby_setup" if "lobby_setup" in phase_order else _next_phase("phase1")
                credentials = _safe_dict(workflow.get("credentials"))
                if not str(credentials.get("map") or ""):
                    credentials["map"] = selected_map
                workflow["credentials"] = credentials
                lobby_info["map"] = str(credentials.get("map") or "")

            changed = True
            message = f"Veto updated: side {actor_side} {expected_action}ed {item}."

        elif action == "direct_ready":
            _assert_checkin_gate()
            if mode != "direct":
                raise ValueError("This match does not use direct setup flow.")
            if actor_side not in (1, 2):
                raise ValueError("Unable to resolve acting side for ready check.")

            ready_state = _safe_dict(workflow.get("direct_ready"))
            ready_state.setdefault("1", False)
            ready_state.setdefault("2", False)
            ready_state[str(actor_side)] = bool(payload.get("ready", True))
            workflow["direct_ready"] = ready_state

            if ready_state.get("1") and ready_state.get("2"):
                workflow["phase"] = "lobby_setup" if "lobby_setup" in phase_order else _next_phase("phase1")
            else:
                workflow["phase"] = "phase1"

            changed = True
            message = "Ready status updated."

        elif action == "save_credentials":
            _assert_checkin_gate()
            is_host_actor = actor_side == 1
            if not is_host_actor and not (is_staff and is_admin_mode):
                raise ValueError("Only the host (side 1) can broadcast lobby credentials.")

            credentials = _safe_dict(workflow.get("credentials"))
            schema_keys = _credential_schema_keys(runtime.get("credential_schema"))
            for key in schema_keys:
                if key in payload:
                    credentials[key] = str(payload.get(key) or "").strip()

            workflow["credentials"] = credentials

            lobby_info["lobby_code"] = str(credentials.get("lobby_code") or "")
            lobby_info["room_number"] = str(credentials.get("lobby_code") or "")
            lobby_info["code"] = str(credentials.get("lobby_code") or "")
            lobby_info["password"] = str(credentials.get("password") or "")
            lobby_info["map"] = str(credentials.get("map") or "")
            lobby_info["server"] = str(credentials.get("server") or "")
            lobby_info["game_mode"] = str(credentials.get("game_mode") or "")
            lobby_info["notes"] = str(credentials.get("notes") or "")

            if phase in ("coin_toss", "phase1"):
                workflow["phase"] = "lobby_setup"

            changed = True
            message = "Host broadcasted lobby credentials."

        elif action == "start_live":
            _assert_checkin_gate()
            if actor_side not in (1, 2) and not is_staff:
                raise ValueError("Only participants or staff can start the live phase.")

            workflow["phase"] = "live"
            if match.state in (Match.SCHEDULED, Match.CHECK_IN, Match.READY, Match.PENDING_RESULT):
                match.state = Match.LIVE
            if not match.started_at:
                match.started_at = timezone.now()

            changed = True
            message = "Match marked live."

        elif action == "submit_result":
            if actor_side not in (1, 2):
                raise ValueError("Only participating sides can submit results.")

            if _latest_submission_for_side(actor_side):
                raise ValueError("Result already submitted. You cannot edit it. Contact admin for correction.")

            score_for = self._parse_int(payload.get("score_for"), "score_for")
            score_against = self._parse_int(payload.get("score_against"), "score_against")
            note = str(payload.get("note") or "").strip()
            proof_url = str(payload.get("proof_screenshot_url") or payload.get("evidence_url") or "").strip()
            proof_file = files.get("proof") or files.get("proof_file") or files.get("evidence")
            require_match_evidence = bool(policy_effective.get("require_match_evidence"))

            if require_match_evidence and proof_file is None:
                raise ValueError("Evidence image is required before submitting a result.")

            if proof_file is not None:
                content_type = str(getattr(proof_file, "content_type", "") or "").lower()
                if content_type and not content_type.startswith("image/"):
                    raise ValueError("Only image files are allowed for proof upload.")
                if int(getattr(proof_file, "size", 0) or 0) > 10 * 1024 * 1024:
                    raise ValueError("Proof image exceeds 10MB limit.")

            submission = _persist_side_submission(
                side=actor_side,
                score_for=score_for,
                score_against=score_against,
                note=note,
                proof_file=proof_file,
                proof_url=proof_url,
            )

            submissions = _safe_dict(workflow.get("result_submissions"))
            submissions.setdefault("1", None)
            submissions.setdefault("2", None)
            submissions[str(actor_side)] = _serialize_side_submission(submission, actor_side)
            workflow["result_submissions"] = submissions
            workflow["phase"] = "results"
            workflow["result_status"] = "pending"

            if match.state in (Match.SCHEDULED, Match.CHECK_IN, Match.READY, Match.LIVE):
                match.state = Match.PENDING_RESULT

            side_1 = submissions.get("1")
            side_2 = submissions.get("2")

            if isinstance(side_1, dict) and isinstance(side_2, dict):
                mirrored = (
                    int(side_1.get("score_for", -1)) == int(side_2.get("score_against", -2))
                    and int(side_1.get("score_against", -1)) == int(side_2.get("score_for", -2))
                )

                sub_1 = _latest_submission_for_side(1)
                sub_2 = _latest_submission_for_side(2)

                if mirrored:
                    p1_score = int(side_1.get("score_for", 0))
                    p2_score = int(side_1.get("score_against", 0))
                    match.participant1_score = p1_score
                    match.participant2_score = p2_score

                    if p1_score == p2_score:
                        draw_allowed = _draws_allowed_for_match(match)
                        match.winner_id = None
                        match.loser_id = None

                        if draw_allowed:
                            match.state = Match.COMPLETED
                            if not match.completed_at:
                                match.completed_at = timezone.now()

                            for side_sub in (sub_1, sub_2):
                                if not side_sub:
                                    continue
                                side_sub.status = MatchResultSubmission.STATUS_FINALIZED
                                side_sub.confirmed_at = timezone.now()
                                side_sub.confirmed_by_user_id = access.get("user_id")
                                side_sub.finalized_at = timezone.now()
                                side_sub.save(
                                    update_fields=[
                                        "status",
                                        "confirmed_at",
                                        "confirmed_by_user",
                                        "finalized_at",
                                    ]
                                )

                            workflow["result_status"] = "verified_draw"
                            workflow["phase"] = "completed"
                            workflow["final_result"] = {
                                "participant1_score": p1_score,
                                "participant2_score": p2_score,
                                "winner_side": 0,
                                "result_mode": "draw",
                                "verified_at": timezone.now().isoformat(),
                            }
                            message = "Result verified as draw."
                        else:
                            for side_sub in (sub_1, sub_2):
                                if not side_sub:
                                    continue
                                side_sub.status = MatchResultSubmission.STATUS_CONFIRMED
                                side_sub.confirmed_at = timezone.now()
                                side_sub.confirmed_by_user_id = access.get("user_id")
                                side_sub.save(update_fields=["status", "confirmed_at", "confirmed_by_user"])

                            workflow["result_status"] = "tie_pending_review"
                            workflow["phase"] = "results"
                            match.state = Match.PENDING_RESULT
                            workflow["final_result"] = None
                            message = "Scores match but ended tied. Staff review required."
                    else:
                        winner_side = 1 if p1_score > p2_score else 2
                        winner_id = match.participant1_id if winner_side == 1 else match.participant2_id
                        loser_id = match.participant2_id if winner_side == 1 else match.participant1_id

                        match.winner_id = winner_id
                        match.loser_id = loser_id
                        match.state = Match.COMPLETED
                        if not match.completed_at:
                            match.completed_at = timezone.now()

                        for side_sub in (sub_1, sub_2):
                            if not side_sub:
                                continue
                            side_sub.status = MatchResultSubmission.STATUS_FINALIZED
                            side_sub.confirmed_at = timezone.now()
                            side_sub.confirmed_by_user_id = access.get("user_id")
                            side_sub.finalized_at = timezone.now()
                            side_sub.save(
                                update_fields=[
                                    "status",
                                    "confirmed_at",
                                    "confirmed_by_user",
                                    "finalized_at",
                                ]
                            )

                        workflow["result_status"] = "verified"
                        workflow["phase"] = "completed"
                        workflow["final_result"] = {
                            "participant1_score": p1_score,
                            "participant2_score": p2_score,
                            "winner_side": winner_side,
                            "verified_at": timezone.now().isoformat(),
                        }
                        message = "Result verified and match completed."
                else:
                    for side_sub in (sub_1, sub_2):
                        if not side_sub:
                            continue
                        side_sub.status = MatchResultSubmission.STATUS_DISPUTED
                        side_sub.confirmed_at = timezone.now()
                        side_sub.confirmed_by_user_id = access.get("user_id")
                        side_sub.save(update_fields=["status", "confirmed_at", "confirmed_by_user"])

                    workflow["result_status"] = "mismatch"
                    workflow["phase"] = "results"
                    match.state = Match.PENDING_RESULT
                    message = "Score mismatch detected. Awaiting staff resolution."

            changed = True

        elif action == "admin_override_result":
            if not is_staff or not access.get("admin_mode"):
                raise ValueError("Admin mode is required for score override.")

            p1_score = self._parse_int(payload.get("participant1_score"), "participant1_score")
            p2_score = self._parse_int(payload.get("participant2_score"), "participant2_score")

            match.participant1_score = p1_score
            match.participant2_score = p2_score

            if p1_score == p2_score:
                match.winner_id = None
                match.loser_id = None
                draw_allowed = _draws_allowed_for_match(match)

                if draw_allowed:
                    match.state = Match.COMPLETED
                    if not match.completed_at:
                        match.completed_at = timezone.now()
                    workflow["result_status"] = "admin_overridden_draw"
                    workflow["phase"] = "completed"
                    workflow["final_result"] = {
                        "participant1_score": p1_score,
                        "participant2_score": p2_score,
                        "winner_side": 0,
                        "result_mode": "draw",
                        "verified_at": timezone.now().isoformat(),
                    }
                    message = "Admin override finalized as draw result."
                else:
                    match.state = Match.PENDING_RESULT
                    workflow["result_status"] = "admin_tie_pending_review"
                    workflow["phase"] = "results"
                    workflow["final_result"] = None
                    message = "Admin override saved as tied score."
            else:
                winner_side = 1 if p1_score > p2_score else 2
                match.winner_id = match.participant1_id if winner_side == 1 else match.participant2_id
                match.loser_id = match.participant2_id if winner_side == 1 else match.participant1_id
                match.state = Match.COMPLETED
                if not match.completed_at:
                    match.completed_at = timezone.now()
                workflow["result_status"] = "admin_overridden"
                workflow["phase"] = "completed"
                workflow["final_result"] = {
                    "participant1_score": p1_score,
                    "participant2_score": p2_score,
                    "winner_side": winner_side,
                    "verified_at": timezone.now().isoformat(),
                }
                message = "Admin override finalized the match result."

            submission_status = (
                MatchResultSubmission.STATUS_CONFIRMED
                if p1_score == p2_score and match.state != Match.COMPLETED
                else MatchResultSubmission.STATUS_FINALIZED
            )

            latest_submissions = MatchResultSubmission.objects.filter(match=match).order_by("-submitted_at")[:8]
            for existing in latest_submissions:
                existing.status = submission_status
                existing.confirmed_at = timezone.now()
                existing.confirmed_by_user_id = access.get("user_id")
                if submission_status == MatchResultSubmission.STATUS_FINALIZED:
                    existing.finalized_at = timezone.now()
                existing.save(
                    update_fields=[
                        "status",
                        "confirmed_at",
                        "confirmed_by_user",
                        "finalized_at",
                    ]
                )

            MatchResultSubmission.objects.create(
                match=match,
                submitted_by_user_id=access.get("user_id"),
                submitted_by_team_id=None,
                raw_result_payload={
                    "score_p1": p1_score,
                    "score_p2": p2_score,
                    "admin_override": True,
                    "resolved_at": timezone.now().isoformat(),
                },
                submitter_notes=str(payload.get("note") or "Admin override from match room."),
                status=submission_status,
                source=MatchResultSubmission.SOURCE_ADMIN_OVERRIDE,
                confirmed_at=timezone.now(),
                confirmed_by_user_id=access.get("user_id"),
                finalized_at=timezone.now() if submission_status == MatchResultSubmission.STATUS_FINALIZED else None,
            )

            changed = True

        elif action == "advance_phase":
            if not is_staff or not access.get("admin_mode"):
                raise ValueError("Admin mode is required for forced phase transitions.")
            next_phase = str(payload.get("phase") or "").strip().lower()
            if next_phase not in phase_order:
                raise ValueError("Invalid phase value.")
            workflow["phase"] = next_phase
            changed = True
            message = f"Phase moved to {next_phase}."

        elif action == "system_announcement":
            if not is_staff or not access.get("admin_mode"):
                raise ValueError("Admin mode is required for system announcements.")

            announcement = str(payload.get("message") or payload.get("text") or "").strip()
            if not announcement:
                raise ValueError("Announcement message is required.")
            if len(announcement) > 280:
                raise ValueError("Announcement cannot exceed 280 characters.")

            rows = _safe_list(workflow.get("announcements"))
            rows.append(
                {
                    "message": announcement,
                    "by_user_id": access.get("user_id"),
                    "at": timezone.now().isoformat(),
                }
            )
            workflow["announcements"] = rows[-30:]

            changed = True
            message = f"System announcement: {announcement}"

        else:
            raise ValueError("Unsupported action.")

        if str(workflow.get("phase") or "") not in phase_order:
            workflow["phase"] = _phase_for_match_state(match, phase_order)

        workflow["phase_order"] = list(phase_order)
        workflow["phase1_kind"] = str(runtime.get("phase1_kind") or workflow.get("phase1_kind") or "none")
        workflow["policy"] = _safe_dict(runtime.get("policy"))
        workflow["check_in_window"] = _safe_dict(runtime.get("check_in_window"))
        lobby_info[WORKFLOW_KEY] = workflow

        return changed, message
