"""Mobile match service helpers."""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.organizations.models import TeamMembership
from apps.tournaments.models import Match, MatchResultSubmission

from .serializers import participant_side, result_submission_summary


ALLOWED_RESULT_STATES = {Match.LIVE, Match.PENDING_RESULT}


def matches_for_user(user):
    team_ids = list(
        TeamMembership.objects.filter(user=user, status=TeamMembership.Status.ACTIVE).values_list("team_id", flat=True)
    )
    participant_ids = [user.id, *team_ids]
    return Match.objects.filter(
        Q(participant1_id__in=participant_ids) | Q(participant2_id__in=participant_ids),
        is_deleted=False,
    )


def check_in_match(match: Match, user) -> dict:
    side = participant_side(match, user)
    if side is None:
        raise MobileMatchValidation("permission_denied", "You cannot check in for this match.", status_code=403)
    if match.state not in {Match.CHECK_IN, Match.READY, Match.LIVE}:
        raise MobileMatchValidation("invalid_state", "Check-in is not open for this match.")
    if match.check_in_deadline and timezone.now() > match.check_in_deadline:
        raise MobileMatchValidation("check_in_closed", "The match check-in window is closed.")

    update_fields = ["updated_at"]
    if side == 1 and not match.participant1_checked_in:
        match.participant1_checked_in = True
        update_fields.append("participant1_checked_in")
    elif side == 2 and not match.participant2_checked_in:
        match.participant2_checked_in = True
        update_fields.append("participant2_checked_in")

    if match.state == Match.CHECK_IN and match.participant1_checked_in and match.participant2_checked_in:
        match.state = Match.READY
        update_fields.append("state")

    match.save(update_fields=update_fields)
    return {"checked_in": True, "side": side}


def submit_match_result(match: Match, user, payload: dict, proof_url: str = "", proof_file=None) -> MatchResultSubmission:
    side = participant_side(match, user)
    if side is None:
        raise MobileMatchValidation("permission_denied", "You cannot submit a result for this match.", status_code=403)
    if match.state not in ALLOWED_RESULT_STATES:
        raise MobileMatchValidation("invalid_state", "This match is not accepting result submissions.")

    result_payload = payload.get("result_payload") if isinstance(payload.get("result_payload"), dict) else {}
    score = payload.get("score")
    if score is not None:
        result_payload["score"] = score
    result_payload.setdefault("side", side)

    submitted_by_team_id = _team_id_for_side(match, side)
    try:
        with transaction.atomic():
            submission = MatchResultSubmission.objects.create(
                match=match,
                submitted_by_user=user,
                submitted_by_team_id=submitted_by_team_id,
                raw_result_payload=result_payload,
                proof_screenshot_url=(proof_url or payload.get("proof_url") or payload.get("proof_screenshot_url") or "")[:500],
                submitter_notes=(payload.get("notes") or "")[:2000],
            )
            if proof_file is not None:
                submission.proof_screenshot = proof_file
                submission.save(update_fields=["proof_screenshot"])
            if match.state == Match.LIVE:
                match.state = Match.PENDING_RESULT
                match.save(update_fields=["state", "updated_at"])
    except IntegrityError as exc:
        raise MobileMatchValidation("result_submission_failed", "Result submission could not be saved.") from exc
    return submission


def upload_match_proof(match: Match, user, proof_url: str = "", proof_file=None) -> dict:
    side = participant_side(match, user)
    if side is None:
        raise MobileMatchValidation("permission_denied", "You cannot upload proof for this match.", status_code=403)

    submission = (
        MatchResultSubmission.objects.filter(match=match, submitted_by_user=user, is_archived=False)
        .order_by("-submitted_at", "-id")
        .first()
    )
    if submission is None:
        submission = submit_match_result(
            match,
            user,
            {"result_payload": {"side": side}, "notes": ""},
            proof_url=proof_url,
            proof_file=proof_file,
        )
    else:
        update_fields = []
        if proof_url:
            submission.proof_screenshot_url = proof_url[:500]
            update_fields.append("proof_screenshot_url")
        if proof_file is not None:
            submission.proof_screenshot = proof_file
            update_fields.append("proof_screenshot")
        if update_fields:
            submission.save(update_fields=update_fields)

    note = None
    if proof_file is None:
        note = "proof_url accepted. Native multipart upload can use proof_file when mobile storage is ready."
    return {"submission": result_submission_summary(submission), "note": note}


def _team_id_for_side(match: Match, side: int) -> int | None:
    participant_id = match.participant1_id if side == 1 else match.participant2_id
    if TeamMembership.objects.filter(team_id=participant_id).exists():
        return participant_id
    return None


class MobileMatchValidation(Exception):
    def __init__(self, code: str, message: str, *, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)
