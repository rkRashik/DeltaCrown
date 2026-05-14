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
       ``screenshot_utils.name_similarity`` (stdlib SequenceMatcher). Within
       each aligned team, STRICTLY match each AI player row to a roster
       candidate by exact normalised Game Passport IGN — no fuzzy fallback,
       no username matching. Unmatched rows return with ``user_id=None`` so
       the admin assigns them manually in the TOC grid.
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


def normalize_name(name):
    """Removes spaces and converts to lowercase for strict matching."""
    if not name:
        return ""
    return "".join(str(name).split()).lower()



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

# Same active-registration filter the Rosters TOC tab uses. Keeps the two
# sources in sync — what the rosters page shows is what the AI picker sees.
_ACTIVE_REGISTRATION_STATUSES = ("confirmed", "auto_approved")


def build_team_rosters(
    tournament,
    participant1_id: Optional[int],
    participant2_id: Optional[int],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Return ``(team1_candidates, team2_candidates)``. Each element is a candidate
    dict with the V2.3 shape:

        {
          "user_id":       <int>,
          "passport_ign":  "<str>" | None,   # AI MATCH KEY — Game Passport IGN
          "platform_name": "<str>",          # platform @-username (e.g. "rkrashik")
          "label":         "<str>"           # passport_ign if set, else username
        }

    **Source of truth — tournament-specific lineup_snapshot.** The Rosters TOC
    tab reads from ``Registration.lineup_snapshot`` for each team (a JSON list
    captured at registration time). We read from the SAME source so the AI
    picker sees the same 5 starters the rosters page does. We previously
    queried ``TeamMembership`` directly, which silently dropped any players
    whose general-team status was INVITED / SUBSTITUTE / NULL roster_slot —
    even though they were locked in for THIS tournament.

    Players whose ``passport_ign`` is None are kept in the candidate list (so
    the admin can still select them manually) but the AI mapping pass skips
    them — V2 matches strictly against Game Passport IGN, never username.
    """
    from apps.tournaments.models.registration import Registration

    # Bulk-load Game Passport IGNs for this game's roster. Match the
    # rosters_service approach: filter GameProfile by game_display_name
    # (which is the field the roster page successfully uses).
    user_ign_map: Dict[int, str] = {}
    game_dn = ""
    try:
        game_dn = (tournament.game.display_name if tournament.game_id else "") or ""
    except Exception:
        game_dn = ""
    if game_dn:
        try:
            from apps.user_profile.models import GameProfile  # type: ignore
            qs = (
                GameProfile.objects
                .filter(game_display_name__iexact=game_dn)
                .exclude(ign="")
                .values("user_id", "ign")
            )
            user_ign_map = {int(row["user_id"]): (row["ign"] or "").strip() for row in qs}
        except Exception as exc:
            logger.warning("team_5v5: GameProfile bulk fetch failed game=%s err=%s", game_dn, exc)

    def _roster(team_id: Optional[int]) -> List[Dict[str, Any]]:
        if not team_id:
            return []
        try:
            reg = (
                Registration.objects
                .filter(
                    tournament=tournament,
                    team_id=team_id,
                    status__in=_ACTIVE_REGISTRATION_STATUSES,
                )
                .order_by("-registered_at")
                .first()
            )
        except Exception as exc:
            logger.warning("team_5v5: registration fetch failed team_id=%s err=%s", team_id, exc)
            return []

        if not reg or not reg.lineup_snapshot:
            return []

        out: List[Dict[str, Any]] = []
        seen_user_ids: set = set()
        for entry in reg.lineup_snapshot:
            if not isinstance(entry, dict):
                continue
            uid = entry.get("user_id")
            if not uid:
                continue
            try:
                uid = int(uid)
            except (TypeError, ValueError):
                continue
            if uid in seen_user_ids:
                continue
            # Default to STARTER when the field is missing (matches the
            # rosters tab's lenient interpretation of legacy entries).
            slot = entry.get("roster_slot", "STARTER") or "STARTER"
            if slot != "STARTER":
                continue
            seen_user_ids.add(uid)

            passport_ign = (user_ign_map.get(uid) or "").strip()
            # platform_name = the platform @-username (e.g. "rkrashik"), NOT
            # the team display_name. The admin wants their account handle in
            # the dropdown's parenthetical for unambiguous identification.
            username = (entry.get("username") or "").strip()
            platform_name = username or f"User #{uid}"

            out.append({
                "user_id":       uid,
                "passport_ign":  passport_ign or None,
                "platform_name": platform_name,
                "label":         passport_ign or platform_name,
            })
        return out

    return _roster(participant1_id), _roster(participant2_id)


# ── Prompt builder ─────────────────────────────────────────────────────────

def _format_candidate_block(name: str, candidates: List[Dict[str, Any]]) -> str:
    """
    Emit the prompt's roster-hint block for ONE team. Only candidates with a
    Game Passport IGN are listed — V2 matches strictly against passport IGN,
    so feeding Gemini platform names would only invite false positives. The
    platform name is shown as a parenthetical so the model can still recognise
    a player by their roster handle if needed.
    """
    if not candidates:
        return f"  {name or '(unknown)'}: (no roster on file — extract IGNs as best you can)"
    matchable = [c for c in candidates if c.get("passport_ign")]
    if not matchable:
        return f"  {name or '(unknown)'}: (roster has no Game Passport IGNs — extract IGNs as best you can)"
    lines = [f"  {name or '(unknown)'}:"]
    for c in matchable:
        platform = (c.get("platform_name") or "").strip()
        if platform and platform.lower() != c["passport_ign"].lower():
            lines.append(f"    - {c['passport_ign']}  (platform: {platform})")
        else:
            lines.append(f"    - {c['passport_ign']}")
    return "\n".join(lines)


def _build_prompt(
    team_a_name: str,
    team_a_candidates: List[Dict[str, Any]],
    team_b_name: str,
    team_b_candidates: List[Dict[str, Any]],
    game_name: str,
) -> str:
    game_line = game_name.strip() if game_name else "Valorant / CS2 / MLBB / Call of Duty"
    a_block = _format_candidate_block(team_a_name, team_a_candidates)
    b_block = _format_candidate_block(team_b_name, team_b_candidates)
    return f"""You are reading a 5v5 competitive match end-of-game scoreboard. Optimise for VALORANT screens
(the schema below is Valorant-led); also works for CS2 / MLBB / Call of Duty — fill 0 / empty string
for fields that don't apply.

Game: {game_line}

The two teams in this fixture, with their Game Passport IGNs as hints. Each player row's displayed
IGN should match one of these where possible.

team_a — roster of "{team_a_name}":
{a_block}

team_b — roster of "{team_b_name}":
{b_block}

============================================================================
CRITICAL — Valorant scoreboard layout (READ CAREFULLY before extracting)
============================================================================
The Valorant end-of-game scoreboard (heading "INDIVIDUALLY SORTED") shows ALL 10 players
in a SINGLE list ordered by AVG COMBAT SCORE descending. Players from the two teams
are INTERLEAVED — the top 5 rows are NOT one team and the bottom 5 rows are NOT one
team. You MUST use ROW BACKGROUND COLOUR to determine each player's team:

  • GREEN rows  (and at most ONE GOLD/yellow row — that is the recording player,
                 still on the GREEN team) ──► call this the "Green Team"
  • RED rows                                  ──► call this the "Red Team"

The banner at the top reads "<X> VICTORY <Y>" or "<X> DEFEAT <Y>":
  • LEFT number (X)  = the GREEN team's final score (ALWAYS — ignore the VICTORY/DEFEAT word).
  • RIGHT number (Y) = the RED team's final score.
  (VICTORY/DEFEAT only describes the recording player's POV; do NOT use it to assign scores.)

Mapping the coloured teams to team_a / team_b:
  • Count how many player IGNs in the GREEN team match the team_a roster hints above.
    If the Green team has more team_a matches → Green Team is team_a, Red Team is team_b.
    Otherwise → Green Team is team_b, Red Team is team_a.
  • Set "team_a_score" and "team_b_score" accordingly.
  • Each player goes into team_a or team_b based on the COLOUR of their row + the colour↔team
    mapping you just computed. Do NOT put players in team_a just because their row was near the
    top of the scoreboard.

COMMON FAILURE TO AVOID:
Do NOT chunk the scoreboard as "rows 1–5 = team_a, rows 6–10 = team_b". The Valorant scoreboard
is ACS-sorted across BOTH teams. Always split by COLOUR, never by row position.

============================================================================
Extract from the screenshot:
============================================================================

1. team_a / team_b: each has a "team_name", a "score", and exactly 5 "players" (grouped by COLOUR,
   not by row position).

2. Top-level "team_a_score" and "team_b_score" — mirroring the per-team "score" values.

3. For EACH player (5 per team, 10 total):
   - "agent":   agent / hero / operator played (e.g. "Jett", "Killjoy", "Layla"). Empty string if not applicable.
   - "ign":     the in-game name EXACTLY as displayed on the scoreboard (no clan-tag brackets, no
                rank icons, preserve original capitalisation and spacing).
   - "kills":   integer, 0..{_MAX_KDA}
   - "deaths":  integer, 0..{_MAX_KDA}
   - "assists": integer, 0..{_MAX_KDA}
   - "acs":     Average Combat Score (Valorant), Score (CS2/CoD), Net Worth/Gold (MLBB). Integer, 0..{_MAX_PLAYER_SCORE}.
   - "econ":    Economy rating (Valorant ECON column). Integer, 0..{_MAX_KDA}. 0 if not visible.
   - "fb":      First Bloods. Integer, 0..{_MAX_KDA}. 0 if not visible.
   - "plants":  Spike plants (Valorant) or bomb plants (CS2). Integer, 0..{_MAX_KDA}. 0 if not applicable.
   - "defuses": Spike defuses (Valorant) or bomb defuses (CS2). Integer, 0..{_MAX_KDA}. 0 if not applicable.

If a number is unreadable, return your best-effort integer (small ambiguities only — do NOT invent
values). If a player row is partially obscured, still include them with whatever you could read; set
unknown numeric fields to 0 and unknown text fields to "".

Return ONLY a single JSON object with this EXACT shape — no prose, no markdown fences, no explanation:
{{"team_a_score": <int>, "team_b_score": <int>, "team_a": {{"team_name": "<str>", "score": <int>, "players": [{{"agent": "<str>", "ign": "<str>", "kills": <int>, "deaths": <int>, "assists": <int>, "acs": <int>, "econ": <int>, "fb": <int>, "plants": <int>, "defuses": <int>}}]}}, "team_b": {{"team_name": "<str>", "score": <int>, "players": [{{"agent": "<str>", "ign": "<str>", "kills": <int>, "deaths": <int>, "assists": <int>, "acs": <int>, "econ": <int>, "fb": <int>, "plants": <int>, "defuses": <int>}}]}}}}
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


def _safe_str(value: Any, *, limit: int) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()[:limit]


def _validate_player(row: Any) -> Dict[str, Any]:
    """V2 player row — Valorant-led schema with full KDA + agent + econ stats."""
    if not isinstance(row, dict):
        raise Team5v5ScreenshotExtractionError(
            "AI player row was not an object.",
            code="bad_shape",
        )
    # V2 schema renames: name → ign, score → acs.
    # Tolerate v1-shaped responses defensively (older Gemini cache, etc.) so a
    # transient prompt-version mismatch doesn't 422 the whole request.
    ign_raw = row.get("ign")
    if not ign_raw:
        ign_raw = row.get("name")
    acs_raw = row.get("acs")
    if acs_raw is None:
        acs_raw = row.get("score")

    return {
        "agent":   _safe_str(row.get("agent"), limit=32),
        "ign":     _safe_str(ign_raw, limit=64),
        "kills":   _coerce_int(row.get("kills"),   low=0, high=_MAX_KDA),
        "deaths":  _coerce_int(row.get("deaths"),  low=0, high=_MAX_KDA),
        "assists": _coerce_int(row.get("assists"), low=0, high=_MAX_KDA),
        "acs":     _coerce_int(acs_raw,            low=0, high=_MAX_PLAYER_SCORE),
        "econ":    _coerce_int(row.get("econ"),    low=0, high=_MAX_KDA),
        "fb":      _coerce_int(row.get("fb"),      low=0, high=_MAX_KDA),
        "plants":  _coerce_int(row.get("plants"),  low=0, high=_MAX_KDA),
        "defuses": _coerce_int(row.get("defuses"), low=0, high=_MAX_KDA),
    }


def _validate_team_block(team: Any, side: str) -> Dict[str, Any]:
    if not isinstance(team, dict):
        raise Team5v5ScreenshotExtractionError(
            f"AI '{side}' was not an object.",
            code="bad_shape",
        )
    team_name = _safe_str(team.get("team_name"), limit=80)
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
        "team_name": team_name,
        "score":     score,
        "players":   cleaned_players,
    }


def _validate_response(raw: Any) -> Dict[str, Any]:
    """
    V2 envelope. Adds top-level ``team_a_score`` / ``team_b_score`` read off
    the "13 VICTORY 3" banner. The per-team block ``score`` field is preserved
    too (Gemini is asked to mirror them) — when banner and per-team scores
    disagree the banner wins, since it's the clearer source.
    """
    if not isinstance(raw, dict):
        raise Team5v5ScreenshotExtractionError(
            "AI response was not a JSON object.",
            code="bad_shape",
        )
    team_a = _validate_team_block(raw.get("team_a"), "team_a")
    team_b = _validate_team_block(raw.get("team_b"), "team_b")

    # Banner scores. Fall back to the per-team values if the banner field is
    # missing entirely — and if the banner *is* present, prefer it over the
    # per-team mirror.
    try:
        a_banner = _coerce_int(raw.get("team_a_score"), low=0, high=_MAX_TEAM_SCORE)
    except Team5v5ScreenshotExtractionError:
        a_banner = None
    try:
        b_banner = _coerce_int(raw.get("team_b_score"), low=0, high=_MAX_TEAM_SCORE)
    except Team5v5ScreenshotExtractionError:
        b_banner = None

    team_a_score = a_banner if a_banner is not None else team_a["score"]
    team_b_score = b_banner if b_banner is not None else team_b["score"]
    # Mirror back onto the team blocks so callers reading either path get a
    # consistent picture.
    team_a["score"] = team_a_score
    team_b["score"] = team_b_score

    return {
        "team_a_score": team_a_score,
        "team_b_score": team_b_score,
        "team_a":       team_a,
        "team_b":       team_b,
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

def _build_player_payload(
    extracted: Dict[str, Any],
    cand: Optional[Dict[str, Any]],
    confidence: str,
) -> Dict[str, Any]:
    """Shared row builder. ``cand=None`` → unassigned row, admin picks manually."""
    return {
        "user_id":               cand["user_id"]       if cand else None,
        "matched_label":         cand["passport_ign"]  if cand else None,
        "matched_platform_name": cand["platform_name"] if cand else None,
        "agent":                 extracted["agent"],
        "ign":                   extracted["ign"],
        "kills":                 extracted["kills"],
        "deaths":                extracted["deaths"],
        "assists":               extracted["assists"],
        "acs":                   extracted["acs"],
        "econ":                  extracted["econ"],
        "fb":                    extracted["fb"],
        "plants":                extracted["plants"],
        "defuses":               extracted["defuses"],
        "mapping_confidence":    confidence,
    }


def _map_players_to_users(
    extracted_players: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Strict-binary passport mapping (V2.1). The only valid match is a
    normalised, case-insensitive equality between the AI's extracted ``ign``
    and a candidate's Game Passport ``ign``:

        normalize_name(extracted_ign) == normalize_name(candidate.passport_ign)

    If that exact match is found, the row locks at ``"high"`` confidence with
    the candidate's ``user_id``. If not, the row stays unassigned
    (``user_id=None``, ``mapping_confidence="none"``) and the TOC renders an
    empty dropdown with an amber "AI saw: <ign>" hint so the admin assigns it
    manually. No fuzzy guessing — guesses produce noise like "1W Pandaaa" →
    "1W ProfXoR" which costs more to clean up than to fill from scratch.

    Candidates without a Game Passport never match (V2 never falls back to
    platform names / usernames); they still appear in the dropdown for manual
    pickup. Each candidate is consumed at most once — duplicate IGNs on the
    AI side won't both claim the same roster slot.
    """
    used_candidates: set = set()
    out: List[Dict[str, Any]] = []

    for p in extracted_players:
        key = normalize_name(p["ign"])
        match: Optional[Dict[str, Any]] = None
        if key:
            for idx, c in enumerate(candidates):
                if idx in used_candidates:
                    continue
                cand_key = normalize_name(c.get("passport_ign") or "")
                if cand_key and cand_key == key:
                    match = c
                    used_candidates.add(idx)
                    break
        out.append(_build_player_payload(
            p, match, "high" if match else "none",
        ))
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
    End-to-end pipeline. V2 returns the Valorant-led envelope:

        {
          "match_id": <int>,
          "team_a_score": <int>,             # banner score, AI-side
          "team_b_score": <int>,             # banner score, AI-side
          "team_a":   {team_name, score, players[5]},
          "team_b":   {team_name, score, players[5]},
          "team_mapping_confidence": "high"|"low"|"none",
          "participant1_score":     <int>,   # post-alignment, always populated
          "participant2_score":     <int>,
          "participant1_name":      "<str>",
          "participant2_name":      "<str>",
          "participant1_players":   [
            {
              "user_id":               <int|None>,
              "matched_label":         "<passport_ign|None>",
              "matched_platform_name": "<str|None>",
              "agent": "<str>", "ign": "<str>",
              "kills": <int>, "deaths": <int>, "assists": <int>,
              "acs": <int>, "econ": <int>, "fb": <int>,
              "plants": <int>, "defuses": <int>,
              "mapping_confidence": "high"|"low"|"none"
            }, ... up to 5
          ],
          "participant2_players":    [...],
          "participant1_candidates": [{user_id, passport_ign, platform_name, label}, ...],
          "participant2_candidates": [...],
          "audit": {
            "supabase_path": "<str>",
            "supabase_url":  "<str>",
            "team1_candidates_count": <int>,
            "team2_candidates_count": <int>
          }
        }

    Note on alignment: team-level scores are ALWAYS populated regardless of
    ``team_mapping_confidence`` (the AI reads the numbers reliably even when
    slot mapping is uncertain). The frontend uses ``team_mapping_confidence``
    only to gate a "verify slot order" warning toast.

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
        # V2: top-level banner scores. Mirror the per-team-block scores when
        # the banner field is unavailable; ``_validate_response`` keeps these
        # in sync with team_a["score"] / team_b["score"].
        "team_a_score":            parsed["team_a_score"],
        "team_b_score":            parsed["team_b_score"],
        "team_a":                  parsed["team_a"],
        "team_b":                  parsed["team_b"],
        "team_mapping_confidence": team_conf,
        "participant1_name":       p1_name,
        "participant2_name":       p2_name,
        # V2: always populate slot-aligned scores (admin still gets a warning
        # toast on the frontend when team_mapping_confidence is low/none, but
        # the numbers themselves are reliable even when the slot order isn't).
        "participant1_score":      a_block["score"],
        "participant2_score":      b_block["score"],
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
