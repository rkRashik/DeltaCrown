"""
1v1 Sports Screenshot Extraction Service — eFootball / EA SPORTS FC 26.

Pipeline (admin uploads a final-whistle screen for a Match in any
SE / DE / RR / Swiss / GP fixture):

    1. Upload the raw image to Supabase Storage as a temporary audit copy.
    2. Send the image inline to Gemini Vision with a strict-shape prompt and
       the names of the two participants as hints. Gemini returns:
           {"home_team": "<str>", "home_score": <int>,
            "away_team": "<str>", "away_score": <int>}
    3. Delete the Supabase object (best-effort, in finally).
    4. Fuzzy-match the AI's home/away pair against ``match.participant1_name``
       and ``match.participant2_name`` so the orchestrator can also return:
           "participant1_score", "participant2_score", "mapping_confidence"
       The frontend uses ``participant{1,2}_score`` to pre-fill the *correct*
       slot inputs when ``mapping_confidence`` is ``"high"`` and otherwise
       surfaces the raw home/away pair so the admin can adjust manually.
    5. Return the merged dict to the caller.

Storage + Gemini plumbing is shared with ``br_screenshot_service`` via
``screenshot_utils``.

Public surface
==============
    process_sports_screenshot(*, tournament, match, image_bytes, content_type,
                              original_filename='') -> dict
    extract_score_via_gemini(image_bytes, content_type, *,
                             participant1_name, participant2_name,
                             game_name='') -> dict   (low-level; no upload/delete)

Re-exports the generic error classes under ``Sports*`` aliases for symmetry
with the BR service.

Env vars (same as screenshot_utils)
===================================
    GEMINI_API_KEY                  required
    SUPABASE_URL                    required
    SUPABASE_SERVICE_KEY            required
    SUPABASE_SCREENSHOTS_BUCKET     optional, default 'screenshots'
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from .screenshot_utils import (
    ScreenshotConfigError as SportsScreenshotConfigError,
    ScreenshotError as SportsScreenshotError,
    ScreenshotExtractionError as SportsScreenshotExtractionError,
    ScreenshotUploadError as SportsScreenshotUploadError,
    build_storage_path,
    call_gemini_vision_json,
    delete_screenshot,
    name_similarity,
    upload_screenshot,
)

logger = logging.getLogger(__name__)

__all__ = [
    "SportsScreenshotConfigError",
    "SportsScreenshotError",
    "SportsScreenshotExtractionError",
    "SportsScreenshotUploadError",
    "extract_score_via_gemini",
    "process_sports_screenshot",
]


# Plausible ceiling for a single sports match. Past this the model almost
# certainly hallucinated; force a manual entry instead of polluting the slot.
_MAX_PLAUSIBLE_SCORE = 30


# ── Prompt + response validation ───────────────────────────────────────────

def _build_prompt(
    p1_name: str,
    p2_name: str,
    game_name: str,
) -> str:
    p1_line = p1_name.strip() if p1_name else "(unknown)"
    p2_line = p2_name.strip() if p2_name else "(unknown)"
    game_line = game_name.strip() if game_name else "eFootball or EA SPORTS FC 26"
    return f"""You are reading a 1v1 sports videogame end-of-match result screen.

Game: {game_line}

The two participants in this fixture are (use these as hints — names on the screen may be club names, manager names, or gamertags that loosely resemble these):
- Team / Player A: {p1_line}
- Team / Player B: {p2_line}

Extract from the screenshot:
1. The HOME team / player name (the side displayed on the left, or labelled "HOME").
2. The HOME final score (goals — integer).
3. The AWAY team / player name (the side displayed on the right, or labelled "AWAY").
4. The AWAY final score (goals — integer).

If the screenshot shows penalty-shootout or extra-time totals, use the FINAL score after all of that. If a number is unreadable, return your best-effort integer (do not guess wildly — small ambiguities only).

Return ONLY a single JSON object with this EXACT shape — no prose, no markdown fences:
{{"home_team": "<string>", "home_score": <int>, "away_team": "<string>", "away_score": <int>}}
"""


def _validate_response(raw: Any) -> Dict[str, Any]:
    """Coerce + validate Gemini's JSON. Raises on shape/value errors."""
    if not isinstance(raw, dict):
        raise SportsScreenshotExtractionError(
            "AI response was not a JSON object.",
            code="bad_shape",
        )

    home_team = raw.get("home_team") or ""
    away_team = raw.get("away_team") or ""
    if not isinstance(home_team, str) or not isinstance(away_team, str):
        raise SportsScreenshotExtractionError(
            "AI returned non-string team names.",
            code="bad_shape",
        )

    try:
        home_score = int(raw.get("home_score"))
        away_score = int(raw.get("away_score"))
    except (TypeError, ValueError) as exc:
        raise SportsScreenshotExtractionError(
            "AI response had non-integer scores.",
            code="bad_shape",
        ) from exc

    if home_score < 0 or away_score < 0:
        raise SportsScreenshotExtractionError(
            "AI returned negative scores.",
            code="bad_values",
        )
    if home_score > _MAX_PLAUSIBLE_SCORE or away_score > _MAX_PLAUSIBLE_SCORE:
        raise SportsScreenshotExtractionError(
            f"AI returned implausibly high scores ({home_score}-{away_score}).",
            code="bad_values",
            details={"home_score": home_score, "away_score": away_score},
        )

    return {
        "home_team": home_team.strip()[:80],
        "home_score": home_score,
        "away_team": away_team.strip()[:80],
        "away_score": away_score,
    }


# ── Fuzzy mapping: home/away → participant1/participant2 ───────────────────

def _map_to_participants(
    parsed: Dict[str, Any],
    p1_name: str,
    p2_name: str,
) -> Dict[str, Any]:
    """
    Decide which side of the AI extraction maps to participant1 vs
    participant2, and return ``(p1_score, p2_score, confidence)``.

    Strategy: score both possible alignments — (home→p1, away→p2) and
    (home→p2, away→p1) — by summing string-similarity ratios. The winning
    alignment dictates the slot mapping. Confidence is graded by the absolute
    score of the best alignment.
    """
    out = {
        "participant1_score": None,
        "participant2_score": None,
        "mapping_confidence": "none",
    }
    if not p1_name and not p2_name:
        return out

    h_to_p1 = name_similarity(parsed["home_team"], p1_name)
    h_to_p2 = name_similarity(parsed["home_team"], p2_name)
    a_to_p1 = name_similarity(parsed["away_team"], p1_name)
    a_to_p2 = name_similarity(parsed["away_team"], p2_name)

    # Two alignments. Each summed ratio is in [0, 2].
    align_a = h_to_p1 + a_to_p2  # home → p1, away → p2
    align_b = h_to_p2 + a_to_p1  # home → p2, away → p1
    best = max(align_a, align_b)

    # Threshold tuning:
    #   sum >= 1.2  → 'high'   (each side likely matched, e.g. 0.6 + 0.6+)
    #   sum >= 0.6  → 'low'    (one side matched, the other was noisy)
    #   sum  < 0.6  → 'none'   (don't auto-fill, let admin choose)
    if best < 0.6:
        return out

    # Tiebreaker: prefer alignment_a on equal sums (deterministic).
    if align_a >= align_b:
        out["participant1_score"] = parsed["home_score"]
        out["participant2_score"] = parsed["away_score"]
    else:
        out["participant1_score"] = parsed["away_score"]
        out["participant2_score"] = parsed["home_score"]

    out["mapping_confidence"] = "high" if best >= 1.2 else "low"
    return out


# ── Public: low-level extraction (no storage round-trip) ───────────────────

def extract_score_via_gemini(
    image_bytes: bytes,
    content_type: str,
    *,
    participant1_name: str,
    participant2_name: str,
    game_name: str = "",
) -> Dict[str, Any]:
    """
    Send the image to Gemini Vision and return:

        {
          "home_team": "...", "home_score": <int>,
          "away_team": "...", "away_score": <int>,
          "participant1_score": <int|None>,
          "participant2_score": <int|None>,
          "mapping_confidence": "high"|"low"|"none",
        }

    Does NOT touch Supabase Storage — for that, use
    ``process_sports_screenshot``. Useful in tests and for unit work.
    """
    prompt = _build_prompt(participant1_name, participant2_name, game_name)
    raw = call_gemini_vision_json(prompt, image_bytes, content_type)
    parsed = _validate_response(raw)
    parsed.update(_map_to_participants(parsed, participant1_name, participant2_name))
    return parsed


# ── Public: top-level orchestrator (upload → extract → delete) ─────────────

def process_sports_screenshot(
    *,
    tournament,
    match,
    image_bytes: bytes,
    content_type: str,
    original_filename: str = "",
) -> Dict[str, Any]:
    """
    End-to-end pipeline. Returns:

        {
          "match_id":   <int>,
          "home_team":  "...",  "home_score": <int>,
          "away_team":  "...",  "away_score": <int>,
          "participant1_name": "...",  "participant1_score": <int|None>,
          "participant2_name": "...",  "participant2_score": <int|None>,
          "mapping_confidence": "high"|"low"|"none",
          "audit": {
            "supabase_path": "...",
            "supabase_url":  "...",
          }
        }

    Raises ``SportsScreenshotError`` (or subclass) on any pipeline failure.
    The Supabase object is deleted in ``finally`` so storage stays clean even
    when Gemini blows up.
    """
    if not image_bytes:
        raise SportsScreenshotError("Empty image upload.", code="empty_upload")

    p1_name = (getattr(match, "participant1_name", "") or "").strip()
    p2_name = (getattr(match, "participant2_name", "") or "").strip()

    game_name = ""
    try:
        game_name = (tournament.game.name if tournament.game_id else "") or ""
    except Exception:
        game_name = ""

    storage_path = ""
    public_url = ""
    parsed: Dict[str, Any] = {}

    try:
        path = build_storage_path(
            "sports",
            f"tournament_{tournament.id}",
            f"match_{match.id}",
            original_filename=original_filename,
        )
        public_url, storage_path = upload_screenshot(
            image_bytes=image_bytes,
            content_type=content_type,
            storage_path=path,
        )
        parsed = extract_score_via_gemini(
            image_bytes=image_bytes,
            content_type=content_type,
            participant1_name=p1_name,
            participant2_name=p2_name,
            game_name=game_name,
        )
    finally:
        if storage_path:
            delete_screenshot(storage_path)

    parsed["match_id"] = match.id
    parsed["participant1_name"] = p1_name
    parsed["participant2_name"] = p2_name
    parsed["audit"] = {
        "supabase_path": storage_path,
        "supabase_url": public_url,
    }
    return parsed
