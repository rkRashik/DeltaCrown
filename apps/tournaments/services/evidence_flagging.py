"""
P3.2/P3.3 — OCR evidence comparison and review-flagging service.

After both sides' OCR is complete this service:
  1. Computes a structured ``evidence_comparison`` dict (single source of
     truth — FE reads from it rather than reimplementing logic in JS).
  2. Updates ``workflow.result_status`` to ``"review_needed"`` when scores
     disagree, or ``"ocr_verified_candidate"`` when all checks pass.
  3. Writes a match timeline audit entry.
  4. Broadcasts a ``match_room_event`` to the TOC channel so the Evidence
     tab refreshes without a manual reload.

Design constraints
------------------
* Never auto-finalises the match — only updates review status.
* Idempotent — safe to call multiple times (last write wins, same logic).
* Respects evidence retention policy — does not delete any evidence.
* Works for BO1 (single submission per side) and BO3/BO5 (latest per side).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.utils import timezone

from apps.tournaments.models.result_submission import MatchResultSubmission

logger = logging.getLogger("tournaments.evidence_flagging")

# ── OCR comparison ─────────────────────────────────────────────────────────


def _extracted_p1_p2(extracted: dict) -> tuple[Optional[int], Optional[int]]:
    """Return (participant1_score, participant2_score) from an OCR result dict.

    Handles multiple service output shapes:
      * team_5v5 / sports: ``participant1_score``, ``participant2_score``
      * sports alt:        ``home_score``, ``away_score``
      * br:                no canonical dual-side score (returns None, None)
    """
    if not isinstance(extracted, dict):
        return None, None

    def _i(v: Any) -> Optional[int]:
        try:
            n = int(v)
            return n if n >= 0 else None
        except (TypeError, ValueError):
            return None

    a = _i(extracted.get("participant1_score"))
    b = _i(extracted.get("participant2_score"))
    if a is None:
        a = _i(extracted.get("home_score"))
    if b is None:
        b = _i(extracted.get("away_score"))
    return a, b


def compute_evidence_comparison(
    side1_sub: Optional[MatchResultSubmission],
    side2_sub: Optional[MatchResultSubmission],
    *,
    match=None,
) -> Dict[str, Any]:
    """Return a structured evidence comparison dict.

    Shape::

        {
          "state": "consistent" | "mismatch_submitted" | "mismatch_ocr"
                 | "mismatch_submitted_vs_ocr" | "waiting_both"
                 | "waiting_one" | "waiting_scan" | "ocr_failed"
                 | "missing_screenshot" | "inconclusive",
          "recommendation": "safe_to_verify" | "needs_staff_review"
                          | "pending" | "rescan_needed",
          "reason": str,
          "submitted_consistent": bool | None,
          "ocr_cross_consistent": bool | None,
          "side1_sub_matches_ocr": bool | None,
          "side2_sub_matches_ocr": bool | None,
          "side1": { "submitted_for": int|None, "submitted_against": int|None,
                     "ocr_p1": int|None, "ocr_p2": int|None,
                     "ocr_status": str, "has_screenshot": bool },
          "side2": { same shape },
        }
    """

    def _sub_info(sub: Optional[MatchResultSubmission]) -> dict:
        if sub is None:
            return {
                "submitted_for": None, "submitted_against": None,
                "ocr_p1": None, "ocr_p2": None,
                "ocr_status": "", "has_screenshot": False,
            }
        try:
            sf = int(sub.score_for) if sub.score_for is not None else None
        except (TypeError, ValueError):
            sf = None
        try:
            sa = int(sub.score_against) if sub.score_against is not None else None
        except (TypeError, ValueError):
            sa = None
        ep1, ep2 = _extracted_p1_p2(sub.ocr_extracted or {})
        has_shot = bool(
            (getattr(sub, "proof_screenshot", None) and sub.proof_screenshot.name)
            or (sub.proof_screenshot_url or "").strip()
        )
        return {
            "submitted_for": sf,
            "submitted_against": sa,
            "ocr_p1": ep1,
            "ocr_p2": ep2,
            "ocr_status": str(sub.ocr_status or ""),
            "has_screenshot": has_shot,
        }

    s1 = _sub_info(side1_sub)
    s2 = _sub_info(side2_sub)

    # ── Guards ─────────────────────────────────────────────────────────
    if side1_sub is None and side2_sub is None:
        return _result("waiting_both", "pending", "Neither side has submitted.", s1, s2,
                       None, None, None, None)
    if side1_sub is None or side2_sub is None:
        return _result("waiting_one", "pending",
                       "Waiting for the other side to submit.", s1, s2,
                       None, None, None, None)
    if not s1["has_screenshot"] or not s2["has_screenshot"]:
        return _result("missing_screenshot", "pending",
                       "One or both sides submitted without a screenshot.",
                       s1, s2, None, None, None, None)
    if s1["ocr_status"] == "failed" or s2["ocr_status"] == "failed":
        return _result("ocr_failed", "rescan_needed",
                       "OCR failed on one or both sides. Retry scan.",
                       s1, s2, None, None, None, None)
    if s1["ocr_status"] != "completed" or s2["ocr_status"] != "completed":
        return _result("waiting_scan", "pending",
                       "OCR not yet completed for all submissions.",
                       s1, s2, None, None, None, None)

    # ── Score comparisons ──────────────────────────────────────────────
    # Submitted consistency — side1's perspective vs side2's.
    sub_cons: Optional[bool] = None
    if all(v is not None for v in [s1["submitted_for"], s1["submitted_against"],
                                    s2["submitted_for"], s2["submitted_against"]]):
        sub_cons = (s1["submitted_for"] == s2["submitted_against"] and
                    s1["submitted_against"] == s2["submitted_for"])

    # Both OCRs agree on participant1 / participant2 absolute scores.
    ocr_cons: Optional[bool] = None
    if all(v is not None for v in [s1["ocr_p1"], s1["ocr_p2"],
                                    s2["ocr_p1"], s2["ocr_p2"]]):
        ocr_cons = (s1["ocr_p1"] == s2["ocr_p1"] and s1["ocr_p2"] == s2["ocr_p2"])

    # Side1's submitted matches side1's OCR (their for=p1, against=p2).
    s1_vs_ocr: Optional[bool] = None
    if (s1["submitted_for"] is not None and s1["submitted_against"] is not None
            and s1["ocr_p1"] is not None and s1["ocr_p2"] is not None):
        s1_vs_ocr = (s1["submitted_for"] == s1["ocr_p1"] and
                     s1["submitted_against"] == s1["ocr_p2"])

    # Side2 is participant2 — their for=p2, against=p1.
    s2_vs_ocr: Optional[bool] = None
    if (s2["submitted_for"] is not None and s2["submitted_against"] is not None
            and s2["ocr_p1"] is not None and s2["ocr_p2"] is not None):
        s2_vs_ocr = (s2["submitted_for"] == s2["ocr_p2"] and
                     s2["submitted_against"] == s2["ocr_p1"])

    # ── Determine overall state ────────────────────────────────────────
    if sub_cons is False:
        return _result("mismatch_submitted", "needs_staff_review",
                       "Submitted scores disagree between participants.",
                       s1, s2, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr)
    if ocr_cons is False:
        return _result("mismatch_ocr", "needs_staff_review",
                       "Screenshots extract different scores. Manual review needed.",
                       s1, s2, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr)
    if s1_vs_ocr is False or s2_vs_ocr is False:
        return _result("mismatch_submitted_vs_ocr", "needs_staff_review",
                       "At least one side's screenshot extract differs from their submission.",
                       s1, s2, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr)
    if (sub_cons is True and ocr_cons is True
            and s1_vs_ocr is True and s2_vs_ocr is True):
        return _result("consistent", "safe_to_verify",
                       "All checks pass. Evidence is consistent — safe to verify.",
                       s1, s2, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr)
    return _result("inconclusive", "pending",
                   "Comparison incomplete — some checks could not run.",
                   s1, s2, sub_cons, ocr_cons, s1_vs_ocr, s2_vs_ocr)


def _result(state, rec, reason, s1, s2, sub_cons, ocr_cons, s1_ocr, s2_ocr) -> dict:
    return {
        "state": state,
        "recommendation": rec,
        "reason": reason,
        "submitted_consistent": sub_cons,
        "ocr_cross_consistent": ocr_cons,
        "side1_sub_matches_ocr": s1_ocr,
        "side2_sub_matches_ocr": s2_ocr,
        "side1": s1,
        "side2": s2,
    }


# ── Flagging + audit ───────────────────────────────────────────────────────


def check_and_flag_evidence_after_ocr(submission_id: int) -> dict:
    """Run comparison and update workflow/audit when appropriate.

    Called automatically after OCR completes (P3.1 task). Also safe to
    call manually from the admin review endpoint.

    Returns the ``evidence_comparison`` dict for the caller's use.
    """
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
    tournament = match.tournament

    # Only act while the match is in an active / review state.
    terminal = {Match.COMPLETED, Match.CANCELLED, Match.FORFEIT}
    if match.state in terminal:
        return {}

    # Load the latest submission per side.
    p1_id = getattr(match, "participant1_id", None)
    p2_id = getattr(match, "participant2_id", None)

    def _latest(team_id) -> Optional[MatchResultSubmission]:
        if team_id is None:
            return None
        return (
            MatchResultSubmission.objects
            .filter(match=match, submitted_by_team_id=team_id)
            .order_by("-submitted_at")
            .first()
        )

    sub1 = _latest(p1_id)
    sub2 = _latest(p2_id)
    comparison = compute_evidence_comparison(sub1, sub2)
    state = comparison.get("state", "inconclusive")
    recommendation = comparison.get("recommendation", "pending")

    # Update workflow result_status to reflect evidence state.
    lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
    from apps.tournaments.views.match_room import WORKFLOW_KEY, _safe_dict
    workflow = _safe_dict(lobby_info.get(WORKFLOW_KEY))
    old_status = str(workflow.get("result_status") or "")
    new_status = old_status

    if recommendation == "needs_staff_review":
        new_status = "ocr_review_needed"
        if match.state not in {Match.DISPUTED}:
            pass  # don't change Match.state automatically — preserve participant flow
    elif recommendation == "safe_to_verify" and old_status not in {
        "verified", "admin_overridden", "verified_draw",
        "mismatch", "ocr_review_needed",
    }:
        new_status = "ocr_verified_candidate"

    if new_status != old_status:
        workflow["result_status"] = new_status
        lobby_info[WORKFLOW_KEY] = workflow
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info", "updated_at"])

        _write_audit_entry(
            match=match,
            action=f"evidence_{state}",
            detail=f"Evidence comparison: {state} — {comparison.get('reason', '')}",
            automated=True,
        )
        _broadcast_evidence_update(match)
        logger.info(
            "evidence_flagging: match=%s state=%s recommendation=%s old_status=%s new_status=%s",
            match.id, state, recommendation, old_status, new_status,
        )

    return comparison


def _write_audit_entry(*, match, action: str, detail: str, user_id=None,
                       automated: bool = False) -> None:
    """Append a timeline entry to the match lobby_info audit log."""
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
        # Rolling window — keep last 50 entries.
        lobby_info["evidence_timeline"] = timeline[-50:]
        match.lobby_info = lobby_info
        match.save(update_fields=["lobby_info", "updated_at"])
    except Exception as exc:
        logger.warning("_write_audit_entry failed match=%s err=%s", match.id, exc)


def _broadcast_evidence_update(match) -> None:
    """Notify TOC channel that evidence state changed."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        from django.utils import timezone as tz
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        async_to_sync(channel_layer.group_send)(
            f"toc_{match.tournament_id}",
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
        logger.warning("_broadcast_evidence_update failed match=%s err=%s", match.id, exc)
