"""
Match lobby helpers.

Centralizes auto-lobby bootstrap logic for scheduled matches and reminder
marker lifecycle so schedule updates do not leave stale notification state.
"""

from __future__ import annotations

import secrets
from typing import Any, Dict, Tuple

from django.utils import timezone


TERMINAL_MATCH_STATES = {"completed", "forfeit", "cancelled", "disputed"}
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

