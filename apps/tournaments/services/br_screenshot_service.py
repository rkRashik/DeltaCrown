"""
Battle Royale Screenshot Extraction Service.

Pipeline (admin uploads a PUBG Mobile / FreeFire end-of-match screenshot):

    1. Build a candidate list (participant_id -> displayed name) from the
       tournament's Leaderboard GroupStanding rows so Gemini can map names
       to numeric ids.
    2. Upload the raw image to Supabase Storage as a temporary audit copy
       (REST API via ``screenshot_utils.upload_screenshot``).
    3. Send the image bytes inline to the Gemini Vision API together with a
       strict-shape prompt that pins the output schema to the contract used by
       ``BRScoringService.apply_lobby_results``:
           {
             "results": [
               {"participant_id": <int>, "placement": <int>, "kills": <int>}
             ],
             "map_name": "<string>"
           }
    4. Delete the Supabase object (best-effort, runs in finally) so the bucket
       does not accumulate raw screenshots.
    5. Return the parsed dict to the caller. The caller (TOC view) returns it
       to the frontend so the admin can review and edit the grid before the
       *real* submission to ``/brackets/br-score-entry/``.

Storage + Gemini plumbing lives in ``apps.tournaments.services.screenshot_utils``
so the sister sports OCR service can reuse it without code duplication.

Env vars
========
    GEMINI_API_KEY                  required (see screenshot_utils)
    GEMINI_MODEL                    optional, default 'gemini-1.5-flash'
    SUPABASE_URL                    required
    SUPABASE_SERVICE_KEY            required
    SUPABASE_SCREENSHOTS_BUCKET     optional, default 'screenshots'
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .screenshot_utils import (
    ScreenshotConfigError as BRScreenshotConfigError,
    ScreenshotError as BRScreenshotError,
    ScreenshotExtractionError as BRScreenshotExtractionError,
    ScreenshotUploadError as BRScreenshotUploadError,
    build_storage_path,
    call_gemini_vision_json,
    delete_screenshot,
    upload_screenshot,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BRScreenshotConfigError",
    "BRScreenshotError",
    "BRScreenshotExtractionError",
    "BRScreenshotUploadError",
    "build_candidate_list",
    "extract_results_via_gemini",
    "process_br_screenshot",
]


# ── Prompt + response validation ───────────────────────────────────────────

def _build_prompt(
    candidates: List[Tuple[int, str]],
    game_name: str,
    session_number: Optional[int],
) -> str:
    candidate_lines = "\n".join(f"  {pid} : {name}" for pid, name in candidates) or "  (none)"
    session_line = f"\n- Lobby session: #{session_number}" if session_number else ""
    return f"""You are an expert at reading Battle Royale match-result screenshots from games like PUBG Mobile and FreeFire.

Tournament context:
- Game: {game_name}{session_line}

Extract from the screenshot:
1. For each row visible, the team/player's PLACEMENT (final ranking position, integer >= 1).
2. For each row visible, the KILL count (integer >= 0; if not visible, use 0).
3. The MAP NAME if shown anywhere (e.g. "Erangel", "Miramar", "Sanhok", "Vikendi", "Karakin", "Kalahari", "Bermuda", "Purgatory"). Return an empty string if not visible.

Match each row's displayed team/player name to ONE of the candidates below by their participant_id.
Names may not match exactly — use fuzzy matching (case-insensitive, ignore spaces, ignore clan-tag brackets). If a row in the screenshot cannot be matched confidently to ANY candidate, OMIT that row. Each candidate may appear at most once in your output.

Candidates (participant_id : displayed_name):
{candidate_lines}

Return ONLY a single JSON object matching this EXACT shape — no prose, no markdown fences, no explanation:
{{"results": [{{"participant_id": <int>, "placement": <int>, "kills": <int>}}], "map_name": "<string>"}}
"""


def _coerce_results(raw: Any, valid_pids: set) -> Dict[str, Any]:
    """Validate Gemini output shape and drop rows that don't map to a known pid."""
    if not isinstance(raw, dict):
        raise BRScreenshotExtractionError(
            "AI response was not a JSON object.",
            code="bad_shape",
        )

    rows_in = raw.get("results")
    if not isinstance(rows_in, list):
        raise BRScreenshotExtractionError(
            "AI response is missing a 'results' array.",
            code="bad_shape",
        )

    cleaned: List[Dict[str, Any]] = []
    seen_pids: set = set()
    for row in rows_in:
        if not isinstance(row, dict):
            continue
        try:
            pid = int(row.get("participant_id"))
            placement = int(row.get("placement"))
            kills = int(row.get("kills") or 0)
        except (TypeError, ValueError):
            continue
        if pid not in valid_pids or pid in seen_pids:
            continue
        if placement < 1 or kills < 0:
            continue
        seen_pids.add(pid)
        cleaned.append({"participant_id": pid, "placement": placement, "kills": kills})

    map_name = raw.get("map_name") or ""
    if not isinstance(map_name, str):
        map_name = ""
    return {"results": cleaned, "map_name": map_name.strip()[:64]}


def extract_results_via_gemini(
    image_bytes: bytes,
    content_type: str,
    candidates: List[Tuple[int, str]],
    game_name: str,
    session_number: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Call Gemini Vision and parse the response into the BR scoring contract.

    Raises ``BRScreenshotExtractionError`` if the model fails to return parseable
    JSON or the parsed structure is unusable.
    """
    prompt = _build_prompt(candidates, game_name, session_number)
    raw = call_gemini_vision_json(prompt, image_bytes, content_type)
    valid_pids = {pid for pid, _ in candidates}
    return _coerce_results(raw, valid_pids)


# ── Candidate list builder ─────────────────────────────────────────────────

def _label_for_team(team_id: int) -> str:
    try:
        from apps.organizations.models import Team  # type: ignore
        team = Team.objects.only("name", "tag").get(pk=team_id)
        if getattr(team, "tag", None):
            return f"[{team.tag}] {team.name}"
        return team.name or f"Team #{team_id}"
    except Exception:
        return f"Team #{team_id}"


def _label_for_user(user) -> str:
    if user is None:
        return ""
    return (
        getattr(user, "display_name", None)
        or getattr(user, "username", None)
        or getattr(user, "email", None)
        or f"User #{user.pk}"
    )


def build_candidate_list(tournament_id: int) -> List[Tuple[int, str]]:
    """
    Return a list of (participant_id, displayed_name) for every leaderboard
    standing on this tournament, prefixed by team if applicable.

    participant_id matches what BRScoringService treats as the pid:
    team_id when the standing is for a team, else user_id.
    """
    from apps.tournaments.models.group import Group, GroupStanding

    group = (
        Group.objects.filter(tournament_id=tournament_id, is_deleted=False)
        .order_by("display_order", "id")
        .first()
    )
    if not group:
        return []

    standings = GroupStanding.objects.filter(
        group=group, is_deleted=False
    ).select_related("user")

    out: List[Tuple[int, str]] = []
    for s in standings:
        if s.team_id:
            out.append((int(s.team_id), _label_for_team(s.team_id)))
        elif s.user_id:
            out.append((int(s.user_id), _label_for_user(s.user)))
    return out


# ── Top-level orchestrator ─────────────────────────────────────────────────

def process_br_screenshot(
    *,
    tournament,
    match,
    image_bytes: bytes,
    content_type: str,
    original_filename: str = "",
) -> Dict[str, Any]:
    """
    End-to-end pipeline. Returns a dict ready to seed the review grid:

        {
          "results":  [{"participant_id": ..., "placement": ..., "kills": ...}, ...],
          "map_name": "<str>",
          "audit": {
            "supabase_path": "<storage path that briefly held the image>",
            "supabase_url":  "<public URL — empty after delete>",
            "candidates_count": <int>,
            "rows_extracted":   <int>
          }
        }

    Raises ``BRScreenshotError`` (or subclass) on any pipeline failure. The
    Supabase object is deleted in ``finally`` so storage stays clean even when
    Gemini blows up.
    """
    if not image_bytes:
        raise BRScreenshotError("Empty image upload.", code="empty_upload")

    candidates = build_candidate_list(tournament.id)
    if not candidates:
        raise BRScreenshotError(
            "No leaderboard participants exist for this tournament — "
            "generate the BR lobby sessions first.",
            code="no_candidates",
        )

    game_name = ""
    try:
        game_name = (tournament.game.name if tournament.game_id else "") or ""
    except Exception:
        game_name = ""

    session_number = None
    try:
        session_number = (match.lobby_info or {}).get("session_number")
    except Exception:
        session_number = None

    storage_path = ""
    public_url = ""
    parsed: Dict[str, Any] = {}

    try:
        path = build_storage_path(
            "br",
            f"tournament_{tournament.id}",
            f"match_{match.id}",
            original_filename=original_filename,
        )
        public_url, storage_path = upload_screenshot(
            image_bytes=image_bytes,
            content_type=content_type,
            storage_path=path,
        )

        parsed = extract_results_via_gemini(
            image_bytes=image_bytes,
            content_type=content_type,
            candidates=candidates,
            game_name=game_name,
            session_number=session_number,
        )
    finally:
        if storage_path:
            delete_screenshot(storage_path)

    parsed["audit"] = {
        "supabase_path": storage_path,
        "supabase_url": public_url,
        "candidates_count": len(candidates),
        "rows_extracted": len(parsed.get("results") or []),
    }
    return parsed
