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
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView

from apps.tournaments.models import Match

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
    if game_key in DIRECT_GAME_KEYS or category == "BR" or game_type == "BATTLE_ROYALE":
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


def _initial_phase_from_match_state(match: Match) -> str:
    if match.state == Match.LIVE:
        return "live"
    if match.state == Match.PENDING_RESULT:
        return "results"
    if match.state in (Match.COMPLETED, Match.FORFEIT, Match.CANCELLED, Match.DISPUTED):
        return "completed"
    return "coin_toss"


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
        "phase": _initial_phase_from_match_state(match),
        "mode": phase_mode,
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

    lobby_info = _safe_dict(match.lobby_info)
    defaults = _build_default_workflow(
        match=match,
        phase_mode=phase_mode,
        map_pool=map_pool,
        hero_pool=hero_pool,
        best_of=best_of,
        lobby_info=lobby_info,
    )

    existing = lobby_info.get(WORKFLOW_KEY)
    workflow = deepcopy(defaults)
    if isinstance(existing, dict):
        _deep_merge_dict(workflow, existing)

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

    runtime = {
        "game_name": getattr(game, "display_name", "") or getattr(game, "name", "Game"),
        "game_slug": game_slug,
        "phase_mode": phase_mode,
        "best_of": best_of,
        "map_pool": map_pool,
        "hero_pool": hero_pool,
    }

    return lobby_info, workflow, runtime, changed


def _resolve_match_room_access(user, match: Match) -> Dict[str, Any]:
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


def _build_room_payload(
    match: Match,
    access: Dict[str, Any],
    lobby_info: Dict[str, Any],
    workflow: Dict[str, Any],
    runtime: Dict[str, Any],
) -> Dict[str, Any]:
    user_side = access.get("user_side")

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
            },
            "participant2": {
                "id": match.participant2_id,
                "name": match.participant2_name or "TBD",
                "score": match.participant2_score,
                "checked_in": bool(match.participant2_checked_in),
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
        "workflow": workflow,
        "me": {
            "user_id": access.get("user_id"),
            "side": user_side,
            "is_staff": bool(access.get("is_staff")),
            "can_edit_credentials": bool(access.get("is_staff") or user_side == 1),
            "can_submit_result": bool(access.get("is_staff") or user_side in (1, 2)),
        },
        "urls": {
            "workflow": reverse("tournaments:match_room_workflow", kwargs={"slug": match.tournament.slug, "match_id": match.id}),
            "check_in": reverse("tournaments:match_room_checkin", kwargs={"slug": match.tournament.slug, "match_id": match.id}),
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
        self.access = _resolve_match_room_access(request.user, self.object)

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
        access = _resolve_match_room_access(request.user, match)
        if not access["allowed"]:
            return JsonResponse({"success": False, "error": "forbidden"}, status=403)

        lobby_info, workflow, runtime, _ = _ensure_match_workflow(match, persist=True)
        payload = _build_room_payload(match, access, lobby_info, workflow, runtime)
        return JsonResponse({"success": True, "room": payload})

    def post(self, request, slug, match_id):
        try:
            body = json.loads(request.body or "{}")
            if not isinstance(body, dict):
                body = {}
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "invalid_json"}, status=400)

        action = str(body.get("action") or "").strip().lower()
        if not action:
            return JsonResponse({"success": False, "error": "action_required"}, status=400)

        event_message = "Workflow updated."

        with transaction.atomic():
            match = self._load_match(slug, match_id)
            match = Match.objects.select_for_update().get(pk=match.pk)

            access = _resolve_match_room_access(request.user, match)
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
        access = _resolve_match_room_access(request.user, match)
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
    ) -> Tuple[bool, str]:
        phase = str(workflow.get("phase") or "coin_toss")
        mode = str(workflow.get("mode") or runtime["phase_mode"])
        actor_side = self._resolve_actor_side(access, payload)
        is_staff = bool(access.get("is_staff"))

        changed = False
        message = "Workflow updated."

        if action == "coin_toss":
            winner_side = self._parse_side(payload.get("winner_side"))
            if winner_side not in (1, 2):
                winner_side = random.choice([1, 2])

            coin_toss = _safe_dict(workflow.get("coin_toss"))
            coin_toss["winner_side"] = winner_side
            coin_toss["performed_at"] = timezone.now().isoformat()
            workflow["coin_toss"] = coin_toss

            if phase == "coin_toss":
                workflow["phase"] = "phase1"

            changed = True
            message = f"Coin toss resolved. Side {winner_side} won first control."

        elif action == "veto_action":
            if mode != "veto":
                raise ValueError("This match does not use map veto flow.")

            if phase == "coin_toss":
                workflow["phase"] = "phase1"

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
                workflow["phase"] = "lobby_setup"
                credentials = _safe_dict(workflow.get("credentials"))
                if not str(credentials.get("map") or ""):
                    credentials["map"] = selected_map
                workflow["credentials"] = credentials
                lobby_info["map"] = str(credentials.get("map") or "")

            changed = True
            message = f"Veto updated: side {actor_side} {expected_action}ed {item}."

        elif action == "draft_action":
            if mode != "draft":
                raise ValueError("This match does not use hero draft flow.")

            if phase == "coin_toss":
                workflow["phase"] = "phase1"

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
                workflow["phase"] = "lobby_setup"

            workflow["draft"] = draft

            changed = True
            message = f"Draft updated: side {actor_side} {expected_action}ed {item}."

        elif action == "direct_ready":
            if mode != "direct":
                raise ValueError("This match does not use direct ready flow.")
            if actor_side not in (1, 2):
                raise ValueError("Unable to resolve acting side for ready check.")

            ready_state = _safe_dict(workflow.get("direct_ready"))
            ready_state[str(actor_side)] = bool(payload.get("ready", True))
            ready_state.setdefault("1", False)
            ready_state.setdefault("2", False)
            workflow["direct_ready"] = ready_state

            if ready_state.get("1") and ready_state.get("2"):
                workflow["phase"] = "lobby_setup"
            else:
                workflow["phase"] = "phase1"

            changed = True
            message = "Ready status updated."

        elif action == "save_credentials":
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
                workflow["phase"] = "lobby_setup"

            changed = True
            message = "Lobby credentials updated."

        elif action == "start_live":
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

            submissions = _safe_dict(workflow.get("result_submissions"))
            submissions.setdefault("1", None)
            submissions.setdefault("2", None)
            submissions[str(actor_side)] = {
                "score_for": score_for,
                "score_against": score_against,
                "note": str(payload.get("note") or "").strip(),
                "submitted_at": timezone.now().isoformat(),
                "submitted_by_side": actor_side,
            }
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

                if mirrored:
                    p1_score = int(side_1.get("score_for", 0))
                    p2_score = int(side_1.get("score_against", 0))
                    match.participant1_score = p1_score
                    match.participant2_score = p2_score

                    if p1_score == p2_score:
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
                    workflow["result_status"] = "mismatch"
                    workflow["phase"] = "results"
                    match.state = Match.PENDING_RESULT
                    message = "Score mismatch detected. Awaiting staff resolution."

            changed = True

        elif action == "admin_override_result":
            if not is_staff:
                raise ValueError("Only staff can override results.")

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

            changed = True

        elif action == "advance_phase":
            if not is_staff:
                raise ValueError("Only staff can force phase transitions.")
            next_phase = str(payload.get("phase") or "").strip().lower()
            if next_phase not in PHASES:
                raise ValueError("Invalid phase value.")
            workflow["phase"] = next_phase
            changed = True
            message = f"Phase moved to {next_phase}."

        else:
            raise ValueError("Unsupported action.")

        # Persist workflow object back into lobby_info for all successful actions.
        lobby_info[WORKFLOW_KEY] = workflow
        return changed, message
