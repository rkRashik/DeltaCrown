"""Unified competitive operations feed for the dashboard hub."""
from __future__ import annotations

from typing import Any

from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.competition.models import Bounty, BountyClaim, Challenge
from apps.contracts.models import ContractEnrollment
from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.organizations.models.membership import TeamMembership
from apps.royale.models import RoyaleEntry


HUB_URLS = {
    "showdown": "/dashboard/competitive/#showdown",
    "mission": "/dashboard/competitive/#missions",
    "bounty": "/dashboard/competitive/#bounty",
    "dropzone": "/dashboard/competitive/#dropzone",
}

TERMINAL_CHALLENGE_STATUSES = {"COMPLETED", "SETTLED", "DECLINED", "EXPIRED", "CANCELLED", "ADMIN_RESOLVED"}
TERMINAL_MISSION_STATUSES = {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED", "VOIDED"}
TERMINAL_BOUNTY_STATUSES = {"CLAIMED", "VERIFIED", "PAID", "EXPIRED", "CANCELLED"}
TERMINAL_BOUNTY_CLAIM_STATUSES = {"VERIFIED", "REJECTED", "PAID"}
TERMINAL_DROPZONE_STATUSES = {"SCORED", "NO_SHOW", "REFUNDED", "VOIDED"}
MATCH_REVIEW_STATUSES = {"mismatch", "tie_pending_review", "admin_tie_pending_review"}
MATCH_VERIFIED_STATUSES = {"verified", "verified_draw", "admin_overridden", "admin_overridden_draw"}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def _game_payload(game: Any) -> dict[str, Any] | None:
    if not game:
        return None
    return {
        "id": game.id,
        "name": getattr(game, "display_name", None) or getattr(game, "name", ""),
        "short_code": getattr(game, "short_code", "") or "",
    }


def _match_room_url(match: Any) -> str | None:
    if not match or not getattr(match, "tournament_id", None):
        return None
    tournament = getattr(match, "tournament", None)
    if not tournament or not getattr(tournament, "slug", ""):
        return None
    try:
        return reverse("tournaments:match_room", kwargs={"slug": tournament.slug, "match_id": match.id})
    except NoReverseMatch:
        return None


def _safe_match_workflow(match: Any) -> dict[str, Any]:
    lobby_info = getattr(match, "lobby_info", None)
    if not isinstance(lobby_info, dict):
        return {}
    workflow = lobby_info.get("match_lobby_workflow") or lobby_info.get("premium_lobby_workflow")
    return workflow if isinstance(workflow, dict) else {}


def _linked_match_result_state(match: Any, *, viewer_team_id: int | None = None) -> dict[str, Any]:
    """Summarize tournament Match Room proof/result state for competitive wrappers.

    This is intentionally read-only. Settlement still stays in the competitive
    service/admin layer until a later phase defines a safe automatic bridge.
    """
    if not match:
        return {
            "state": "missing",
            "match_state": None,
            "result_status": None,
            "submission_count": 0,
            "viewer_has_submission": False,
            "open_dispute_count": 0,
        }

    workflow = _safe_match_workflow(match)
    result_status = str(workflow.get("result_status") or "").strip().lower() or None
    match_state = str(getattr(match, "state", "") or "").strip().lower()

    try:
        submissions = list(match.result_submissions.all())
    except Exception:
        submissions = []

    open_dispute_count = 0
    for submission in submissions:
        try:
            disputes = submission.disputes.all()
        except Exception:
            disputes = []
        for dispute in disputes:
            is_open = getattr(dispute, "is_open", None)
            if callable(is_open):
                open_dispute_count += 1 if is_open() else 0
            else:
                status = str(getattr(dispute, "status", "") or "").lower()
                open_dispute_count += 1 if status in {"open", "under_review", "escalated"} else 0

    viewer_has_submission = bool(
        viewer_team_id
        and any(getattr(submission, "submitted_by_team_id", None) == viewer_team_id for submission in submissions)
    )

    if open_dispute_count or match_state == "disputed" or result_status in MATCH_REVIEW_STATUSES:
        state = "under_review"
    elif match_state == "completed" or result_status in MATCH_VERIFIED_STATUSES:
        state = "finalized"
    elif submissions:
        state = "viewer_submitted" if viewer_has_submission else "opponent_submitted"
    elif match_state == "pending_result" or str(workflow.get("phase") or "").lower() == "results":
        state = "result_needed"
    elif match_state in {"live", "ready", "scheduled", "check_in"}:
        state = "room_ready"
    else:
        state = "room_ready"

    return {
        "state": state,
        "match_state": match_state or None,
        "result_status": result_status,
        "submission_count": len(submissions),
        "viewer_has_submission": viewer_has_submission,
        "open_dispute_count": open_dispute_count,
    }


def _base_item(
    *,
    item_id: str,
    item_type: str,
    title: str,
    status: str,
    game: Any,
    team_name: str | None = None,
    team_id: int | None = None,
    entry_fee_dc: int | None = None,
    reward_dc: int | None = None,
    reward_summary: str | None = None,
    starts_at: Any = None,
    scheduled_at: Any = None,
    created_at: Any = None,
    next_action_label: str = "View Details",
    next_action_url: str | None = None,
    match_room_url: str | None = None,
    detail_url: str | None = None,
    is_action_required: bool = False,
    **extra: Any,
) -> dict[str, Any]:
    item = {
        "id": item_id,
        "type": item_type,
        "title": title,
        "status": status,
        "game": _game_payload(game),
        "team_name": team_name,
        "team_id": team_id,
        "entry_fee_dc": entry_fee_dc,
        "reward_dc": reward_dc,
        "reward_summary": reward_summary,
        "starts_at": _iso(starts_at),
        "scheduled_at": _iso(scheduled_at),
        "created_at": _iso(created_at),
        "next_action_label": next_action_label,
        "next_action_url": next_action_url,
        "match_room_url": match_room_url,
        "detail_url": detail_url,
        "is_action_required": is_action_required,
    }
    item.update(extra)
    return item


class MyCompetitiveOperationsView(APIView):
    """Return the current user's canonical competitive operations feed."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        authority_team_ids = self._authority_team_ids(request.user)
        operations: list[dict[str, Any]] = []

        operations.extend(self._showdown_items(authority_team_ids))
        operations.extend(self._mission_items(request.user))
        operations.extend(self._bounty_items(authority_team_ids))
        operations.extend(self._dropzone_items(request.user))

        operations.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return Response({"count": len(operations), "results": operations})

    def _authority_team_ids(self, user) -> list[int]:
        return list(
            TeamMembership.objects.filter(user=user, status=MembershipStatus.ACTIVE)
            .filter(
                Q(role__in=[MembershipRole.OWNER, MembershipRole.MANAGER])
                | Q(is_tournament_captain=True)
            )
            .values_list("team_id", flat=True)
            .distinct()
        )

    def _showdown_items(self, team_ids: list[int]) -> list[dict[str, Any]]:
        if not team_ids:
            return []

        showdowns = (
            Challenge.objects.filter(
                Q(challenger_team_id__in=team_ids) | Q(challenged_team_id__in=team_ids)
            )
            .select_related("challenger_team", "challenged_team", "game", "match__tournament")
            .prefetch_related("result_submissions", "match__result_submissions__disputes")
            .order_by("-created_at")[:50]
        )

        items = []
        for showdown in showdowns:
            owned_teams = [
                team for team in (showdown.challenger_team, showdown.challenged_team)
                if team is not None and team.id in team_ids
            ]
            submitted_team_ids = {sub.team_id for sub in showdown.result_submissions.all()}
            own_team = next(
                (team for team in owned_teams if team.id not in submitted_team_ids),
                owned_teams[0] if owned_teams else None,
            )
            match_url = _match_room_url(showdown.match)
            linked_result = _linked_match_result_state(
                showdown.match,
                viewer_team_id=getattr(own_team, "id", None),
            )
            label, action_url, required = self._showdown_action(
                showdown,
                own_team,
                match_url,
                linked_result=linked_result,
            )
            items.append(
                _base_item(
                    item_id=str(showdown.id),
                    item_type="showdown",
                    title=showdown.title or f"Showdown {showdown.reference_code}",
                    status=showdown.status,
                    game=showdown.game,
                    team_name=getattr(own_team, "name", None),
                    team_id=getattr(own_team, "id", None),
                    entry_fee_dc=showdown.entry_fee_dc,
                    reward_dc=getattr(showdown, "prize_pot_dc", None),
                    scheduled_at=showdown.scheduled_at,
                    created_at=showdown.created_at,
                    next_action_label=label,
                    next_action_url=action_url,
                    match_room_url=match_url,
                    detail_url=HUB_URLS["showdown"],
                    is_action_required=required,
                    linked_match_id=getattr(showdown.match, "id", None),
                    linked_match_state=linked_result["match_state"],
                    linked_result_state=linked_result["state"],
                    linked_result_status=linked_result["result_status"],
                    linked_result_submission_count=linked_result["submission_count"],
                    linked_open_dispute_count=linked_result["open_dispute_count"],
                    challenger_team_name=getattr(showdown.challenger_team, "name", None),
                    challenged_team_name=getattr(showdown.challenged_team, "name", None),
                    submit_result_url=None if match_url else f"/api/v1/challenges/{showdown.id}/result/",
                )
            )
        return items

    def _mission_items(self, user) -> list[dict[str, Any]]:
        enrollments = (
            ContractEnrollment.objects.filter(user=user)
            .select_related("template", "template__game")
            .order_by("-enrolled_at")[:50]
        )

        items = []
        for enrollment in enrollments:
            template = enrollment.template
            if enrollment.status == "ACTIVE":
                label = "Track Mission"
                required = True
            elif enrollment.status == "COMPLETED":
                label = "View Result"
                required = False
            elif enrollment.status == "FAILED":
                label = "Mission Failed"
                required = False
            elif enrollment.status == "EXPIRED":
                label = "Expired"
                required = False
            elif enrollment.status == "VOIDED":
                label = "Refunded"
                required = False
            elif enrollment.status == "CANCELLED":
                label = "Closed"
                required = False
            elif enrollment.status in TERMINAL_MISSION_STATUSES:
                label = "View Result"
                required = False
            else:
                label = "View Details"
                required = False

            items.append(
                _base_item(
                    item_id=str(enrollment.id),
                    item_type="mission",
                    title=template.title,
                    status=enrollment.status,
                    game=template.game,
                    entry_fee_dc=template.entry_fee_dc,
                    reward_dc=template.reward_dc,
                    starts_at=enrollment.enrolled_at,
                    scheduled_at=enrollment.deadline_at,
                    created_at=enrollment.enrolled_at,
                    next_action_label=label,
                    next_action_url=HUB_URLS["mission"],
                    detail_url=HUB_URLS["mission"],
                    is_action_required=required,
                )
            )
        return items

    def _bounty_items(self, team_ids: list[int]) -> list[dict[str, Any]]:
        if not team_ids:
            return []

        items = []
        issued = (
            Bounty.objects.filter(issuer_team_id__in=team_ids)
            .select_related("issuer_team", "game")
            .order_by("-created_at")[:50]
        )
        for bounty in issued:
            if bounty.status in TERMINAL_BOUNTY_STATUSES:
                label = "View Result"
            else:
                label = "View Bounty"
            items.append(
                _base_item(
                    item_id=f"issued:{bounty.id}",
                    item_type="bounty",
                    title=bounty.title,
                    status=bounty.status,
                    game=bounty.game,
                    team_name=getattr(bounty.issuer_team, "name", None),
                    entry_fee_dc=getattr(bounty, "challenger_entry_fee_dc", None),
                    reward_dc=getattr(bounty, "reward_amount_dc", None),
                    reward_summary=bounty.reward_description or None,
                    created_at=bounty.created_at,
                    next_action_label=label,
                    next_action_url=HUB_URLS["bounty"],
                    detail_url=HUB_URLS["bounty"],
                    is_action_required=False,
                )
            )

        claims = (
            BountyClaim.objects.filter(claiming_team_id__in=team_ids)
            .select_related(
                "bounty",
                "bounty__game",
                "bounty__issuer_team",
                "claiming_team",
                "challenge",
                "challenge__match__tournament",
                "match__tournament",
            )
            .prefetch_related("match__result_submissions__disputes", "challenge__match__result_submissions__disputes")
            .order_by("-claimed_at")[:50]
        )
        for claim in claims:
            claim_match = claim.match or getattr(claim.challenge, "match", None)
            match_url = _match_room_url(claim_match)
            linked_result = _linked_match_result_state(
                claim_match,
                viewer_team_id=getattr(claim.claiming_team, "id", None),
            )
            label, action_url, required = self._bounty_claim_action(
                claim.status,
                match_url,
                linked_result=linked_result,
            )
            items.append(
                _base_item(
                    item_id=f"claim:{claim.id}",
                    item_type="bounty",
                    title=claim.bounty.title,
                    status=claim.status,
                    game=claim.bounty.game,
                    team_name=getattr(claim.claiming_team, "name", None),
                    entry_fee_dc=getattr(claim.bounty, "challenger_entry_fee_dc", None),
                    reward_dc=getattr(claim.bounty, "reward_amount_dc", None),
                    reward_summary=claim.bounty.reward_description or None,
                    scheduled_at=getattr(claim.challenge, "scheduled_at", None),
                    created_at=claim.claimed_at,
                    next_action_label=label,
                    next_action_url=action_url,
                    match_room_url=match_url,
                    detail_url=HUB_URLS["bounty"],
                    is_action_required=required,
                    linked_match_id=getattr(claim_match, "id", None),
                    linked_match_state=linked_result["match_state"],
                    linked_result_state=linked_result["state"],
                    linked_result_status=linked_result["result_status"],
                    linked_result_submission_count=linked_result["submission_count"],
                    linked_open_dispute_count=linked_result["open_dispute_count"],
                )
            )
        return items

    def _dropzone_items(self, user) -> list[dict[str, Any]]:
        entries = (
            RoyaleEntry.objects.filter(user=user)
            .select_related("lobby", "lobby__game", "lobby__tournament")
            .order_by("-reserved_at")[:50]
        )

        items = []
        now = timezone.now()
        for entry in entries:
            lobby = entry.lobby
            credentials_ready = bool((lobby.room_id or lobby.room_password) and lobby.scheduled_at <= now)
            if entry.status in {"REFUNDED", "VOIDED"}:
                label = "Refunded"
                required = False
            elif entry.status in {"SCORED", "NO_SHOW"} or lobby.status == "SETTLED":
                label = "View Result"
                required = False
            elif lobby.status in {"LIVE", "SCORING"}:
                label = "Awaiting Results"
                required = False
            elif credentials_ready:
                label = "View Room Details"
                required = True
            else:
                label = "View Entry"
                required = False

            items.append(
                _base_item(
                    item_id=str(entry.id),
                    item_type="dropzone",
                    title=lobby.title,
                    status=entry.status,
                    game=lobby.game,
                    entry_fee_dc=lobby.entry_fee_dc,
                    reward_summary=self._dropzone_reward_summary(lobby.prize_distribution),
                    scheduled_at=lobby.scheduled_at,
                    created_at=entry.reserved_at,
                    next_action_label=label,
                    next_action_url=HUB_URLS["dropzone"],
                    detail_url=HUB_URLS["dropzone"],
                    is_action_required=required,
                )
            )
        return items

    def _showdown_action(
        self,
        showdown,
        own_team,
        match_url: str | None,
        *,
        linked_result: dict[str, Any] | None = None,
    ) -> tuple[str, str | None, bool]:
        status = showdown.status
        linked_result = linked_result or {}
        linked_state = linked_result.get("state")

        if match_url and linked_state == "under_review":
            return "Under Review", match_url, False
        if match_url and linked_state == "finalized" and showdown.settled_at is None:
            return "Proof Under Review", match_url, False
        if match_url and linked_state == "viewer_submitted":
            return "Proof Under Review", match_url, False
        if match_url and linked_state in {"opponent_submitted", "result_needed"}:
            return "Submit Result in Match Room", match_url, True

        if status == "OPEN":
            return "Waiting for opponent", HUB_URLS["showdown"], False
        if status in {"ACCEPTED", "SCHEDULED", "IN_PROGRESS"}:
            if match_url:
                return "Enter Match Room", match_url, True
            return "Preparing Match Room", HUB_URLS["showdown"], False
        if status in {"PENDING_CONFIRMATION", "COMPLETED"} and showdown.settled_at is None:
            own_submission = False
            if own_team is not None:
                own_submission = any(
                    sub.team_id == own_team.id for sub in showdown.result_submissions.all()
                )
            if own_submission:
                return "Waiting for Confirmation", HUB_URLS["showdown"], False
            return "Submit Result", HUB_URLS["showdown"], True
        if status == "DISPUTED":
            return "Under Review", HUB_URLS["showdown"], False
        if status in TERMINAL_CHALLENGE_STATUSES:
            return "View Result", match_url or HUB_URLS["showdown"], False
        return "View Details", HUB_URLS["showdown"], False

    def _bounty_claim_action(
        self,
        status: str,
        match_url: str | None,
        *,
        linked_result: dict[str, Any] | None = None,
    ) -> tuple[str, str | None, bool]:
        linked_result = linked_result or {}
        linked_state = linked_result.get("state")

        if match_url and linked_state == "under_review":
            return "Under Review", match_url, False
        if match_url and linked_state in {"finalized", "viewer_submitted"}:
            return "Proof Under Review", match_url, False
        if match_url and linked_state in {"opponent_submitted", "result_needed"}:
            return "Submit Result in Match Room", match_url, True

        if status == "PENDING":
            if match_url:
                return "Enter Match Room", match_url, True
            return "Waiting for Review", HUB_URLS["bounty"], False
        if status in {"VERIFIED", "PAID"}:
            return "View Result", match_url or HUB_URLS["bounty"], False
        if status == "REJECTED":
            return "Claim Rejected", HUB_URLS["bounty"], False
        if status in TERMINAL_BOUNTY_CLAIM_STATUSES:
            return "View Result", match_url or HUB_URLS["bounty"], False
        return "Under Review", HUB_URLS["bounty"], False

    def _dropzone_reward_summary(self, prize_distribution: dict[str, Any]) -> str | None:
        if not prize_distribution:
            return None
        mode = prize_distribution.get("mode")
        splits = prize_distribution.get("splits") or {}
        if not splits:
            return None
        top_places = ", ".join(f"#{place}: {amount}" for place, amount in list(splits.items())[:3])
        if mode == "PERCENT":
            return f"Placement split: {top_places}%"
        if mode == "FIXED":
            return f"Placement reward: {top_places} DC"
        return "Placement reward configured"
