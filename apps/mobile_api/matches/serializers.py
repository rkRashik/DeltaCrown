"""Mobile-safe serializers for match endpoints."""
from __future__ import annotations

from apps.organizations.models import Team, TeamMembership
from apps.tournaments.models import Match, MatchResultSubmission
from apps.tournaments.models.dispute import DisputeRecord


SAFE_LOBBY_KEYS = {
    "map",
    "mode",
    "server",
    "region",
    "lobby_code",
    "lobby_name",
    "password",
    "instructions",
    "room_id",
    "voice_url",
    "stream_url",
}


def match_card(match: Match, user) -> dict:
    side = participant_side(match, user)
    latest_submission = latest_result_submission(match)
    return {
        "id": match.id,
        "tournament": tournament_summary(match.tournament),
        "game": game_summary(getattr(match.tournament, "game", None)),
        "status": match.state,
        "round": match.round_number,
        "stage": None,
        "match_number": match.match_number,
        "scheduled_time": match.scheduled_time.isoformat() if match.scheduled_time else None,
        "user_side": side_summary(match, side),
        "opponent_side": side_summary(match, opponent_side(side)),
        "lobby": lobby_summary(match, side),
        "result_submission": result_submission_summary(latest_submission),
        "next_action": next_action(match, side, latest_submission),
    }


def match_detail(match: Match, user) -> dict:
    data = match_card(match, user)
    data.update(
        {
            "best_of": match.best_of,
            "scores": {
                "participant1": match.participant1_score,
                "participant2": match.participant2_score,
                "games": match.game_scores or [],
            },
            "winner": side_summary(match, _winner_side(match)),
            "started_at": match.started_at.isoformat() if match.started_at else None,
            "completed_at": match.completed_at.isoformat() if match.completed_at else None,
        }
    )
    return data


def lobby_detail(match: Match, user) -> dict:
    side = participant_side(match, user)
    lobby_info = match.lobby_info if isinstance(match.lobby_info, dict) else {}
    safe_lobby_info = {key: value for key, value in lobby_info.items() if key in SAFE_LOBBY_KEYS}
    return {
        "match": match_card(match, user),
        "match_state": match.state,
        "scheduled_time": match.scheduled_time.isoformat() if match.scheduled_time else None,
        "check_in_deadline": match.check_in_deadline.isoformat() if match.check_in_deadline else None,
        "lobby_info": safe_lobby_info,
        "setup_instructions": safe_lobby_info.get("instructions", ""),
        "user_readiness": readiness_summary(match, side),
        "opponent_readiness": readiness_summary(match, opponent_side(side)),
        "next_action": next_action(match, side, latest_result_submission(match)),
    }


def polling_status(match: Match, user) -> dict:
    side = participant_side(match, user)
    submission = latest_result_submission(match)
    dispute = latest_dispute(submission)
    return {
        "match_id": match.id,
        "match_status": match.state,
        "lobby": lobby_summary(match, side),
        "result_status": submission.status if submission else None,
        "dispute_status": dispute.status if dispute else None,
        "updated_at": match.updated_at.isoformat() if match.updated_at else None,
        "next_action": next_action(match, side, submission),
    }


def tournament_summary(tournament) -> dict:
    return {
        "id": tournament.id,
        "slug": tournament.slug,
        "name": tournament.name,
        "status": tournament.status,
    }


def game_summary(game) -> dict | None:
    if game is None:
        return None
    return {
        "id": game.id,
        "name": game.display_name or game.name,
        "slug": game.slug,
        "short_code": game.short_code,
    }


def side_summary(match: Match, side: int | None) -> dict | None:
    if side == 1:
        return _participant_summary(match.participant1_id, match.participant1_name)
    if side == 2:
        return _participant_summary(match.participant2_id, match.participant2_name)
    return None


def readiness_summary(match: Match, side: int | None) -> dict | None:
    if side == 1:
        return {"side": 1, "checked_in": match.participant1_checked_in}
    if side == 2:
        return {"side": 2, "checked_in": match.participant2_checked_in}
    return None


def lobby_summary(match: Match, side: int | None) -> dict:
    return {
        "state": match.state,
        "check_in_required": bool(match.check_in_deadline),
        "check_in_deadline": match.check_in_deadline.isoformat() if match.check_in_deadline else None,
        "user_checked_in": _checked_in_for_side(match, side),
        "opponent_checked_in": _checked_in_for_side(match, opponent_side(side)),
        "both_checked_in": match.is_both_checked_in,
    }


def result_submission_summary(submission: MatchResultSubmission | None) -> dict | None:
    if submission is None:
        return None
    proof_url = submission.proof_screenshot_url or ""
    if not proof_url and submission.proof_screenshot:
        try:
            proof_url = submission.proof_screenshot.url
        except Exception:
            proof_url = ""
    return {
        "id": submission.id,
        "status": submission.status,
        "submitted_by_user_id": submission.submitted_by_user_id,
        "submitted_by_team_id": submission.submitted_by_team_id,
        "proof_url": proof_url or None,
        "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
        "auto_confirm_deadline": submission.auto_confirm_deadline.isoformat() if submission.auto_confirm_deadline else None,
    }


def next_action(match: Match, side: int | None, submission: MatchResultSubmission | None = None) -> str:
    if side is None:
        return "none"
    if match.state == Match.CHECK_IN and not _checked_in_for_side(match, side):
        return "check_in"
    if match.state in [Match.READY, Match.LIVE] and match.lobby_info:
        return "open_lobby"
    if match.state == Match.LIVE:
        return "submit_result"
    if match.state == Match.PENDING_RESULT:
        return "view_result" if submission else "submit_result"
    if match.state == Match.DISPUTED:
        return "view_dispute"
    if match.state in [Match.COMPLETED, Match.FORFEIT]:
        return "view_result"
    return "none"


def participant_side(match: Match, user) -> int | None:
    if not user or not user.is_authenticated:
        return None
    if _user_matches_participant(match, user, match.participant1_id):
        return 1
    if _user_matches_participant(match, user, match.participant2_id):
        return 2
    return None


def user_can_access_match(match: Match, user) -> bool:
    return participant_side(match, user) is not None


def opponent_side(side: int | None) -> int | None:
    if side == 1:
        return 2
    if side == 2:
        return 1
    return None


def latest_result_submission(match: Match) -> MatchResultSubmission | None:
    return (
        MatchResultSubmission.objects.filter(match=match, is_archived=False)
        .order_by("-submitted_at", "-id")
        .first()
    )


def latest_dispute(submission: MatchResultSubmission | None) -> DisputeRecord | None:
    if submission is None:
        return None
    return DisputeRecord.objects.filter(submission=submission, is_deleted=False).order_by("-created_at").first()


def _participant_summary(participant_id: int | None, name: str) -> dict | None:
    if participant_id is None:
        return None
    team = Team.objects.filter(id=participant_id).first()
    if team:
        return {
            "id": participant_id,
            "type": "team",
            "name": team.name,
            "slug": team.slug,
            "tag": team.tag,
        }
    return {
        "id": participant_id,
        "type": "player",
        "name": name or f"Player {participant_id}",
    }


def _user_matches_participant(match: Match, user, participant_id: int | None) -> bool:
    if participant_id is None:
        return False
    if participant_id == user.id:
        return True
    return TeamMembership.objects.filter(
        team_id=participant_id,
        user=user,
        status=TeamMembership.Status.ACTIVE,
    ).exists()


def _checked_in_for_side(match: Match, side: int | None) -> bool | None:
    if side == 1:
        return match.participant1_checked_in
    if side == 2:
        return match.participant2_checked_in
    return None


def _winner_side(match: Match) -> int | None:
    if match.winner_id == match.participant1_id:
        return 1
    if match.winner_id == match.participant2_id:
        return 2
    return None
