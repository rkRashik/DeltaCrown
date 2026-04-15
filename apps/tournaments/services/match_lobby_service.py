"""
Match lobby helpers.

Centralizes auto-lobby bootstrap logic for scheduled matches and reminder
marker lifecycle so schedule updates do not leave stale notification state.

Also provides the SINGLE SOURCE OF TRUTH for lobby window state via
``resolve_lobby_state()``.  Every surface (HUB overview, HUB matches tab,
tournament detail, match detail, dashboard, API, JS) MUST derive lobby
state from this helper or its serialised output.
"""

from __future__ import annotations

import secrets
from datetime import timedelta
from typing import Any, Dict, Optional, Tuple

from django.utils import timezone


TERMINAL_MATCH_STATES = {"completed", "forfeit", "cancelled", "disputed"}
FORCED_OPEN_MATCH_STATES = {"ready", "live", "pending_result"}

# ── Lobby policy constants ────────────────────────────────────────────────
LOBBY_OPENS_BEFORE_MINUTES = 30
LOBBY_CLOSES_AFTER_MINUTES = 10

# Canonical lobby states (used as enum values in API / JS)
LOBBY_STATE_UPCOMING = "upcoming_not_open"
LOBBY_STATE_OPEN = "lobby_open"
LOBBY_STATE_LIVE = "live_grace_or_ready"
LOBBY_STATE_CLOSED = "lobby_closed"
LOBBY_STATE_FORFEIT_REVIEW = "forfeit_review"
LOBBY_STATE_COMPLETED = "completed"

MATCH_ROOM_ADMIN_SESSION_KEY = "match_room_admin_tokens"
MATCH_ROOM_ADMIN_TOKEN_TTL_SECONDS = 4 * 60 * 60
MATCH_ROOM_ADMIN_MAX_TOKENS = 48


def resolve_lobby_state(
    match,
    *,
    now: Optional[Any] = None,
) -> Dict[str, Any]:
    """Return canonical lobby window state for *match*.

    This is the **single source of truth**.  Every surface must use this
    (or the serialised dict it returns) instead of ad-hoc time checks.

    Returns dict with keys:
        state           – one of the LOBBY_STATE_* constants
        is_open         – True when participant may enter the lobby
        opens_at        – datetime or None
        closes_at       – datetime or None
        scheduled_at    – match.scheduled_time or None
        minutes_before  – int (policy constant)
        minutes_after   – int (policy constant)
        can_enter       – True if lobby is actionable (open + not terminal)
        can_reschedule  – True if lobby is closed but match is not terminal
        policy_summary  – human-readable one-liner for UI tooltips
    """
    now = now or timezone.now()
    state_raw = str(getattr(match, "state", "") or "").lower()
    scheduled_time = getattr(match, "scheduled_time", None)
    lobby_info = getattr(match, "lobby_info", None) or {}

    base = {
        "scheduled_at": scheduled_time,
        "minutes_before": LOBBY_OPENS_BEFORE_MINUTES,
        "minutes_after": LOBBY_CLOSES_AFTER_MINUTES,
        "policy_summary": (
            f"Lobby opens {LOBBY_OPENS_BEFORE_MINUTES} min before match time "
            f"and closes {LOBBY_CLOSES_AFTER_MINUTES} min after."
        ),
    }

    # ── Terminal states ────────────────────────────────────────
    if state_raw in TERMINAL_MATCH_STATES:
        return {
            **base,
            "state": LOBBY_STATE_COMPLETED,
            "is_open": False,
            "opens_at": None,
            "closes_at": None,
            "can_enter": False,
            "can_reschedule": False,
        }

    # ── Forced-open states (match already in progress) ─────────
    if state_raw in FORCED_OPEN_MATCH_STATES:
        return {
            **base,
            "state": LOBBY_STATE_LIVE,
            "is_open": True,
            "opens_at": None,
            "closes_at": None,
            "can_enter": True,
            "can_reschedule": False,
        }

    # ── Time-based states ──────────────────────────────────────
    if not scheduled_time:
        # No schedule yet => treat as upcoming, not open
        return {
            **base,
            "state": LOBBY_STATE_UPCOMING,
            "is_open": False,
            "opens_at": None,
            "closes_at": None,
            "can_enter": False,
            "can_reschedule": False,
        }

    opens_at = scheduled_time - timedelta(minutes=LOBBY_OPENS_BEFORE_MINUTES)
    closes_at = scheduled_time + timedelta(minutes=LOBBY_CLOSES_AFTER_MINUTES)

    if now < opens_at:
        return {
            **base,
            "state": LOBBY_STATE_UPCOMING,
            "is_open": False,
            "opens_at": opens_at,
            "closes_at": closes_at,
            "can_enter": False,
            "can_reschedule": False,
        }

    if now < closes_at:
        return {
            **base,
            "state": LOBBY_STATE_OPEN,
            "is_open": True,
            "opens_at": opens_at,
            "closes_at": closes_at,
            "can_enter": True,
            "can_reschedule": False,
        }

    # Lobby window has elapsed — check for forfeit / no-show marker
    no_show_marker = lobby_info.get("no_show_auto_dq", False) if isinstance(lobby_info, dict) else False
    if no_show_marker:
        return {
            **base,
            "state": LOBBY_STATE_FORFEIT_REVIEW,
            "is_open": False,
            "opens_at": opens_at,
            "closes_at": closes_at,
            "can_enter": False,
            "can_reschedule": False,
        }

    return {
        **base,
        "state": LOBBY_STATE_CLOSED,
        "is_open": False,
        "opens_at": opens_at,
        "closes_at": closes_at,
        "can_enter": False,
        "can_reschedule": True,
    }


def serialize_lobby_state(lobby: Dict[str, Any]) -> Dict[str, Any]:
    """Convert resolve_lobby_state() output to JSON-safe dict for API."""
    return {
        "lobby_state": lobby["state"],
        "lobby_is_open": lobby["is_open"],
        "lobby_opens_at": lobby["opens_at"].isoformat() if lobby["opens_at"] else None,
        "lobby_closes_at": lobby["closes_at"].isoformat() if lobby["closes_at"] else None,
        "lobby_can_enter": lobby["can_enter"],
        "lobby_can_reschedule": lobby["can_reschedule"],
        "lobby_minutes_before": lobby["minutes_before"],
        "lobby_minutes_after": lobby["minutes_after"],
        "lobby_policy_summary": lobby["policy_summary"],
        "scheduled_at": lobby["scheduled_at"].isoformat() if lobby["scheduled_at"] else None,
    }


def resolve_participant_lobby_access(
    match,
    *,
    now: Optional[Any] = None,
) -> Dict[str, Any]:
    """Return canonical participant entry decision for match-room access.

    This helper maps canonical lobby states to gate-friendly reasons used by
    HTTP and WebSocket access checks.
    """
    lobby = resolve_lobby_state(match, now=now)
    denied_reason = None
    lobby_state = str(lobby.get("state") or "")

    if not lobby.get("can_enter"):
        if lobby_state == LOBBY_STATE_UPCOMING:
            denied_reason = "lobby_not_open"
        elif lobby_state in {LOBBY_STATE_CLOSED, LOBBY_STATE_FORFEIT_REVIEW, LOBBY_STATE_COMPLETED}:
            denied_reason = "lobby_closed"
        else:
            denied_reason = "forbidden"

    return {
        "allowed": denied_reason is None,
        "denied_reason": denied_reason,
        "lobby_state": lobby_state,
        "lobby_opens_at": lobby.get("opens_at"),
        "lobby_closes_at": lobby.get("closes_at"),
        "lobby": lobby,
    }


def _prune_match_room_admin_tokens(raw_tokens: Any, *, now_ts: int) -> Dict[str, Dict[str, int]]:
    if not isinstance(raw_tokens, dict):
        return {}

    normalized: Dict[str, Dict[str, int]] = {}
    for token, payload in raw_tokens.items():
        token_text = str(token or "").strip()
        if not token_text or not isinstance(payload, dict):
            continue

        try:
            issued_ts = int(payload.get("issued_ts") or 0)
            user_id = int(payload.get("user_id") or 0)
            tournament_id = int(payload.get("tournament_id") or 0)
            match_id = int(payload.get("match_id") or 0)
        except (TypeError, ValueError):
            continue

        if issued_ts <= 0 or now_ts - issued_ts > MATCH_ROOM_ADMIN_TOKEN_TTL_SECONDS:
            continue
        if user_id <= 0 or tournament_id <= 0 or match_id <= 0:
            continue

        normalized[token_text] = {
            "issued_ts": issued_ts,
            "user_id": user_id,
            "tournament_id": tournament_id,
            "match_id": match_id,
        }

    if len(normalized) <= MATCH_ROOM_ADMIN_MAX_TOKENS:
        return normalized

    ordered = sorted(
        normalized.items(),
        key=lambda row: int(row[1].get("issued_ts", 0)),
        reverse=True,
    )
    return dict(ordered[:MATCH_ROOM_ADMIN_MAX_TOKENS])


def issue_match_room_admin_token(
    session: Any,
    *,
    user_id: int,
    tournament_id: int,
    match_id: int,
    now: Optional[Any] = None,
) -> str:
    if session is None:
        return ""

    try:
        user_id = int(user_id)
        tournament_id = int(tournament_id)
        match_id = int(match_id)
    except (TypeError, ValueError):
        return ""

    if user_id <= 0 or tournament_id <= 0 or match_id <= 0:
        return ""

    now_ts = int((now or timezone.now()).timestamp())
    tokens = _prune_match_room_admin_tokens(
        session.get(MATCH_ROOM_ADMIN_SESSION_KEY),
        now_ts=now_ts,
    )

    token = secrets.token_urlsafe(24)
    tokens[token] = {
        "issued_ts": now_ts,
        "user_id": user_id,
        "tournament_id": tournament_id,
        "match_id": match_id,
    }

    tokens = _prune_match_room_admin_tokens(tokens, now_ts=now_ts)
    session[MATCH_ROOM_ADMIN_SESSION_KEY] = tokens
    try:
        session.modified = True
    except Exception:
        pass
    return token


def validate_match_room_admin_token(
    session: Any,
    *,
    token: str,
    user_id: int,
    tournament_id: int,
    match_id: int,
    now: Optional[Any] = None,
) -> bool:
    token_text = str(token or "").strip()
    if session is None or not token_text:
        return False

    try:
        user_id = int(user_id)
        tournament_id = int(tournament_id)
        match_id = int(match_id)
    except (TypeError, ValueError):
        return False

    if user_id <= 0 or tournament_id <= 0 or match_id <= 0:
        return False

    now_ts = int((now or timezone.now()).timestamp())
    raw_tokens = session.get(MATCH_ROOM_ADMIN_SESSION_KEY)
    tokens = _prune_match_room_admin_tokens(raw_tokens, now_ts=now_ts)

    if tokens != (raw_tokens if isinstance(raw_tokens, dict) else {}):
        session[MATCH_ROOM_ADMIN_SESSION_KEY] = tokens
        try:
            session.modified = True
        except Exception:
            pass

    payload = tokens.get(token_text)
    if not isinstance(payload, dict):
        return False

    return bool(
        int(payload.get("user_id") or 0) == user_id
        and int(payload.get("tournament_id") or 0) == tournament_id
        and int(payload.get("match_id") or 0) == match_id
    )


REMINDER_MARKERS_KEY = "auto_reminder_marks"


def _normalize_lobby_info(raw: Any) -> Dict[str, Any]:
	if isinstance(raw, dict):
		return dict(raw)
	return {}


def build_match_lobby_code(match) -> str:
	"""Generate a compact lobby code that is stable enough for human use."""
	slug = "".join(ch for ch in str(getattr(match.tournament, "slug", "") or "").upper() if ch.isalnum())
	prefix = (slug[:4] or "DCRN").ljust(4, "X")
	round_part = f"{int(getattr(match, 'round_number', 0) or 0):02d}"
	match_part = f"{int(getattr(match, 'match_number', 0) or 0):03d}"
	entropy = secrets.token_hex(2).upper()
	return f"{prefix}{round_part}{match_part}{entropy}"


def hydrate_match_lobby_info(
	match,
	*,
	create_if_missing: bool = True,
	reset_reminder_marks: bool = False,
) -> Tuple[Dict[str, Any], bool]:
	"""
	Return normalized lobby_info and whether any mutation is required.

	This does not persist to the database. Callers decide when to save.
	"""
	lobby_info = _normalize_lobby_info(getattr(match, "lobby_info", None))
	changed = not isinstance(getattr(match, "lobby_info", None), dict)

	existing_code = str(lobby_info.get("lobby_code") or lobby_info.get("code") or "").strip()
	can_auto_create = (
		create_if_missing
		and not existing_code
		and bool(getattr(match, "scheduled_time", None))
		and str(getattr(match, "state", "")).lower() not in TERMINAL_MATCH_STATES
	)

	if can_auto_create:
		existing_code = build_match_lobby_code(match)
		lobby_info["lobby_code"] = existing_code
		lobby_info["code"] = existing_code
		lobby_info.setdefault("status", "pending")
		lobby_info.setdefault("auto_created", True)
		lobby_info.setdefault("auto_created_at", timezone.now().isoformat())
		changed = True
	elif existing_code:
		if lobby_info.get("lobby_code") != existing_code:
			lobby_info["lobby_code"] = existing_code
			changed = True
		if lobby_info.get("code") != existing_code:
			lobby_info["code"] = existing_code
			changed = True

	if reset_reminder_marks and REMINDER_MARKERS_KEY in lobby_info:
		lobby_info.pop(REMINDER_MARKERS_KEY, None)
		changed = True

	return lobby_info, changed


def ensure_match_lobby_info(
	match,
	*,
	create_if_missing: bool = True,
	reset_reminder_marks: bool = False,
) -> Dict[str, Any]:
	"""Normalize and persist lobby_info when needed, returning final payload."""
	lobby_info, changed = hydrate_match_lobby_info(
		match,
		create_if_missing=create_if_missing,
		reset_reminder_marks=reset_reminder_marks,
	)
	if changed:
		match.lobby_info = lobby_info
		match.save(update_fields=["lobby_info", "updated_at"])
	return lobby_info

