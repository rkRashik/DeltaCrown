"""
5v5 Team Match Screenshot Extraction Service.

Covers MOBA + Tactical Shooter formats:
    Mobile Legends: Bang Bang, Valorant, CS2, Call of Duty.

Pipeline (admin uploads an end-of-match scoreboard from the relevant game):

    1. Resolve the two team participants on the Match (participant1_id /
       participant2_id are team_ids in 5v5 format) and fetch each side's
       active starter roster.
    2. Build a candidate label per player: prefer the per-game ``GameProfile``
       IGN — that's exactly what shows on a Valorant scoreboard or MLBB
       results screen — falling back to the team-roster ``display_name``,
       then the user's display_name / username.
    3. Upload the raw image to Supabase Storage (shared `screenshots` bucket,
       under ``team_5v5/...``) as a temporary audit copy.
    4. Send the image inline to Gemini Vision with a strict-shape prompt and
       both teams' rosters as hints.
    5. Delete the Supabase object (best-effort, in finally).
    6. Fuzzy-match team_a/team_b → participant1/participant2 using
       ``screenshot_utils.name_similarity`` (stdlib SequenceMatcher); within
       each aligned team, fuzzy-match each AI player row to a candidate user
       on that team's roster, dropping rows that already claimed a candidate
       so each user_id appears at most once per team.
    7. Return mapped + raw structures so the frontend can pre-fill its 5v5
       KDA grid for matched players and surface raw IGNs for unmatched rows
       so the admin can correct them manually.

Storage + Gemini plumbing is shared with the BR / sports services via
``screenshot_utils``.

Public surface
==============
    process_team_5v5_screenshot(*, tournament, match, image_bytes, content_type,
                                original_filename='') -> dict
    extract_team_5v5_via_gemini(image_bytes, content_type, *,
                                team_a_name, team_a_candidates,
                                team_b_name, team_b_candidates,
                                game_name='') -> dict   (low-level)

Re-exports the generic error classes under ``Team5v5*`` aliases for symmetry.

Env vars (same as screenshot_utils)
===================================
    GEMINI_API_KEY                  required
    SUPABASE_URL                    required
    SUPABASE_SERVICE_KEY            required
    SUPABASE_SCREENSHOTS_BUCKET     optional, default 'screenshots'
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .screenshot_utils import (
    ScreenshotConfigError as Team5v5ScreenshotConfigError,
    ScreenshotError as Team5v5ScreenshotError,
    ScreenshotExtractionError as Team5v5ScreenshotExtractionError,
    ScreenshotUploadError as Team5v5ScreenshotUploadError,
    build_storage_path,
    call_gemini_vision_json,
    delete_screenshot,
    name_similarity,
    upload_screenshot,
)

logger = logging.getLogger(__name__)

__all__ = [
    "Team5v5ScreenshotConfigError",
    "Team5v5ScreenshotError",
    "Team5v5ScreenshotExtractionError",
    "Team5v5ScreenshotUploadError",
    "build_team_rosters",
    "extract_team_5v5_via_gemini",
    "process_team_5v5_screenshot",
]


# Hallucination ceilings — anything past these is a model failure.
_MAX_KDA = 99
_MAX_TEAM_SCORE = 200          # Valorant rare 30+, MLBB kills sum, etc.
_MAX_PLAYER_SCORE = 200_000    # Covers MLBB gold (~30k typical), CoD score, etc.
_TEAM_SIZE = 5


# ── Player roster candidate builder ─────────────────────────────────────────

def _label_for_player(passport_ign: str, membership_display: str, user) -> str:
    """Pick the best human-readable label for a roster player."""
    if passport_ign:
        return passport_ign
    if membership_display:
        return membership_display
    if user is not None:
        return (
            getattr(user, "display_name", None)
            or getattr(user, "username", None)
            or f"User #{user.pk}"
        )
    return "Unknown"


def build_team_rosters(
    tournament,
    participant1_id: Optional[int],
    participant2_id: Optional[int],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Return ``(team1_candidates, team2_candidates)``. Each element is a list of
    candidate dicts:

        {"user_id": <int>, "label": "<displayed name>"}

    Empty list = team_id was None or the team had no active starters. The AI
    can still extract IGNs in that case; the mapping step just won't find any
    user_ids.
    """
    from apps.organizations.models import TeamMembership
    from apps.user_profile.services.game_passport_service import GamePassportService

    game_slug = ""
    try:
        game_slug = (tournament.game.slug if tournament.game_id else "") or ""
    except Exception:
        game_slug = ""

    def _roster(team_id: Optional[int]) -> List[Dict[str, Any]]:
        if not team_id:
            return []
        try:
            memberships = list(
                TeamMembership.objects.filter(
                    team_id=team_id,
                    status=TeamMembership.Status.ACTIVE,
                    roster_slot="STARTER",
                ).select_related("user")
            )
        except Exception as exc:
            logger.warning("team_5v5: roster fetch failed team_id=%s err=%s", team_id, exc)
            return []

        if not memberships:
            return []

        # Bulk-fetch passports for this game in one query.
        passport_map: Dict[int, Any] = {}
        if game_slug:
            try:
                user_ids = [m.user_id for m in memberships if m.user_id]
                passport_map = (
                    GamePassportService.get_passports_bulk(user_ids, game_slug) or {}
                )
            except Exception as exc:
                logger.warning(
                    "team_5v5: passport bulk fetch failed game=%s err=%s",
                    game_slug, exc,
                )
                passport_map = {}

        out: List[Dict[str, Any]] = []
        for m in memberships:
            if not m.user_id:
                continue
            passport = passport_map.get(m.user_id)
            ign = (getattr(passport, "ign", None) or "") if passport else ""
            label = _label_for_player(
                passport_ign=ign,
                membership_display=(m.display_name or "").strip(),
                user=m.user,
            )
            out.append({"user_id": int(m.user_id), "label": label})
        return out

    return _roster(participant1_id), _roster(participant2_id)


# ── Prompt builder ─────────────────────────────────────────────────────────

def _format_candidate_block(name: str, candidates: List[Dict[str, Any]]) -> str:
    if not candidates:
        return f"  {name or '(unknown)'}: (no roster on file — extract IGNs as best you can)"
    lines = [f"  {name or '(unknown)'}:"]
    lines += [f"    - {c['label']}" for c in candidates]
    return "\n".join(lines)


def _build_prompt(
    team_a_name: str,
    team_a_candidates: List[Dict[str, Any]],
    team_b_name: str,
    team_b_candidates: List[Dict[str, Any]],
    game_name: str,
) -> str:
    game_line = game_name.strip() if game_name else "MLBB / Valorant / CS2 / Call of Duty"
    a_block = _format_candidate_block(team_a_name, team_a_candidates)
    b_block = _format_candidate_block(team_b_name, team_b_candidates)
    return f"""You are reading a 5v5 competitive match end-of-game scoreboard from a MOBA or tactical shooter.

Game: {game_line}

The two teams in this fixture are (use these as hints for what you should see on the scoreboard):
{a_block}
{b_block}

Extract from the screenshot:
1. The two TEAM names exactly as displayed.
2. Each team's final SCORE — for tactical shooters this is rounds won (e.g. 13 for Valorant/CS2); for MOBAs use total kills if score isn't shown; for CoD use the team's score number.
3. For EACH player on EACH team (5 players per team), extract:
   - "name": the IGN exactly as displayed on the scoreboard (no clan tag brackets or rank icons)
   - "kills": kill count (integer, 0..{_MAX_KDA})
   - "deaths": death count (integer, 0..{_MAX_KDA})
   - "assists": assist count (integer, 0..{_MAX_KDA})
   - "score": Combat Score (Valorant ACS), Score (CS2/CoD), or Net Worth/Gold (MLBB) — pick whichever stat the screenshot actually shows. Integer.

If a number is unreadable, return your best-effort integer (small ambiguities only — do NOT invent values).
If a player row is partially obscured, still include them with whatever you could read; set unknown numeric fields to 0.

Return ONLY a single JSON object with this EXACT shape — no prose, no markdown fences, no explanation:
{{"team_a": {{"team_name": "<string>", "score": <int>, "players": [{{"name": "<string>", "kills": <int>, "deaths": <int>, "assists": <int>, "score": <int>}}]}}, "team_b": {{"team_name": "<string>", "score": <int>, "players": [{{"name": "<string>", "kills": <int>, "deaths": <int>, "assists": <int>, "score": <int>}}]}}}}
"""


# ── Response validation ────────────────────────────────────────────────────

def _coerce_int(value: Any, *, low: int, high: int, allow_zero: bool = True) -> int:
    """Parse ``value`` into ``[low, high]``. Negatives clamped to 0."""
    try:
        n = int(value)
    except (TypeError, ValueError) as exc:
        raise Team5v5ScreenshotExtractionError(
            f"AI returned a non-integer value: {value!r}",
            code="bad_shape",
        ) from exc
    if n < 0:
        n = 0
    if not allow_zero and n == 0:
        return 0
    if n > high:
        raise Team5v5ScreenshotExtractionError(
            f"AI returned an implausibly high value ({n} > {high}).",
            code="bad_values",
            details={"value": n, "limit": high},
        )
    if n < low:
        n = low
    return n


def _validate_player(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        raise Team5v5ScreenshotExtractionError(
            "AI player row was not an object.",
            code="bad_shape",
        )
    name = (row.get("name") or "").strip()
    if not isinstance(name, str):
        name = str(name or "")
    return {
        "name":    name[:64],
        "kills":   _coerce_int(row.get("kills"),   low=0, high=_MAX_KDA),
        "deaths":  _coerce_int(row.get("deaths"),  low=0, high=_MAX_KDA),
        "assists": _coerce_int(row.get("assists"), low=0, high=_MAX_KDA),
        "score":   _coerce_int(row.get("score"),   low=0, high=_MAX_PLAYER_SCORE),
    }


def _validate_team_block(team: Any, side: str) -> Dict[str, Any]:
    if not isinstance(team, dict):
        raise Team5v5ScreenshotExtractionError(
            f"AI '{side}' was not an object.",
            code="bad_shape",
        )
    team_name = (team.get("team_name") or "").strip()
    if not isinstance(team_name, str):
        team_name = str(team_name or "")
    score = _coerce_int(team.get("score"), low=0, high=_MAX_TEAM_SCORE)

    raw_players = team.get("players")
    if not isinstance(raw_players, list) or not raw_players:
        raise Team5v5ScreenshotExtractionError(
            f"AI '{side}' has no player rows.",
            code="bad_shape",
        )
    # Take up to 5 — if fewer, that's fine (admin can edit). If more, prefer
    # the first 5 (the scoreboard order is the natural ranking).
    cleaned_players = [_validate_player(p) for p in raw_players[:_TEAM_SIZE]]

    return {
        "team_name": team_name[:80],
        "score":     score,
        "players":   cleaned_players,
    }


def _validate_response(raw: Any) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise Team5v5ScreenshotExtractionError(
            "AI response was not a JSON object.",
            code="bad_shape",
        )
    return {
        "team_a": _validate_team_block(raw.get("team_a"), "team_a"),
        "team_b": _validate_team_block(raw.get("team_b"), "team_b"),
    }


# ── Mapping: AI sides → participant1/participant2 ──────────────────────────

def _map_team_alignment(
    parsed: Dict[str, Any],
    p1_name: str,
    p2_name: str,
) -> Tuple[bool, str]:
    """
    Return ``(swap, confidence)``. ``swap=False`` means team_a→participant1,
    team_b→participant2; ``swap=True`` flips them.

    Confidence is graded the same way as the sports service: sum of
    name-similarity ratios across both team comparisons.
    """
    if not p1_name and not p2_name:
        return False, "none"

    a_to_p1 = name_similarity(parsed["team_a"]["team_name"], p1_name)
    a_to_p2 = name_similarity(parsed["team_a"]["team_name"], p2_name)
    b_to_p1 = name_similarity(parsed["team_b"]["team_name"], p1_name)
    b_to_p2 = name_similarity(parsed["team_b"]["team_name"], p2_name)

    align_no_swap = a_to_p1 + b_to_p2  # team_a → p1
    align_swap    = a_to_p2 + b_to_p1  # team_a → p2
    best = max(align_no_swap, align_swap)

    if best < 0.6:
        return False, "none"
    confidence = "high" if best >= 1.2 else "low"
    swap = align_swap > align_no_swap
    return swap, confidence


# ── Mapping: per-player → user_id ──────────────────────────────────────────

# Per-row similarity thresholds (single ratio, 0..1).
_PLAYER_HIGH = 0.7
_PLAYER_LOW  = 0.4


def _map_players_to_users(
    extracted_players: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Greedy best-first assignment of AI rows → candidate user_ids on this team.

    Algorithm:
      1. Compute the (row, candidate) similarity matrix.
      2. Pick the global max; assign that pair if its score >= _PLAYER_LOW.
      3. Remove both row and candidate from contention; repeat.
      4. Any unassigned row gets ``user_id=None`` and ``mapping_confidence='none'``.

    Greedy is fine here: 5×5 max, and ties rarely matter — the human reviews.
    """
    available = list(range(len(candidates)))
    pending = list(range(len(extracted_players)))
    assignments: Dict[int, Tuple[int, float]] = {}   # row_idx -> (cand_idx, ratio)

    # Pre-compute matrix so we don't recompute on each pop.
    matrix = [
        [name_similarity(p["name"], c["label"]) for c in candidates]
        for p in extracted_players
    ]

    while pending and available:
        best_row, best_cand, best_score = -1, -1, -1.0
        for r in pending:
            for c in available:
                s = matrix[r][c]
                if s > best_score:
                    best_row, best_cand, best_score = r, c, s
        if best_score < _PLAYER_LOW:
            break  # nothing else worth assigning
        assignments[best_row] = (best_cand, best_score)
        pending.remove(best_row)
        available.remove(best_cand)

    out: List[Dict[str, Any]] = []
    for idx, p in enumerate(extracted_players):
        if idx in assignments:
            cand_idx, score = assignments[idx]
            cand = candidates[cand_idx]
            confidence = "high" if score >= _PLAYER_HIGH else "low"
            out.append({
                "user_id":            cand["user_id"],
                "matched_label":      cand["label"],
                "ign":                p["name"],
                "kills":              p["kills"],
                "deaths":             p["deaths"],
                "assists":            p["assists"],
                "score":              p["score"],
                "mapping_confidence": confidence,
            })
        else:
            out.append({
                "user_id":            None,
                "matched_label":      None,
                "ign":                p["name"],
                "kills":              p["kills"],
                "deaths":             p["deaths"],
                "assists":            p["assists"],
                "score":              p["score"],
                "mapping_confidence": "none",
            })
    return out


# ── Public: low-level extraction (no storage round-trip) ───────────────────

def extract_team_5v5_via_gemini(
    image_bytes: bytes,
    content_type: str,
    *,
    team_a_name: str,
    team_a_candidates: List[Dict[str, Any]],
    team_b_name: str,
    team_b_candidates: List[Dict[str, Any]],
    game_name: str = "",
) -> Dict[str, Any]:
    """
    Send the image to Gemini Vision and validate the response. Returns the raw
    validated structure (NOT yet aligned to participant1/participant2 — that's
    done in the orchestrator):

        {"team_a": {team_name, score, players[5]},
         "team_b": {team_name, score, players[5]}}

    Useful for tests and unit work. Production should call
    ``process_team_5v5_screenshot``.
    """
    prompt = _build_prompt(
        team_a_name=team_a_name,
        team_a_candidates=team_a_candidates,
        team_b_name=team_b_name,
        team_b_candidates=team_b_candidates,
        game_name=game_name,
    )
    raw = call_gemini_vision_json(prompt, image_bytes, content_type)
    return _validate_response(raw)


# ── Public: top-level orchestrator (upload → extract → align → delete) ─────

def process_team_5v5_screenshot(
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
          "match_id": <int>,
          "team_a":   {raw AI block — team_name, score, players[5]},
          "team_b":   {raw AI block},
          "team_mapping_confidence": "high"|"low"|"none",
          "participant1_score":     <int|None>,
          "participant2_score":     <int|None>,
          "participant1_name":      "<str>",
          "participant2_name":      "<str>",
          "participant1_players":   [
            {
              "user_id":  <int|None>,
              "matched_label":      "<str|None>",
              "ign":                "<str>",
              "kills": <int>, "deaths": <int>, "assists": <int>, "score": <int>,
              "mapping_confidence": "high"|"low"|"none"
            }, ... up to 5
          ],
          "participant2_players":   [...],
          "audit": {
            "supabase_path": "<str>",
            "supabase_url":  "<str>",
            "team1_candidates_count": <int>,
            "team2_candidates_count": <int>
          }
        }

    Raises ``Team5v5ScreenshotError`` (or subclass) on pipeline failure. The
    Supabase object is deleted in ``finally`` so storage stays clean even when
    Gemini blows up.
    """
    if not image_bytes:
        raise Team5v5ScreenshotError("Empty image upload.", code="empty_upload")

    p1_name = (getattr(match, "participant1_name", "") or "").strip()
    p2_name = (getattr(match, "participant2_name", "") or "").strip()

    team1_candidates, team2_candidates = build_team_rosters(
        tournament=tournament,
        participant1_id=getattr(match, "participant1_id", None),
        participant2_id=getattr(match, "participant2_id", None),
    )

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
            "team_5v5",
            f"tournament_{tournament.id}",
            f"match_{match.id}",
            original_filename=original_filename,
        )
        public_url, storage_path = upload_screenshot(
            image_bytes=image_bytes,
            content_type=content_type,
            storage_path=path,
        )
        parsed = extract_team_5v5_via_gemini(
            image_bytes=image_bytes,
            content_type=content_type,
            team_a_name=p1_name,           # initial hint — may be swapped after alignment
            team_a_candidates=team1_candidates,
            team_b_name=p2_name,
            team_b_candidates=team2_candidates,
            game_name=game_name,
        )
    finally:
        if storage_path:
            delete_screenshot(storage_path)

    # Align AI sides to participant slots based on team-name fuzzy match.
    swap, team_conf = _map_team_alignment(parsed, p1_name, p2_name)
    a_block = parsed["team_b"] if swap else parsed["team_a"]
    b_block = parsed["team_a"] if swap else parsed["team_b"]

    p1_players = _map_players_to_users(a_block["players"], team1_candidates)
    p2_players = _map_players_to_users(b_block["players"], team2_candidates)

    return {
        "match_id":                match.id,
        "team_a":                  parsed["team_a"],
        "team_b":                  parsed["team_b"],
        "team_mapping_confidence": team_conf,
        "participant1_name":       p1_name,
        "participant2_name":       p2_name,
        "participant1_score":      a_block["score"] if team_conf != "none" else None,
        "participant2_score":      b_block["score"] if team_conf != "none" else None,
        "participant1_players":    p1_players,
        "participant2_players":    p2_players,
        # Surfaced so the frontend can populate its user-picker dropdowns for
        # unmatched rows without making a second roster fetch.
        "participant1_candidates": team1_candidates,
        "participant2_candidates": team2_candidates,
        "audit": {
            "supabase_path":          storage_path,
            "supabase_url":           public_url,
            "team1_candidates_count": len(team1_candidates),
            "team2_candidates_count": len(team2_candidates),
        },
    }
