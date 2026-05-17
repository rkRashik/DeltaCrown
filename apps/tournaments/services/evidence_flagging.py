"""
P3.2/P3.3 — OCR evidence comparison and review-flagging service.

This is the authoritative backend source for evidence verification state.
The frontend reads from ``evidence_comparison`` returned by
``get_match_detail`` — never re-computes comparison logic itself.

Comparison checks
-----------------
Each check has: id, label, status ("pass"|"fail"|"warning"|"pending"|"unknown"), detail.

  submitted_consistency   — do both participants' submitted scores mirror?
  ocr_consistency         — do both OCR extractions agree on the same scores?
  s1_sub_vs_ocr           — does side 1's submitted score match their OCR?
  s2_sub_vs_ocr           — does side 2's submitted score match their OCR?
  confidence              — are both OCR confidence scores acceptable?
  screenshots             — do both sides have screenshots?

Severity levels
---------------
  ok      — all checks pass, safe_to_verify = True
  low     — minor issues (e.g. low confidence on one side)
  medium  — awaiting scan or incomplete data
  high    — score disagreement or OCR failure, requires_review = True

Design constraints
------------------
* Never auto-finalises the match — only updates review status + audit.
* Idempotent — safe to call multiple times; last write wins.
* Respects evidence retention policy.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from django.utils import timezone

from apps.tournaments.models.result_submission import MatchResultSubmission

logger = logging.getLogger("tournaments.evidence_flagging")

# Minimum acceptable OCR confidence (0–1). Below this, confidence check is "warning".
_MIN_CONFIDENCE = 0.65

# Statuses that mean a submitted score or OCR run is in the "done" bucket.
_OCR_COMPLETE_STATUSES = {"completed"}
_OCR_ACTIVE_STATUSES   = {"pending", "running"}
_OCR_FAIL_STATUSES     = {"failed", "skipped"}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _extracted_p1_p2(extracted: dict) -> Tuple[Optional[int], Optional[int]]:
    """Return (participant1_score, participant2_score) from an OCR result dict."""
    if not isinstance(extracted, dict):
        return None, None
    def _i(v: Any) -> Optional[int]:
        try:
            n = int(v)
            return n if n >= 0 else None
        except (TypeError, ValueError):
            return None
    a = _i(extracted.get("participant1_score")) or _i(extracted.get("home_score"))
    b = _i(extracted.get("participant2_score")) or _i(extracted.get("away_score"))
    return a, b


def _sub_summary(sub: Optional[MatchResultSubmission]) -> dict:
    if sub is None:
        return {
            "submission_id": None, "submitted_for": None, "submitted_against": None,
            "ocr_p1": None, "ocr_p2": None, "ocr_status": "",
            "ocr_confidence": None, "has_screenshot": False,
        }
    def _i(v):
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None
    ep1, ep2 = _extracted_p1_p2(sub.ocr_extracted or {})
    has_shot = bool(
        (getattr(sub, "proof_screenshot", None) and sub.proof_screenshot.name)
        or (sub.proof_screenshot_url or "").strip()
    )
    # Scores are stored in raw_result_payload (canonical) but fall back to
    # any direct attribute for test mocks and legacy paths.
    payload = sub.raw_result_payload if isinstance(sub.raw_result_payload, dict) else {}
    score_for     = _i(payload.get("score_for")) if payload else None
    score_against = _i(payload.get("score_against")) if payload else None
    if score_for is None:
        try:
            score_for = _i(getattr(sub, "score_for", None))
        except Exception:
            pass
    if score_against is None:
        try:
            score_against = _i(getattr(sub, "score_against", None))
        except Exception:
            pass
    return {
        "submission_id": sub.id,
        "submitted_for":     score_for,
        "submitted_against": score_against,
        "ocr_p1": ep1, "ocr_p2": ep2,
        "ocr_status": str(sub.ocr_status or ""),
        "ocr_confidence": sub.ocr_confidence,
        "has_screenshot": has_shot,
    }


def _check(check_id: str, label: str, status: str, detail: str) -> dict:
    """Build a single check entry. status in {pass, fail, warning, pending, unknown}."""
    return {"id": check_id, "label": label, "status": status, "detail": detail}


# ── Core comparison engine ───────────────────────────────────────────────────

def compute_evidence_comparison(
    side1_sub: Optional[MatchResultSubmission],
    side2_sub: Optional[MatchResultSubmission],
    *,
    match=None,
) -> Dict[str, Any]:
    """Return the canonical evidence comparison payload.

    Shape::

        {
          "state":          str,          # machine-readable state key
          "severity":       "ok"|"low"|"medium"|"high",
          "recommendation": str,          # "safe_to_verify"|"needs_staff_review"|
                                          # "rescan_needed"|"pending"
          "safe_to_verify": bool,
          "requires_review": bool,
          "reason":         str,          # one-liner for banners
          "staff_message":  str,          # detailed staff-facing explanation
          "checks":         List[dict],   # per-check results (id, label, status, detail)
          "submitted_consistent":    bool|None,
          "ocr_cross_consistent":    bool|None,
          "side1_sub_matches_ocr":   bool|None,
          "side2_sub_matches_ocr":   bool|None,
          "side1":          dict,         # summary for Side 1
          "side2":          dict,         # summary for Side 2
        }
    """
    s1 = _sub_summary(side1_sub)
    s2 = _sub_summary(side2_sub)
    checks: List[dict] = []

    # ── Screenshot check ─────────────────────────────────────────────────
    if not s1["has_screenshot"] or not s2["has_screenshot"]:
        who = ("both sides" if (not s1["has_screenshot"] and not s2["has_screenshot"])
               else ("Side 1" if not s1["has_screenshot"] else "Side 2"))
        checks.append(_check(
            "screenshots", "Screenshots",
            "fail" if (not s1["has_screenshot"] and not s2["has_screenshot"]) else "warning",
            f"{who} submitted without a screenshot.",
        ))
    else:
        checks.append(_check("screenshots", "Screenshots", "pass",
                             "Both sides uploaded screenshots."))

    # ── Submission state ──────────────────────────────────────────────────
    if side1_sub is None or side2_sub is None:
        who = "Side 1" if side1_sub is None else "Side 2"
        checks.append(_check("submissions", "Both submitted", "pending",
                             f"{who} has not submitted yet."))
        return _build(
            "waiting_one" if (side1_sub is not None or side2_sub is not None) else "waiting_both",
            "medium", "pending", False, False,
            "Waiting for submissions.",
            "One or both sides have not submitted a result yet.",
            checks, None, None, None, None, s1, s2,
        )

    # ── OCR status ────────────────────────────────────────────────────────
    s1_ocr = s1["ocr_status"]
    s2_ocr = s2["ocr_status"]
    any_failed  = s1_ocr in _OCR_FAIL_STATUSES or s2_ocr in _OCR_FAIL_STATUSES
    any_active  = s1_ocr in _OCR_ACTIVE_STATUSES or s2_ocr in _OCR_ACTIVE_STATUSES
    both_done   = (s1_ocr in _OCR_COMPLETE_STATUSES and s2_ocr in _OCR_COMPLETE_STATUSES)

    if any_failed:
        fail_side = "Side 1" if s1_ocr in _OCR_FAIL_STATUSES else "Side 2"
        checks.append(_check("ocr_scan", "OCR Scan", "fail",
                             f"{fail_side} scan failed. Use Retry Scan."))
        return _build(
            "ocr_failed", "high", "rescan_needed", False, True,
            "OCR scan failed on one or more sides.",
            "A scan failed. Retry the scan or review manually.",
            checks, None, None, None, None, s1, s2,
        )
    if any_active:
        checks.append(_check("ocr_scan", "OCR Scan", "pending",
                             "Scan in progress — results will appear automatically."))
        return _build(
            "waiting_scan", "medium", "pending", False, False,
            "OCR scan in progress.",
            "Scans are running. Evidence tab will refresh automatically.",
            checks, None, None, None, None, s1, s2,
        )
    if not both_done:
        checks.append(_check("ocr_scan", "OCR Scan", "pending",
                             "One or both sides have not been scanned yet."))
        return _build(
            "waiting_scan", "medium", "pending", False, False,
            "Scan both screenshots to compare.",
            "Scan both sides to enable cross-check.",
            checks, None, None, None, None, s1, s2,
        )
    checks.append(_check("ocr_scan", "OCR Scan", "pass",
                         "Both sides scanned successfully."))

    # ── Confidence check ──────────────────────────────────────────────────
    c1 = s1["ocr_confidence"]
    c2 = s2["ocr_confidence"]
    if c1 is not None and c2 is not None:
        c_min = min(float(c1), float(c2))
        if c_min < _MIN_CONFIDENCE:
            low_side = ("Side 1" if float(c1) < float(c2) else "Side 2")
            checks.append(_check("confidence", "OCR Confidence", "warning",
                                 f"{low_side} extraction confidence is low "
                                 f"({int(c_min*100)}%). Review screenshot quality."))
        else:
            checks.append(_check("confidence", "OCR Confidence", "pass",
                                 f"Confidence acceptable "
                                 f"({int(min(float(c1), float(c2))*100)}%+)."))
    else:
        checks.append(_check("confidence", "OCR Confidence", "unknown",
                             "Confidence not available for all sides."))

    # ── Score comparisons ─────────────────────────────────────────────────
    def _both(*vals):
        return all(v is not None for v in vals)

    sf1, sa1 = s1["submitted_for"], s1["submitted_against"]
    sf2, sa2 = s2["submitted_for"], s2["submitted_against"]
    ep1_1, ep2_1 = s1["ocr_p1"], s1["ocr_p2"]
    ep1_2, ep2_2 = s2["ocr_p1"], s2["ocr_p2"]

    # 1. Submitted consistency.
    sub_cons: Optional[bool] = None
    if _both(sf1, sa1, sf2, sa2):
        sub_cons = (sf1 == sa2 and sa1 == sf2)
    if sub_cons is True:
        checks.append(_check("submitted_consistency", "Submitted Scores", "pass",
                             f"Side 1 ({sf1}–{sa1}) and Side 2 ({sf2}–{sa2}) agree."))
    elif sub_cons is False:
        checks.append(_check("submitted_consistency", "Submitted Scores", "fail",
                             f"Side 1 reported {sf1}–{sa1} but Side 2 reported {sf2}–{sa2}."))
    else:
        checks.append(_check("submitted_consistency", "Submitted Scores", "unknown",
                             "Cannot compare — some scores missing."))

    # 2. OCR cross-consistency.
    ocr_cons: Optional[bool] = None
    if _both(ep1_1, ep2_1, ep1_2, ep2_2):
        ocr_cons = (ep1_1 == ep1_2 and ep2_1 == ep2_2)
    if ocr_cons is True:
        checks.append(_check("ocr_consistency", "OCR Cross-Check", "pass",
                             f"Both screenshots extract the same score ({ep1_1}–{ep2_1})."))
    elif ocr_cons is False:
        checks.append(_check("ocr_consistency", "OCR Cross-Check", "fail",
                             f"Side 1 screenshot: {ep1_1}–{ep2_1}. "
                             f"Side 2 screenshot: {ep1_2}–{ep2_2}."))
    else:
        checks.append(_check("ocr_consistency", "OCR Cross-Check", "unknown",
                             "Cannot compare — some OCR scores missing."))

    # 3. Side 1 submitted vs OCR.
    s1_vs_ocr: Optional[bool] = None
    if _both(sf1, sa1, ep1_1, ep2_1):
        s1_vs_ocr = (sf1 == ep1_1 and sa1 == ep2_1)
    if s1_vs_ocr is True:
        checks.append(_check("s1_sub_vs_ocr", "Side 1 Sub vs OCR", "pass",
                             f"Side 1 submitted {sf1}–{sa1}, OCR shows {ep1_1}–{ep2_1}."))
    elif s1_vs_ocr is False:
        checks.append(_check("s1_sub_vs_ocr", "Side 1 Sub vs OCR", "fail",
                             f"Side 1 submitted {sf1}–{sa1} but OCR shows {ep1_1}–{ep2_1}."))
    else:
        checks.append(_check("s1_sub_vs_ocr", "Side 1 Sub vs OCR", "unknown",
                             "Cannot compare."))

    # 4. Side 2 submitted vs OCR (their perspective: for=p2, against=p1).
    s2_vs_ocr: Optional[bool] = None
    if _both(sf2, sa2, ep1_2, ep2_2):
        s2_vs_ocr = (sf2 == ep2_2 and sa2 == ep1_2)
    if s2_vs_ocr is True:
        checks.append(_check("s2_sub_vs_ocr", "Side 2 Sub vs OCR", "pass",
                             f"Side 2 submitted {sf2}–{sa2}, OCR shows {ep2_2}–{ep1_2} (their POV)."))
    elif s2_vs_ocr is False:
        checks.append(_check("s2_sub_vs_ocr", "Side 2 Sub vs OCR", "fail",
                             f"Side 2 submitted {sf2}–{sa2} but OCR shows {ep2_2}–{ep1_2} (their POV)."))
    else:
        checks.append(_check("s2_sub_vs_ocr", "Side 2 Sub vs OCR", "unknown",
                             "Cannot compare."))

    # ── Determine overall verdict ─────────────────────────────────────────
    fail_ids = {c["id"] for c in checks if c["status"] == "fail"}
    warn_ids = {c["id"] for c in checks if c["status"] == "warning"}

    if sub_cons is False:
        return _build(
            "mismatch_submitted", "high", "needs_staff_review", False, True,
            "Submitted scores disagree.",
            (f"Side 1 reported {sf1}–{sa1} but Side 2 reported {sf2}–{sa2}. "
             "Staff review required before verifying the result."),
            checks, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr, s1, s2,
        )
    if ocr_cons is False:
        return _build(
            "mismatch_ocr", "high", "needs_staff_review", False, True,
            "Screenshots disagree.",
            (f"Side 1 screenshot: {ep1_1}–{ep2_1}. Side 2 screenshot: {ep1_2}–{ep2_2}. "
             "The two screenshots extract different scores. Manual review needed."),
            checks, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr, s1, s2,
        )
    if s1_vs_ocr is False or s2_vs_ocr is False:
        return _build(
            "mismatch_submitted_vs_ocr", "high", "needs_staff_review", False, True,
            "Submitted score differs from screenshot extraction.",
            ("At least one side's reported score does not match their screenshot. "
             "Verify which is correct before confirming."),
            checks, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr, s1, s2,
        )
    if warn_ids == {"confidence"}:
        # Low confidence but scores agree.
        return _build(
            "consistent_low_confidence", "low", "needs_staff_review", False, True,
            "Scores agree but OCR confidence is low.",
            ("All scores are consistent but extraction confidence is below the safe "
             "threshold. Review the screenshot quality before verifying."),
            checks, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr, s1, s2,
        )
    if (sub_cons is True and ocr_cons is True
            and s1_vs_ocr is True and s2_vs_ocr is True):
        return _build(
            "consistent", "ok", "safe_to_verify", True, False,
            "Evidence is consistent — safe to verify.",
            ("All checks pass. Submitted scores, OCR extractions, and cross-checks agree. "
             "Use 'Verify Result' to confirm the match."),
            checks, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr, s1, s2,
        )
    # Partial pass — some checks unknown/skipped.
    return _build(
        "inconclusive", "medium", "pending", False, False,
        "Comparison inconclusive — some checks could not run.",
        "Manual review recommended before verifying.",
        checks, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr, s1, s2,
    )


def _build(
    state, severity, recommendation, safe_to_verify, requires_review,
    reason, staff_message, checks, sub_cons, ocr_cons, s1_ocr, s2_ocr, s1, s2,
) -> dict:
    return {
        "state": state,
        "severity": severity,
        "recommendation": recommendation,
        "safe_to_verify": safe_to_verify,
        "requires_review": requires_review,
        "reason": reason,
        "staff_message": staff_message,
        "checks": checks,
        "submitted_consistent": sub_cons,
        "ocr_cross_consistent": ocr_cons,
        "side1_sub_matches_ocr": s1_ocr,
        "side2_sub_matches_ocr": s2_ocr,
        "side1": s1,
        "side2": s2,
    }


# ── Per-game comparison (BO3/BO5) ────────────────────────────────────────────

def compute_per_game_comparison(
    all_submissions: list,
    participant1_team_id,
    participant2_team_id,
) -> list:
    """Group submissions by game_number and compute a mini-comparison per game.

    Returns a list of dicts, one per distinct game_number (sorted ascending),
    with null game_number submissions collected under game_number=0 ("Legacy").

    Each dict::

        {
          "game_number":          int,          # 0 = ungrouped/legacy
          "map":                  str,
          "side1":                dict,         # _sub_summary
          "side2":                dict,
          "state":                str,
          "severity":             str,
          "submitted_consistent": bool|None,
          "ocr_cross_consistent": bool|None,
          "side1_sub_matches_ocr": bool|None,
          "side2_sub_matches_ocr": bool|None,
          "recommendation":       str,
        }
    """
    # Build per-game bucket: game_number → {team_id: latest_submission}
    buckets: dict[int, dict] = {}
    for sub in all_submissions:
        gn = sub.game_number if sub.game_number is not None else 0
        if gn not in buckets:
            buckets[gn] = {}
        tid = sub.submitted_by_team_id
        if tid not in buckets[gn] or (
            sub.submitted_at and buckets[gn][tid].submitted_at
            and sub.submitted_at >= buckets[gn][tid].submitted_at
        ):
            buckets[gn][tid] = sub

    result = []
    for gn in sorted(buckets.keys()):
        game_subs = buckets[gn]
        sub1 = game_subs.get(participant1_team_id)
        sub2 = game_subs.get(participant2_team_id)
        s1 = _sub_summary(sub1)
        s2 = _sub_summary(sub2)

        # Map name from payload.
        map_name = ""
        for sub in (sub1, sub2):
            if sub and isinstance(sub.raw_result_payload, dict):
                map_name = str(sub.raw_result_payload.get("map") or "")
                if map_name:
                    break

        # Mini-comparison (fewer checks than full compare).
        sf1, sa1 = s1["submitted_for"], s1["submitted_against"]
        sf2, sa2 = s2["submitted_for"], s2["submitted_against"]
        ep1_1, ep2_1 = s1["ocr_p1"], s1["ocr_p2"]
        ep1_2, ep2_2 = s2["ocr_p1"], s2["ocr_p2"]

        s1_ocr_ok = s1["ocr_status"] in _OCR_COMPLETE_STATUSES
        s2_ocr_ok = s2["ocr_status"] in _OCR_COMPLETE_STATUSES
        s1_ocr_fail = s1["ocr_status"] in _OCR_FAIL_STATUSES
        s2_ocr_fail = s2["ocr_status"] in _OCR_FAIL_STATUSES

        def _b(*vals):
            return all(v is not None for v in vals)

        sub_cons: Optional[bool] = None
        if _b(sf1, sa1, sf2, sa2):
            sub_cons = (sf1 == sa2 and sa1 == sf2)

        ocr_cons: Optional[bool] = None
        if s1_ocr_ok and s2_ocr_ok and _b(ep1_1, ep2_1, ep1_2, ep2_2):
            ocr_cons = (ep1_1 == ep1_2 and ep2_1 == ep2_2)

        s1_v_ocr: Optional[bool] = None
        if s1_ocr_ok and _b(sf1, sa1, ep1_1, ep2_1):
            s1_v_ocr = (sf1 == ep1_1 and sa1 == ep2_1)

        s2_v_ocr: Optional[bool] = None
        if s2_ocr_ok and _b(sf2, sa2, ep1_2, ep2_2):
            s2_v_ocr = (sf2 == ep2_2 and sa2 == ep1_2)

        # Determine state.
        if sub1 is None or sub2 is None:
            state, severity, rec = "waiting_one", "medium", "pending"
        elif s1_ocr_fail or s2_ocr_fail:
            state, severity, rec = "ocr_failed", "high", "rescan_needed"
        elif not s1["has_screenshot"] or not s2["has_screenshot"]:
            state, severity, rec = "missing_screenshot", "medium", "pending"
        elif sub_cons is False:
            state, severity, rec = "mismatch_submitted", "high", "needs_staff_review"
        elif ocr_cons is False:
            state, severity, rec = "mismatch_ocr", "high", "needs_staff_review"
        elif s1_v_ocr is False or s2_v_ocr is False:
            state, severity, rec = "mismatch_submitted_vs_ocr", "high", "needs_staff_review"
        elif sub_cons is True and (ocr_cons is True or ocr_cons is None) and (s1_v_ocr is not False) and (s2_v_ocr is not False):
            state, severity, rec = "consistent", "ok", "safe_to_verify"
        elif not s1_ocr_ok or not s2_ocr_ok:
            state, severity, rec = "waiting_scan", "medium", "pending"
        else:
            state, severity, rec = "inconclusive", "medium", "pending"

        result.append({
            "game_number": gn,
            "map": map_name,
            "side1": s1,
            "side2": s2,
            "state": state,
            "severity": severity,
            "recommendation": rec,
            "submitted_consistent": sub_cons,
            "ocr_cross_consistent": ocr_cons,
            "side1_sub_matches_ocr": s1_v_ocr,
            "side2_sub_matches_ocr": s2_v_ocr,
        })

    return result


# ── Flagging + audit ─────────────────────────────────────────────────────────

def check_and_flag_evidence_after_ocr(submission_id: int) -> dict:
    """Run comparison and update workflow/audit when appropriate."""
    from apps.tournaments.models.match import Match

    submission = (
        MatchResultSubmission.objects
        .select_related("match", "match__tournament", "match__tournament__game")
        .filter(pk=submission_id)
        .first()
    )
    if not submission:
        logger.warning("check_and_flag: submission %s not found", submission_id)
        return {}

    match: Match = submission.match
    terminal = {Match.COMPLETED, Match.CANCELLED, Match.FORFEIT}
    if match.state in terminal:
        return {}

    p1_id = getattr(match, "participant1_id", None)
    p2_id = getattr(match, "participant2_id", None)

    def _latest(team_id) -> Optional[MatchResultSubmission]:
        if team_id is None:
            return None
        return (
            MatchResultSubmission.objects
            .filter(match=match, submitted_by_team_id=team_id, is_archived=False)
            .order_by("-submitted_at")
            .first()
        )

    sub1 = _latest(p1_id)
    sub2 = _latest(p2_id)
    comparison = compute_evidence_comparison(sub1, sub2)

    lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
    from apps.tournaments.views.match_room import WORKFLOW_KEY, _safe_dict
    workflow = _safe_dict(lobby_info.get(WORKFLOW_KEY))
    old_status = str(workflow.get("result_status") or "")
    new_status = old_status

    if comparison["requires_review"]:
        new_status = "ocr_review_needed"
    elif comparison["safe_to_verify"] and old_status not in {
        "verified", "admin_overridden", "verified_draw", "mismatch",
        "ocr_review_needed", "staff_review_required",
    }:
        new_status = "ocr_verified_candidate"

    if new_status != old_status:
        workflow["result_status"] = new_status
        lobby_info[WORKFLOW_KEY] = workflow
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info", "updated_at"])
        _write_audit_entry(
            match=match,
            action=f"evidence_{comparison['state']}",
            detail=(f"Evidence comparison: {comparison['state']} — "
                    f"{comparison['reason']} "
                    f"[severity={comparison['severity']}]"),
            automated=True,
        )
        _broadcast_evidence_update(match)
        logger.info(
            "evidence_flagging: match=%s state=%s severity=%s "
            "safe=%s requires_review=%s old_status=%s new_status=%s",
            match.id, comparison["state"], comparison["severity"],
            comparison["safe_to_verify"], comparison["requires_review"],
            old_status, new_status,
        )

    return comparison


def _write_audit_entry(*, match, action: str, detail: str, user_id=None,
                       automated: bool = False) -> None:
    try:
        lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
        timeline = list(lobby_info.get("evidence_timeline") or [])
        timeline.append({
            "ts": timezone.now().isoformat(),
            "action": str(action),
            "detail": str(detail),
            "user_id": user_id,
            "automated": bool(automated),
        })
        lobby_info["evidence_timeline"] = timeline[-50:]
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info", "updated_at"])
    except Exception as exc:
        logger.warning("_write_audit_entry failed match=%s err=%s", match.id, exc)


def _broadcast_evidence_update(match) -> None:
    """Bump TOC cache scope AND send Channels broadcast."""
    try:
        from apps.tournaments.api.toc.cache_utils import bump_toc_scopes
        bump_toc_scopes(int(match.tournament_id), "matches")
    except Exception as exc:
        logger.warning("_broadcast_evidence_update: cache bump failed match=%s err=%s",
                       match.id, exc)
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        from django.utils import timezone as tz
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"match_{match.id}",
                {
                    "type": "match_room_event",
                    "data": {
                        "event": "evidence_comparison_updated",
                        "payload": {"match_id": match.id, "auto": True},
                        "match_id": match.id,
                        "timestamp": tz.now().isoformat(),
                    },
                },
            )
    except Exception as exc:
        logger.warning("_broadcast_evidence_update: channels failed match=%s err=%s",
                       match.id, exc)
