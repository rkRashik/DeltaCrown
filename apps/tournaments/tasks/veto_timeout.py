"""
Veto Step Timeout Sweeper (P2.B.3)
==================================

Beat-driven task that scans active match-room workflows for veto steps whose
``step_expires_at`` has passed, and auto-executes the expected action with a
random remaining map. Prevents indefinite stalls when a participant abandons
mid-veto.

State contract
--------------
``match.lobby_info["match_lobby_workflow"]["veto"]`` carries:
  * ``sequence``         — list of ``{side, action}`` steps (1 entry per ban/pick)
  * ``step``             — current 0-indexed step
  * ``pool``             — available map names
  * ``bans``, ``picks``  — already-actioned maps
  * ``time_per_action_seconds`` — per-step countdown (from VetoConfiguration)
  * ``auto_random_on_timeout``  — whether sweeper should act on expiry
  * ``step_expires_at``  — ISO timestamp; populated when a step starts

The sweeper is a pure follower of state set by the HTTP workflow handler. It
NEVER mutates a workflow whose ``auto_random_on_timeout`` is False — that
flag is the per-game opt-out.

Beat schedule
-------------
Every 10 seconds is sufficient: a typical Valorant veto step gives 30s, so
worst-case timeout granularity is ~10s late. Conservative on a single
Celery worker. Adjust in ``deltacrown/celery.py`` if needed.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

# Workflow JSON key — must match WORKFLOW_KEY in match_room.py.
_WORKFLOW_KEY = "match_lobby_workflow"

# Active match states where a veto can still be in progress. Anything past
# LIVE has already left phase1, so there's nothing to time out.
_ACTIVE_STATES = ("scheduled", "check_in", "ready")


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _is_step_expired(veto: Dict[str, Any], now: datetime) -> bool:
    """Return True when the veto step's deadline has passed AND auto fallback is enabled."""
    if not bool(veto.get("auto_random_on_timeout", True)):
        return False
    expires = _parse_iso(veto.get("step_expires_at"))
    if expires is None:
        return False
    return expires <= now


def _expanded_step_seconds(veto: Dict[str, Any]) -> int:
    try:
        seconds = int(veto.get("time_per_action_seconds") or 30)
    except (TypeError, ValueError):
        seconds = 30
    return max(5, seconds)  # guard against pathological config


def _auto_execute_one_step(match, workflow: Dict[str, Any]) -> Optional[str]:
    """Apply ONE expected action with a random available map.

    Returns a short message string for logging, or None when nothing was done.
    Mutates ``workflow`` in place; caller is responsible for persisting.
    """
    veto = workflow.get("veto") or {}
    sequence = veto.get("sequence") or []
    try:
        step_idx = int(veto.get("step") or 0)
    except (TypeError, ValueError):
        step_idx = 0
    if step_idx >= len(sequence):
        # Sequence already complete — clear the timestamp defensively.
        veto["step_expires_at"] = None
        workflow["veto"] = veto
        return None

    step_info = sequence[step_idx] if isinstance(sequence[step_idx], dict) else {}
    try:
        expected_side = int(step_info.get("side") or 1)
    except (TypeError, ValueError):
        expected_side = 1
    expected_action = str(step_info.get("action") or "ban").strip().lower()
    if expected_action not in {"ban", "pick"}:
        expected_action = "ban"

    pool: List[str] = [str(m) for m in (veto.get("pool") or []) if str(m or "").strip()]
    bans: List[str] = list(veto.get("bans") or [])
    picks: List[str] = list(veto.get("picks") or [])
    used = set(bans + picks)
    available = [m for m in pool if m not in used]
    if not available:
        # No map left to pick — abort safely; admin will resolve manually.
        veto["step_expires_at"] = None
        workflow["veto"] = veto
        return None

    chosen = random.choice(available)
    if expected_action == "ban":
        bans.append(chosen)
    else:
        picks.append(chosen)
        if not veto.get("selected_map"):
            veto["selected_map"] = chosen

    veto["bans"] = bans
    veto["picks"] = picks
    veto["step"] = step_idx + 1
    veto["last_action"] = {
        "side": expected_side,
        "action": expected_action,
        "item": chosen,
        "at": timezone.now().isoformat(),
        "auto": True,
    }

    # Decider auto-pick: if the sequence is now complete and no map was
    # picked through the sequence itself, take the first remaining map.
    if veto["step"] >= len(sequence) and not veto.get("selected_map"):
        remaining = [m for m in pool if m not in set(bans + picks)]
        if remaining:
            veto["selected_map"] = remaining[0]
            if remaining[0] not in picks:
                picks.append(remaining[0])
                veto["picks"] = picks

    # Reprime or clear the next step's timer.
    if veto["step"] < len(sequence) and bool(veto.get("auto_random_on_timeout", True)):
        veto["step_expires_at"] = (
            timezone.now() + timedelta(seconds=_expanded_step_seconds(veto))
        ).isoformat()
    else:
        veto["step_expires_at"] = None

    workflow["veto"] = veto

    # If a map is now selected, advance the phase to lobby_setup (same as
    # the HTTP handler does) so participants see the right phase.
    if veto.get("selected_map"):
        phase_order = workflow.get("phase_order") or []
        if "lobby_setup" in phase_order:
            workflow["phase"] = "lobby_setup"
        creds = workflow.get("credentials") or {}
        if not creds.get("map"):
            creds["map"] = veto["selected_map"]
        workflow["credentials"] = creds

    return f"auto-{expected_action}: side {expected_side} → {chosen}"


def _broadcast_workflow_update(match, event_name: str) -> None:
    """Fire the standard ``match_room_event`` broadcast so connected clients
    pull a fresh state snapshot on the next render tick.

    Uses the existing channel-layer pipeline — the FE listens on
    ``match_room_event`` and re-applies the room via ``applyRoom`` (full
    state, idempotent). No new WS payload type introduced.
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        async_to_sync(channel_layer.group_send)(
            f"match_{match.id}",
            {
                "type": "match_room_event",
                "data": {
                    "event": event_name,
                    "payload": {"auto": True},
                    "match_id": match.id,
                    "timestamp": timezone.now().isoformat(),
                },
            },
        )
    except Exception as exc:
        logger.warning("veto_timeout broadcast failed match=%s err=%s",
                       getattr(match, "id", None), exc)


@shared_task(
    name="apps.tournaments.tasks.sweep_veto_timeouts",
    bind=True,
    max_retries=0,
    expires=20,  # don't pile up if the worker is busy — drop stale runs
)
def sweep_veto_timeouts(self) -> Dict[str, int]:
    """Scan active matches for expired veto steps and auto-execute.

    Returns a summary dict for monitoring. Designed to be cheap when no work
    exists: queryset is filtered to active match states, and the per-match
    workflow check is short-circuit.
    """
    from apps.tournaments.models import Match

    now = timezone.now()
    swept = 0
    skipped = 0
    errors = 0

    # Pull only fields we need. `state` field is indexed; `lobby_info` is
    # JSON we have to inspect in Python.
    qs = (
        Match.objects
        .filter(state__in=_ACTIVE_STATES, is_deleted=False)
        .only("id", "lobby_info", "state")
    )

    for match in qs.iterator(chunk_size=200):
        try:
            lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
            workflow = lobby_info.get(_WORKFLOW_KEY)
            if not isinstance(workflow, dict):
                continue
            if str(workflow.get("phase") or "") != "phase1":
                continue
            if str(workflow.get("mode") or "") != "veto":
                continue
            veto = workflow.get("veto")
            if not isinstance(veto, dict):
                continue
            if not _is_step_expired(veto, now):
                skipped += 1
                continue

            note = _auto_execute_one_step(match, workflow)
            if not note:
                skipped += 1
                continue

            lobby_info[_WORKFLOW_KEY] = workflow
            match.lobby_info = lobby_info
            match.save(update_fields=["lobby_info"])
            _broadcast_workflow_update(match, "veto_auto_resolved")

            swept += 1
            logger.info(
                "veto_timeout: auto-resolved step match=%s %s",
                match.id, note,
            )
        except Exception as exc:
            errors += 1
            logger.exception(
                "veto_timeout: sweeper error match=%s err=%s",
                getattr(match, "id", None), exc,
            )

    return {"swept": swept, "skipped": skipped, "errors": errors}
