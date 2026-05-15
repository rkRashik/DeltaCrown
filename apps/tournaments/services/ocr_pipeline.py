"""
OCR pipeline orchestrator for participant-uploaded match evidence.

Routes a ``MatchResultSubmission.proof_screenshot`` through the correct
screenshot service (``br`` / ``sports`` / ``team_5v5``) based on the
tournament's game category and persists results on the submission row.

Public API
==========
    run_ocr_for_submission(submission, *, force=False) -> dict
    pick_service_for_game(game) -> str  # 'team_5v5' | 'sports' | 'br' | ''

Storage contract — uses the new fields added by migration 0060:
    ocr_status        ('pending' | 'running' | 'completed' | 'failed' | 'skipped')
    ocr_extracted     (game-specific JSON)
    ocr_confidence    (float 0..1 when known)
    ocr_error         (short message on failure)
    ocr_processed_at  (datetime of run end)

Design notes
------------
* This is a SYNCHRONOUS helper. Callers wanting async behaviour wrap it in
  a Celery task. Sync keeps the manual "Scan Evidence" admin button simple.
* No automatic finalization — we record OCR data but never advance match
  state based on it. Staff decides via the existing admin override path.
* Image reading: we read the bytes from the file's storage backend so the
  pipeline works for both local FileSystemStorage and Cloudinary.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.utils import timezone

from apps.tournaments.models.result_submission import MatchResultSubmission

logger = logging.getLogger("tournaments.ocr_pipeline")


# Game-category → screenshot-service slug.
_SERVICE_BY_CATEGORY = {
    "FPS":      "team_5v5",     # Valorant / CS2 / R6
    "MOBA":     "team_5v5",     # MLBB (Valorant-led prompt also handles MOBA scoreboards)
    "BR":       "br",
    "SPORTS":   "sports",
    "FIGHTING": "sports",       # 1v1, sports flow is closest fit
}


def pick_service_for_game(game) -> str:
    """Return the OCR service identifier for a Game instance, or '' if none."""
    if game is None:
        return ""
    category = str(getattr(game, "category", "") or "").upper()
    slug = str(getattr(game, "slug", "") or "").lower()
    # Direct slug overrides for known sports-style games.
    if slug in {"efootball", "ea-fc"}:
        return "sports"
    return _SERVICE_BY_CATEGORY.get(category, "")


def _read_screenshot_bytes(submission) -> tuple[bytes, str, str]:
    """Read the submission's screenshot file. Returns (bytes, content_type, filename).

    Raises ValueError when no readable screenshot is available.
    """
    proof_field = getattr(submission, "proof_screenshot", None)
    if not proof_field or not getattr(proof_field, "name", ""):
        raise ValueError("Submission has no proof_screenshot file attached.")

    try:
        storage = proof_field.storage
        with storage.open(proof_field.name, "rb") as fh:
            data = fh.read()
    except Exception as exc:
        raise ValueError(f"Could not read proof_screenshot from storage: {exc}") from exc

    name = str(proof_field.name)
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    content_type = {
        "png":  "image/png",
        "jpg":  "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
        "gif":  "image/gif",
    }.get(ext, "image/png")
    return data, content_type, name


def _mark(submission, *, status: str, extracted: Optional[Dict[str, Any]] = None,
          confidence: Optional[float] = None, error: str = "") -> None:
    """Persist OCR state on the submission. Single ``save`` with update_fields."""
    submission.ocr_status = status
    if extracted is not None:
        submission.ocr_extracted = extracted
    if confidence is not None:
        submission.ocr_confidence = float(confidence)
    submission.ocr_error = (error or "")[:500]
    submission.ocr_processed_at = timezone.now()
    submission.save(update_fields=[
        "ocr_status", "ocr_extracted", "ocr_confidence",
        "ocr_error", "ocr_processed_at",
    ])


def run_ocr_for_submission(submission_id: int, *, force: bool = False) -> Dict[str, Any]:
    """Run OCR for a single submission. Persists results on the row.

    Returns a result dict::

        {
          "submission_id": int,
          "ocr_status": str,
          "ocr_confidence": float | None,
          "ocr_extracted": dict,
          "ocr_error": str,
          "service": str,         # which OCR service ran
        }

    ``force=False`` (default) skips when ``ocr_status`` is already
    ``completed`` — pass ``force=True`` to re-run.
    """
    submission = (
        MatchResultSubmission.objects
        .select_related("match", "match__tournament", "match__tournament__game")
        .get(pk=submission_id)
    )

    result: Dict[str, Any] = {
        "submission_id": int(submission.pk),
        "ocr_status": submission.ocr_status,
        "ocr_confidence": submission.ocr_confidence,
        "ocr_extracted": submission.ocr_extracted or {},
        "ocr_error": "",
        "service": "",
    }

    if not force and submission.ocr_status == "completed":
        result["ocr_error"] = "already_completed_skipped"
        return result

    game = getattr(getattr(submission.match.tournament, "game", None), "_wrapped_object", None) \
        or getattr(submission.match.tournament, "game", None)
    service_key = pick_service_for_game(game)
    result["service"] = service_key
    if not service_key:
        _mark(submission, status="skipped", error="no_service_for_game_category")
        result["ocr_status"] = "skipped"
        result["ocr_error"] = "no_service_for_game_category"
        return result

    _mark(submission, status="running")
    result["ocr_status"] = "running"

    try:
        image_bytes, content_type, _filename = _read_screenshot_bytes(submission)
    except ValueError as exc:
        _mark(submission, status="failed", error=str(exc))
        result["ocr_status"] = "failed"
        result["ocr_error"] = str(exc)
        return result

    extracted: Dict[str, Any] = {}
    confidence: Optional[float] = None

    try:
        if service_key == "team_5v5":
            from apps.tournaments.services.team_5v5_screenshot_service import (
                process_team_5v5_screenshot,
            )
            extracted = process_team_5v5_screenshot(
                tournament=submission.match.tournament,
                match=submission.match,
                image_bytes=image_bytes,
                content_type=content_type,
                original_filename=str(getattr(submission.proof_screenshot, "name", "")),
            )
            # Use team-mapping confidence as the overall metric (closest proxy).
            conf_label = str(extracted.get("team_mapping_confidence") or "").lower()
            confidence = {"high": 0.9, "low": 0.55, "none": 0.2}.get(conf_label)
        elif service_key == "sports":
            from apps.tournaments.services.sports_screenshot_service import (
                process_sports_screenshot,
            )
            extracted = process_sports_screenshot(
                tournament=submission.match.tournament,
                match=submission.match,
                image_bytes=image_bytes,
                content_type=content_type,
                original_filename=str(getattr(submission.proof_screenshot, "name", "")),
            )
            conf_label = str(extracted.get("mapping_confidence") or "").lower()
            confidence = {"high": 0.9, "low": 0.55, "none": 0.2}.get(conf_label)
        elif service_key == "br":
            from apps.tournaments.services.br_screenshot_service import (
                process_br_screenshot,
            )
            extracted = process_br_screenshot(
                tournament=submission.match.tournament,
                match=submission.match,
                image_bytes=image_bytes,
                content_type=content_type,
                original_filename=str(getattr(submission.proof_screenshot, "name", "")),
            )
            # BR pipeline doesn't expose a single confidence — leave None.
            confidence = None
        else:
            _mark(submission, status="skipped", error=f"unhandled_service={service_key}")
            result["ocr_status"] = "skipped"
            result["ocr_error"] = f"unhandled_service={service_key}"
            return result
    except Exception as exc:
        logger.exception(
            "OCR pipeline failure submission=%s service=%s",
            submission.pk, service_key,
        )
        _mark(submission, status="failed", error=f"{exc.__class__.__name__}: {exc}")
        result["ocr_status"] = "failed"
        result["ocr_error"] = f"{exc.__class__.__name__}: {exc}"
        return result

    _mark(submission, status="completed", extracted=extracted, confidence=confidence)
    result["ocr_status"] = "completed"
    result["ocr_extracted"] = extracted
    result["ocr_confidence"] = confidence
    logger.info(
        "OCR completed submission=%s service=%s confidence=%s",
        submission.pk, service_key, confidence,
    )
    return result
