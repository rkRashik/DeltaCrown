"""
Premium Match Room / Lobby.

Provides a dynamic, stateful match lobby with:
- Participant/staff access control
- Coin toss + map veto/hero draft/direct ready flow
- Lobby credential management
- Live match transition
- Dual-side result submission and verification
- Realtime event broadcasts to match WebSocket room

URL: /tournaments/<slug>/matches/<match_id>/room/
"""

from __future__ import annotations

from datetime import timedelta
import json
import logging
import random
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView

from apps.tournaments.models import Match, MatchResultSubmission

logger = logging.getLogger(__name__)

WORKFLOW_KEY = "premium_lobby_workflow"

DRAFT_GAME_KEYS = {
    "dota2",
    "mlbb",
    "leagueoflegends",
    "lol",
}

DIRECT_GAME_KEYS = {
    "pubg",
    "pubgm",
    "pubgmobile",
    "freefire",
    "apexlegends",
    "fifa",
    "fc26",
    "efootball",
}

DEFAULT_MAP_POOLS = {
    "valorant": ["Ascent", "Bind", "Haven", "Split", "Icebox", "Lotus", "Sunset"],
    "cs2": ["Mirage", "Inferno", "Dust II", "Nuke", "Overpass", "Vertigo", "Ancient"],
    "r6": ["Clubhouse", "Coastline", "Border", "Kafe", "Villa", "Chalet"],
    "codm": ["Hijacked", "Standoff", "Nuketown", "Scrapyard", "Crash"],
    "rocketleague": ["DFH Stadium", "Mannfield", "Champions Field", "Utopia Coliseum", "AquaDome"],
    "pubgmobile": ["Erangel", "Miramar", "Sanhok", "Vikendi"],
    "freefire": ["Bermuda", "Purgatory", "Kalahari", "Alpine"],
}

DEFAULT_HERO_POOLS = {
    "dota2": [
        "Anti-Mage", "Axe", "Bane", "Crystal Maiden", "Earthshaker", "Juggernaut",
        "Mirana", "Pudge", "Storm Spirit", "Windranger", "Lion", "Lina",
        "Shadow Shaman", "Lich", "Enigma", "Sven",
    ],
    "mlbb": [
        "Aldous", "Angela", "Aurora", "Chou", "Claude", "Diggie", "Esmeralda",
        "Fanny", "Franco", "Granger", "Gusion", "Harith", "Johnson", "Kagura",
        "Khufra", "Layla",
    ],
    "leagueoflegends": [
        "Ahri", "Ashe", "Caitlyn", "Darius", "Ezreal", "Jinx", "Lee Sin", "Leona",
        "Lux", "Orianna", "Renekton", "Thresh", "Vayne", "Yasuo", "Zed", "Vi",
    ],
}

PHASES = {
    "coin_toss",
    "phase1",
    "lobby_setup",
    "live",
    "results",
    "completed",
}

PHASE_FALLBACK_ORDER = ["coin_toss", "phase1", "lobby_setup", "live", "results", "completed"]
PRESENCE_STALE_SECONDS = 45

RESULT_SUBMISSION_EDITABLE_STATUSES = {
    MatchResultSubmission.STATUS_PENDING,
    MatchResultSubmission.STATUS_CONFIRMED,
    MatchResultSubmission.STATUS_DISPUTED,
    MatchResultSubmission.STATUS_AUTO_CONFIRMED,
}


def _is_truthy(value: Any) -> bool:
    token = str(value or "").strip().lower()
    return token in {"1", "true", "yes", "y", "on"}


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


def _safe_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_list_of_strings(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    normalized = []
    for item in value:
        token = str(item or "").strip()
        if token:
            normalized.append(token)
    return normalized


def _normalize_game_slug(raw_slug: str) -> str:
    return str(raw_slug or "").strip().lower().replace("_", "-")


def _compact_game_key(raw_slug: str) -> str:
    return _normalize_game_slug(raw_slug).replace("-", "")


def _default_veto_sequence(best_of: int) -> List[Dict[str, Any]]:
    if best_of >= 5:
        return [
            {"side": 1, "action": "ban"},
            {"side": 2, "action": "ban"},
            {"side": 1, "action": "pick"},
            {"side": 2, "action": "pick"},
            {"side": 1, "action": "pick"},
            {"side": 2, "action": "pick"},
            {"side": 1, "action": "ban"},
            {"side": 2, "action": "ban"},
        ]
    if best_of == 3:
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


def _default_draft_sequence() -> List[Dict[str, Any]]:
    return [
        {"side": 1, "action": "ban"},
        {"side": 2, "action": "ban"},
        {"side": 1, "action": "ban"},
        {"side": 2, "action": "ban"},
        {"side": 1, "action": "pick"},
        {"side": 2, "action": "pick"},
        {"side": 2, "action": "pick"},
        {"side": 1, "action": "pick"},
        {"side": 1, "action": "pick"},
        {"side": 2, "action": "pick"},
    ]


def _determine_phase_mode(match: Match) -> str:
    game = getattr(match.tournament, "game", None)
    game_slug = _normalize_game_slug(getattr(game, "slug", ""))
    game_key = _compact_game_key(game_slug)

    if game_key in DRAFT_GAME_KEYS:
        return "draft"

    category = str(getattr(game, "category", "") or "").upper()
    game_type = str(getattr(game, "game_type", "") or "").upper()
    if (
        game_key in DIRECT_GAME_KEYS
        or category in {"BR", "SPORTS"}
        or game_type in {"BATTLE_ROYALE", "FREE_FOR_ALL"}
    ):
        return "direct"

    return "veto"


def _load_config_pools(match: Match) -> Tuple[List[str], List[str]]:
    map_pool: List[str] = []
    hero_pool: List[str] = []

    cfg = None
    try:
        cfg = match.tournament.game_match_config
    except Exception:
        cfg = None

    if cfg is None:
        return map_pool, hero_pool

    try:
        map_pool = [
            row[0]
            for row in cfg.map_pool.filter(is_active=True).order_by("order", "map_name").values_list("map_name")
            if str(row[0] or "").strip()
        ]
    except Exception:
        map_pool = []

    settings_blob = cfg.match_settings if isinstance(cfg.match_settings, dict) else {}
    hero_pool = _safe_list_of_strings(settings_blob.get("hero_pool") or settings_blob.get("heroes") or [])

    return map_pool, hero_pool


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

        row = _safe_dict(raw_payload)
        if not row:
            continue

        normalized_row: Dict[str, bool] = {}
        for field in ("require_check_in", "require_coin_toss", "require_map_veto"):
            if field in row:
                normalized_row[field] = _coerce_bool(row.get(field), default=False)

        if normalized_row:
            normalized[round_key] = normalized_row

    return normalized


def _resolve_lobby_policy(match: Match) -> Dict[str, Any]:
    tournament = match.tournament
    game = getattr(tournament, "game", None)
    game_category = str(getattr(game, "category", "") or "").upper()

    config = tournament.config if isinstance(tournament.config, dict) else {}
    checkin_cfg = config.get("checkin") if isinstance(config.get("checkin"), dict) else {}
    raw_policy = config.get("lobby_policy") if isinstance(config.get("lobby_policy"), dict) else {}

    defaults = {
        "require_check_in": _coerce_bool(getattr(tournament, "enable_check_in", False), default=False),
        "require_coin_toss": bool(game_category not in {"BR", "SPORTS"}),
        "require_map_veto": bool(game_category not in {"BR", "SPORTS"}),
    }

    base = {
        "require_check_in": _coerce_bool(raw_policy.get("require_check_in"), defaults["require_check_in"]),
        "require_coin_toss": _coerce_bool(raw_policy.get("require_coin_toss"), defaults["require_coin_toss"]),
        "require_map_veto": _coerce_bool(raw_policy.get("require_map_veto"), defaults["require_map_veto"]),
    }

    per_round = _coerce_bool(raw_policy.get("require_check_in_per_round"), _coerce_bool(checkin_cfg.get("per_round"), False))
    round_overrides = _normalize_round_overrides(raw_policy.get("per_round_overrides", {}))

    effective = dict(base)
    wildcard_override = _safe_dict(round_overrides.get("*"))
    if wildcard_override:
        effective.update({k: bool(v) for k, v in wildcard_override.items()})

    exact_override = _safe_dict(round_overrides.get(str(match.round_number)))
    if exact_override:
        effective.update({k: bool(v) for k, v in exact_override.items()})

    if per_round:
        effective["require_check_in"] = True

    return {
        "base": base,
        "effective": effective,
        "check_in_per_round": per_round,
        "round_overrides": round_overrides,
    }


def _fallback_avatar_url(seed: str) -> str:
    token = str(seed or "?").strip()[:2] or "??"
    return f"https://ui-avatars.com/api/?name={token}&background=0A0A0E&color=fff&size=64"


def _participant_media_map(match: Match) -> Dict[int, str]:
    participant_ids = {
        int(pid)
        for pid in (match.participant1_id, match.participant2_id)
        if pid
    }
    if not participant_ids:
        return {}

    tournament = match.tournament
    media_map: Dict[int, str] = {}

    if getattr(tournament, "participation_type", "") == "team":
        from apps.organizations.models import Team

        for team in Team.objects.filter(id__in=participant_ids).only("id", "logo"):
            logo_url = ""
            try:
                if hasattr(team, "logo") and team.logo:
                    logo_url = str(team.logo.url or "")
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
                avatar_url = str(profile.avatar.url or "")
        except Exception:
            avatar_url = ""
        media_map[user.id] = avatar_url or _fallback_avatar_url(getattr(user, "username", ""))

    return media_map


def _build_phase_order(phase_mode: str, effective_policy: Dict[str, Any]) -> Tuple[List[str], str]:
    phase_order: List[str] = []

    if bool(effective_policy.get("require_coin_toss")):
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

    # Ensure we only expose known phases and preserve order.
    normalized_order = [phase for phase in phase_order if phase in PHASES]
    if not normalized_order:
        normalized_order = list(PHASE_FALLBACK_ORDER)

    return normalized_order, phase1_kind


def _phase_for_match_state(match: Match, phase_order: List[str]) -> str:
    if match.state == Match.LIVE:
        return "live" if "live" in phase_order else phase_order[-1]
    if match.state == Match.PENDING_RESULT:
        return "results" if "results" in phase_order else phase_order[-1]
    if match.state in (Match.COMPLETED, Match.FORFEIT, Match.CANCELLED, Match.DISPUTED):
        return "completed" if "completed" in phase_order else phase_order[-1]
    return phase_order[0] if phase_order else "coin_toss"


def _resolve_check_in_window(match: Match, effective_policy: Dict[str, Any]) -> Dict[str, Any]:
    required = bool(effective_policy.get("require_check_in"))
    scheduled_time = match.scheduled_time

    opens_at = None
    closes_at = None
    if required:
        closes_at = match.check_in_deadline
        if scheduled_time:
            open_offset = int(getattr(match.tournament, "check_in_minutes_before", 0) or 0)
            close_offset = int(getattr(match.tournament, "check_in_closes_minutes_before", 0) or 0)
            opens_at = scheduled_time - timedelta(minutes=max(0, open_offset))
            if closes_at is None:
                closes_at = scheduled_time - timedelta(minutes=max(0, close_offset))
        if closes_at and opens_at and closes_at < opens_at:
            closes_at = opens_at

    now = timezone.now()
    is_open = bool(required and opens_at and closes_at and opens_at <= now <= closes_at)
    is_pending = bool(required and opens_at and now < opens_at)
    is_closed = bool(required and closes_at and now > closes_at)

    return {
        "required": required,
        "opens_at": opens_at.isoformat() if opens_at else None,
        "closes_at": closes_at.isoformat() if closes_at else None,
        "is_open": is_open,
        "is_pending": is_pending,
        "is_closed": is_closed,
        "both_checked_in": bool(match.participant1_checked_in and match.participant2_checked_in),
    }


def _resolve_presence_snapshot(workflow: Dict[str, Any], match: Match) -> Dict[str, Dict[str, Any]]:
    presence_blob = _safe_dict(workflow.get("presence"))
    now = timezone.now()

    result: Dict[str, Dict[str, Any]] = {}
    for side in (1, 2):
        key = str(side)
        entry = _safe_dict(presence_blob.get(key))
        last_seen_raw = str(entry.get("last_seen") or "")
        last_seen_dt = parse_datetime(last_seen_raw) if last_seen_raw else None

        is_online = False
        if last_seen_dt:
            try:
                is_online = (now - last_seen_dt).total_seconds() <= PRESENCE_STALE_SECONDS
            except Exception:
                is_online = False

        raw_status = str(entry.get("status") or "").strip().lower()
        if not is_online:
            status = "offline"
        elif raw_status == "away":
            status = "away"
        else:
            status = "online"

        result[key] = {
            "status": status,
            "online": bool(status != "offline"),
            "last_seen": last_seen_raw or None,
            "user_id": entry.get("user_id"),
            "checked_in": bool(match.participant1_checked_in if side == 1 else match.participant2_checked_in),
        }

    return result


def _build_auto_forfeit_hook(match: Match, check_in_window: Dict[str, Any], effective_policy: Dict[str, Any]) -> Dict[str, Any]:
    tournament = match.tournament
    enabled = bool(getattr(tournament, "auto_forfeit_no_shows", False) or getattr(tournament, "enable_no_show_timer", False))
    armed = bool(
        enabled
        and bool(effective_policy.get("require_check_in"))
        and check_in_window.get("is_closed")
        and not check_in_window.get("both_checked_in")
    )
    return {
        "enabled": enabled,
        "armed": armed,
        "task": "apps.tournaments.tasks.check_no_show_matches",
        "timeout_minutes": int(getattr(tournament, "no_show_timeout_minutes", 10) or 10),
        "mode": "scheduled_task",
    }


def _deep_merge_dict(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge_dict(base[key], value)
        else:
            base[key] = value
    return base


def _build_default_workflow(
    match: Match,
    phase_mode: str,
    phase_order: List[str],
    phase1_kind: str,
    policy: Dict[str, Any],
    map_pool: List[str],
    hero_pool: List[str],
    best_of: int,
    lobby_info: Dict[str, Any],
) -> Dict[str, Any]:
    credentials = {
        "lobby_code": str(lobby_info.get("lobby_code") or lobby_info.get("code") or ""),
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
            "pool": map_pool,
            "bans": [],
            "picks": [],
            "selected_map": credentials["map"],
            "last_action": None,
        },
        "draft": {
            "sequence": _default_draft_sequence(),
            "step": 0,
            "pool": hero_pool,
            "bans": [],
            "picks": {"1": [], "2": []},
            "last_action": None,
        },
        "direct_ready": {"1": False, "2": False},
        "presence": {"1": {}, "2": {}},
        "auto_forfeit_hook": {
            "enabled": False,
            "armed": False,
            "task": "apps.tournaments.tasks.check_no_show_matches",
            "mode": "scheduled_task",
        },
        "credentials": credentials,
        "result_submissions": {"1": None, "2": None},
        "result_status": "pending",
        "final_result": None,
    }


def _ensure_match_workflow(match: Match, persist: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], bool]:
    game = getattr(match.tournament, "game", None)
    game_slug = _normalize_game_slug(getattr(game, "slug", ""))
    game_key = _compact_game_key(game_slug)
    phase_mode = _determine_phase_mode(match)
    best_of = int(getattr(match, "best_of", 1) or 1)

    cfg_maps, cfg_heroes = _load_config_pools(match)

    map_pool = cfg_maps
    hero_pool = cfg_heroes

    if not map_pool:
        map_pool = deepcopy(DEFAULT_MAP_POOLS.get(game_key, DEFAULT_MAP_POOLS.get(game_slug, [])))
    if not hero_pool:
        hero_pool = deepcopy(DEFAULT_HERO_POOLS.get(game_key, DEFAULT_HERO_POOLS.get(game_slug, [])))

    if not map_pool:
        map_pool = ["Map 1", "Map 2", "Map 3", "Map 4", "Map 5"]

    lobby_policy = _resolve_lobby_policy(match)
    effective_policy = _safe_dict(lobby_policy.get("effective"))
    phase_order, phase1_kind = _build_phase_order(phase_mode, effective_policy)
    check_in_window = _resolve_check_in_window(match, effective_policy)
    auto_forfeit_hook = _build_auto_forfeit_hook(match, check_in_window, effective_policy)

    lobby_info = _safe_dict(match.lobby_info)
    defaults = _build_default_workflow(
        match=match,
        phase_mode=phase_mode,
        phase_order=phase_order,
        phase1_kind=phase1_kind,
        policy=lobby_policy,
        map_pool=map_pool,
        hero_pool=hero_pool,
        best_of=best_of,
        lobby_info=lobby_info,
    )

    existing = lobby_info.get(WORKFLOW_KEY)
    workflow = deepcopy(defaults)
    if isinstance(existing, dict):
        _deep_merge_dict(workflow, existing)

    # Canonical runtime-derived keys always win over stored values.
    workflow["mode"] = phase_mode
    workflow["phase_order"] = list(phase_order)
    workflow["phase1_kind"] = phase1_kind
    workflow["policy"] = lobby_policy
    workflow["auto_forfeit_hook"] = auto_forfeit_hook

    presence = _safe_dict(workflow.get("presence"))
    presence.setdefault("1", {})
    presence.setdefault("2", {})
    workflow["presence"] = presence

    current_phase = str(workflow.get("phase") or "")
    state_phase = _phase_for_match_state(match, phase_order)
    if match.state in (Match.LIVE, Match.PENDING_RESULT, Match.COMPLETED, Match.FORFEIT, Match.CANCELLED, Match.DISPUTED):
        workflow["phase"] = state_phase
    elif current_phase not in phase_order:
        workflow["phase"] = state_phase

    changed = False

    if lobby_info.get(WORKFLOW_KEY) != workflow:
        lobby_info[WORKFLOW_KEY] = workflow
        changed = True

    credentials = _safe_dict(workflow.get("credentials"))

    top_level_pairs = {
        "lobby_code": credentials.get("lobby_code", ""),
        "code": credentials.get("lobby_code", ""),
        "password": credentials.get("password", ""),
        "map": credentials.get("map", ""),
        "server": credentials.get("server", ""),
        "game_mode": credentials.get("game_mode", ""),
    }
    for key, value in top_level_pairs.items():
        normalized = str(value or "")
        if str(lobby_info.get(key) or "") != normalized:
            lobby_info[key] = normalized
            changed = True

    if persist and changed:
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info", "updated_at"])

    presence_snapshot = _resolve_presence_snapshot(workflow, match)

    runtime = {
        "game_name": getattr(game, "display_name", "") or getattr(game, "name", "Game"),
        "game_slug": game_slug,
        "phase_mode": phase_mode,
        "best_of": best_of,
        "map_pool": map_pool,
        "hero_pool": hero_pool,
        "phase_order": phase_order,
        "phase1_kind": phase1_kind,
        "policy": lobby_policy,
        "check_in_window": check_in_window,
        "presence": presence_snapshot,
        "auto_forfeit_hook": auto_forfeit_hook,
    }

    return lobby_info, workflow, runtime, changed


def _resolve_match_room_access(user, match: Match, *, admin_mode_requested: bool = False) -> Dict[str, Any]:
    if not user or not user.is_authenticated:
        return {
            "allowed": False,
            "is_staff": False,
            "user_side": None,
            "user_id": None,
        }

    is_staff = bool(user.is_staff or match.tournament.organizer_id == user.id)
    user_side = None

    if match.participant1_id == user.id:
        user_side = 1
    elif match.participant2_id == user.id:
        user_side = 2
    else:
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

    return {
        "allowed": bool(is_staff or user_side in (1, 2)),
        "is_staff": is_staff,
        "admin_mode": bool(is_staff and admin_mode_requested),
        "user_side": user_side,
        "user_id": user.id,
    }


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
            return str(proof.url or "")
        except Exception:
            pass
    return str(submission.proof_screenshot_url or "")


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
    teams = {
        1: match.participant1_id,
        2: match.participant2_id,
    }
    team_ids = [tid for tid in teams.values() if tid]
    if not team_ids:
        return {}

    rows = (
        MatchResultSubmission.objects.filter(match=match, submitted_by_team_id__in=team_ids)
        .order_by("-submitted_at")
    )

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
    workflow_payload = _safe_dict(workflow)
    phase_order = runtime.get("phase_order") if isinstance(runtime.get("phase_order"), list) else list(PHASE_FALLBACK_ORDER)

    workflow_payload["phase_order"] = phase_order
    workflow_payload["phase1_kind"] = str(runtime.get("phase1_kind") or workflow_payload.get("phase1_kind") or "none")
    workflow_payload["policy"] = _safe_dict(runtime.get("policy"))
    workflow_payload["check_in_window"] = _safe_dict(runtime.get("check_in_window"))
    workflow_payload["presence"] = _safe_dict(runtime.get("presence"))
    workflow_payload["auto_forfeit_hook"] = _safe_dict(runtime.get("auto_forfeit_hook"))
    participant_media = _participant_media_map(match)

    merged_submissions = _safe_dict(workflow_payload.get("result_submissions"))
    for side, submission in _side_submission_map(match).items():
        merged_submissions[str(side)] = _serialize_side_submission(submission, side)
    if merged_submissions:
        workflow_payload["result_submissions"] = merged_submissions

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
            "phase_mode": runtime["phase_mode"],
            "map_pool": runtime["map_pool"],
            "hero_pool": runtime["hero_pool"],
        },
        "lobby": {
            "lobby_code": str(lobby_info.get("lobby_code") or ""),
            "password": str(lobby_info.get("password") or ""),
            "map": str(lobby_info.get("map") or ""),
            "server": str(lobby_info.get("server") or ""),
            "game_mode": str(lobby_info.get("game_mode") or ""),
        },
        "pipeline": {
            "phase_order": phase_order,
            "phase1_kind": workflow_payload.get("phase1_kind"),
            "policy": workflow_payload.get("policy"),
            "auto_forfeit_hook": workflow_payload.get("auto_forfeit_hook"),
        },
        "check_in": workflow_payload.get("check_in_window"),
        "presence": workflow_payload.get("presence"),
        "announcements": lobby_info.get("system_announcements") if isinstance(lobby_info.get("system_announcements"), list) else [],
        "workflow": workflow_payload,
        "me": {
            "user_id": access.get("user_id"),
            "side": user_side,
            "is_staff": bool(access.get("is_staff")),
            "admin_mode": bool(access.get("admin_mode")),
            "can_edit_credentials": bool(access.get("is_staff") or user_side == 1),
            "can_submit_result": bool(access.get("is_staff") or user_side in (1, 2)),
            "can_force_phase": bool(access.get("admin_mode")),
            "can_override_result": bool(access.get("admin_mode")),
            "can_broadcast_system": bool(access.get("admin_mode")),
        },
        "urls": {
            "workflow": reverse("tournaments:match_room_workflow", kwargs={"slug": match.tournament.slug, "match_id": match.id}) + admin_suffix,
            "check_in": reverse("tournaments:match_room_checkin", kwargs={"slug": match.tournament.slug, "match_id": match.id}) + admin_suffix,
            "submit_result": reverse("tournaments:submit_result", kwargs={"slug": match.tournament.slug, "match_id": match.id}),
            "report_dispute": reverse("tournaments:report_dispute", kwargs={"slug": match.tournament.slug, "match_id": match.id}),
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
    """Participant/staff premium match room."""

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

        # Keep legacy context keys for any shared partials/legacy snippets.
        context["lobby_code"] = str(lobby_info.get("lobby_code") or "")
        context["lobby_password"] = str(lobby_info.get("password") or "")
        context["lobby_map"] = str(lobby_info.get("map") or "")
        context["lobby_server"] = str(lobby_info.get("server") or "")
        context["lobby_game_mode"] = str(lobby_info.get("game_mode") or "")
        context["lobby_raw"] = lobby_info
        context["countdown_target"] = match.scheduled_time.isoformat() if match.scheduled_time else None
        context["checkin_deadline"] = match.check_in_deadline.isoformat() if match.check_in_deadline else None

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
            if match.is_both_checked_in and match.state in (Match.SCHEDULED, Match.CHECK_IN):
                match.state = Match.READY

            match.save(update_fields=[
                "participant1_checked_in",
                "participant2_checked_in",
                "state",
                "updated_at",
            ])

            lobby_info, workflow, runtime, _ = _ensure_match_workflow(match, persist=True)
            payload = _build_room_payload(match, access, lobby_info, workflow, runtime)
            _broadcast_match_room_event(match, "checkin_updated", {"room": payload})

            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({
                    "success": True,
                    "checked_in": True,
                    "both_ready": match.is_both_checked_in,
                    "match_state": match.state,
                    "room": payload,
                })

            messages.success(request, "Check-in successful!")
        else:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "checked_in": False, "already_checked_in": True})
            messages.info(request, "Already checked in.")

        return redirect("tournaments:match_room", slug=slug, match_id=match_id)


class MatchRoomWorkflowView(LoginRequiredMixin, View):
    """JSON API for premium lobby workflow actions."""

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
                match.save(update_fields=[
                    "lobby_info",
                    "state",
                    "started_at",
                    "completed_at",
                    "participant1_score",
                    "participant2_score",
                    "winner_id",
                    "loser_id",
                    "updated_at",
                ])

        # Rebuild payload after commit.
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

        return JsonResponse({
            "success": True,
            "updated": bool(changed),
            "message": event_message,
            "room": room_payload,
        })

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

            submission = _latest_submission_for_side(side)
            if submission and submission.status not in RESULT_SUBMISSION_EDITABLE_STATUSES:
                submission = None

            if submission is None:
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

        if action == "presence_ping":
            if actor_side not in (1, 2):
                raise ValueError("Unable to resolve acting side for presence update.")

            presence = _safe_dict(workflow.get("presence"))
            side_key = str(actor_side)
            current_row = _safe_dict(presence.get(side_key))

            next_status = str(payload.get("status") or "online").strip().lower()
            if next_status not in {"online", "away"}:
                next_status = "online"

            now_dt = timezone.now()
            now_iso = now_dt.isoformat()
            previous_seen = parse_datetime(str(current_row.get("last_seen") or ""))

            should_persist = True
            if previous_seen:
                try:
                    recent = (now_dt - previous_seen).total_seconds() < 20
                    same_status = str(current_row.get("status") or "") == next_status
                    same_user = current_row.get("user_id") == access.get("user_id")
                    if recent and same_status and same_user:
                        should_persist = False
                except Exception:
                    should_persist = True

            if should_persist:
                current_row["user_id"] = access.get("user_id")
                current_row["status"] = next_status
                current_row["last_seen"] = now_iso
                presence[side_key] = current_row
                workflow["presence"] = presence
                changed = True

            message = "Presence updated."

        elif action == "coin_toss":
            _assert_checkin_gate()
            if "coin_toss" not in phase_order:
                raise ValueError("Coin toss is disabled for this lobby policy.")

            winner_side = self._parse_side(payload.get("winner_side"))
            if winner_side not in (1, 2):
                winner_side = random.choice([1, 2])

            coin_toss = _safe_dict(workflow.get("coin_toss"))
            coin_toss["winner_side"] = winner_side
            coin_toss["performed_at"] = timezone.now().isoformat()
            workflow["coin_toss"] = coin_toss

            if phase == "coin_toss":
                workflow["phase"] = _next_phase("coin_toss")

            changed = True
            message = f"Coin toss resolved. Side {winner_side} won first control."

        elif action == "veto_action":
            _assert_checkin_gate()
            if mode != "veto":
                raise ValueError("This match does not use map veto flow.")

            if not bool(policy_effective.get("require_map_veto", True)):
                raise ValueError("Map veto is disabled for this lobby policy.")

            if phase == "coin_toss":
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
            if expected_action not in ("ban", "pick"):
                expected_action = "ban"

            if actor_side != expected_side and not is_staff:
                raise ValueError("It is not your turn to act in veto.")

            pool = _safe_list_of_strings(veto.get("pool")) or _safe_list_of_strings(runtime.get("map_pool"))
            bans = _safe_list_of_strings(veto.get("bans"))
            picks = _safe_list_of_strings(veto.get("picks"))
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

        elif action == "draft_action":
            _assert_checkin_gate()
            if mode != "draft":
                raise ValueError("This match does not use hero draft flow.")

            if phase == "coin_toss":
                workflow["phase"] = _next_phase("coin_toss")

            if str(workflow.get("phase")) != "phase1":
                raise ValueError("Draft actions are not available in the current phase.")

            if actor_side not in (1, 2):
                raise ValueError("Unable to resolve acting side for draft action.")

            item = str(payload.get("item") or "").strip()
            if not item:
                raise ValueError("Hero selection is required.")

            draft = _safe_dict(workflow.get("draft"))
            sequence = draft.get("sequence")
            if not isinstance(sequence, list) or not sequence:
                sequence = _default_draft_sequence()
                draft["sequence"] = sequence

            step = int(draft.get("step") or 0)
            if step >= len(sequence):
                raise ValueError("Draft sequence is already complete.")

            step_info = _safe_dict(sequence[step])
            expected_side = self._parse_side(step_info.get("side")) or 1
            expected_action = str(step_info.get("action") or "ban").strip().lower()
            if expected_action not in ("ban", "pick"):
                expected_action = "ban"

            if actor_side != expected_side and not is_staff:
                raise ValueError("It is not your turn to act in draft.")

            pool = _safe_list_of_strings(draft.get("pool")) or _safe_list_of_strings(runtime.get("hero_pool"))
            bans = _safe_list_of_strings(draft.get("bans"))
            picks = _safe_dict(draft.get("picks"))
            picks_side_1 = _safe_list_of_strings(picks.get("1"))
            picks_side_2 = _safe_list_of_strings(picks.get("2"))
            used = set(bans + picks_side_1 + picks_side_2)
            available = [token for token in pool if token not in used]

            if item not in available:
                raise ValueError("Selected hero is not available.")

            if expected_action == "ban":
                bans.append(item)
            else:
                if actor_side == 1:
                    picks_side_1.append(item)
                else:
                    picks_side_2.append(item)

            draft["bans"] = bans
            draft["picks"] = {"1": picks_side_1, "2": picks_side_2}
            draft["step"] = step + 1
            draft["last_action"] = {
                "side": actor_side,
                "action": expected_action,
                "item": item,
                "at": timezone.now().isoformat(),
            }

            if draft["step"] >= len(sequence):
                workflow["phase"] = "lobby_setup" if "lobby_setup" in phase_order else _next_phase("phase1")

            workflow["draft"] = draft

            changed = True
            message = f"Draft updated: side {actor_side} {expected_action}ed {item}."

        elif action == "direct_ready":
            _assert_checkin_gate()
            if mode != "direct":
                raise ValueError("This match does not use direct ready flow.")
            if "phase1" not in phase_order:
                raise ValueError("Direct ready phase is disabled for this lobby policy.")
            if actor_side not in (1, 2):
                raise ValueError("Unable to resolve acting side for ready check.")

            ready_state = _safe_dict(workflow.get("direct_ready"))
            ready_state[str(actor_side)] = bool(payload.get("ready", True))
            ready_state.setdefault("1", False)
            ready_state.setdefault("2", False)
            workflow["direct_ready"] = ready_state

            if ready_state.get("1") and ready_state.get("2"):
                workflow["phase"] = "lobby_setup" if "lobby_setup" in phase_order else _next_phase("phase1")
            else:
                workflow["phase"] = "phase1"

            changed = True
            message = "Ready status updated."

        elif action == "save_credentials":
            _assert_checkin_gate()
            if not is_staff and actor_side != 1:
                raise ValueError("Only the host side or staff can update lobby credentials.")

            credentials = _safe_dict(workflow.get("credentials"))
            writable = {
                "lobby_code": "lobby_code",
                "password": "password",
                "map": "map",
                "server": "server",
                "game_mode": "game_mode",
                "notes": "notes",
            }
            for key, payload_key in writable.items():
                if payload_key in payload:
                    credentials[key] = str(payload.get(payload_key) or "").strip()

            workflow["credentials"] = credentials

            lobby_info["lobby_code"] = str(credentials.get("lobby_code") or "")
            lobby_info["code"] = str(credentials.get("lobby_code") or "")
            lobby_info["password"] = str(credentials.get("password") or "")
            lobby_info["map"] = str(credentials.get("map") or "")
            lobby_info["server"] = str(credentials.get("server") or "")
            lobby_info["game_mode"] = str(credentials.get("game_mode") or "")

            if phase in ("coin_toss", "phase1"):
                workflow["phase"] = "lobby_setup" if "lobby_setup" in phase_order else _next_phase(phase)

            changed = True
            message = "Lobby credentials updated."

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

            score_for = self._parse_int(payload.get("score_for"), "score_for")
            score_against = self._parse_int(payload.get("score_against"), "score_against")
            note = str(payload.get("note") or "").strip()
            proof_url = str(payload.get("proof_screenshot_url") or payload.get("evidence_url") or "").strip()
            proof_file = files.get("proof") or files.get("proof_file") or files.get("evidence")

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
                        match.winner_id = None
                        match.loser_id = None
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
                            side_sub.save(update_fields=[
                                "status",
                                "confirmed_at",
                                "confirmed_by_user",
                                "finalized_at",
                            ])

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
                if p1_score == p2_score
                else MatchResultSubmission.STATUS_FINALIZED
            )

            latest_submissions = MatchResultSubmission.objects.filter(match=match).order_by("-submitted_at")[:8]
            for existing in latest_submissions:
                existing.status = submission_status
                existing.confirmed_at = timezone.now()
                existing.confirmed_by_user_id = access.get("user_id")
                if submission_status == MatchResultSubmission.STATUS_FINALIZED:
                    existing.finalized_at = timezone.now()
                existing.save(update_fields=[
                    "status",
                    "confirmed_at",
                    "confirmed_by_user",
                    "finalized_at",
                ])

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

            log_rows = lobby_info.get("system_announcements")
            if not isinstance(log_rows, list):
                log_rows = []
            log_rows.append({
                "message": announcement,
                "by_user_id": access.get("user_id"),
                "at": timezone.now().isoformat(),
            })
            lobby_info["system_announcements"] = log_rows[-30:]

            changed = True
            message = f"System announcement: {announcement}"

        else:
            raise ValueError("Unsupported action.")

        if str(workflow.get("phase") or "") not in phase_order:
            workflow["phase"] = _phase_for_match_state(match, phase_order)

        workflow["phase_order"] = list(phase_order)
        workflow["phase1_kind"] = str(runtime.get("phase1_kind") or workflow.get("phase1_kind") or "none")
        workflow["policy"] = _safe_dict(runtime.get("policy"))
        workflow["auto_forfeit_hook"] = _safe_dict(runtime.get("auto_forfeit_hook"))

        # Persist workflow object back into lobby_info for all successful actions.
        lobby_info[WORKFLOW_KEY] = workflow
        return changed, message
