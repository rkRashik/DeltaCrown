from __future__ import annotations
from datetime import datetime, timedelta
from typing import Iterable, Optional
from urllib.parse import quote

from django.apps import apps
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models import Q, Count, Sum
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from .forms import MyMatchesFilterForm
from .helpers import (
    _safe_model, _safe_qs, _safe_int,
    _build_game_lookup, _ts, _img_url, _avatar_fallback,
)
from .command_center import build_cc_data as _build_cc_data

from django.utils.timesince import timesince as _timesince

logger = __import__("logging").getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# MATCH FILTERING (legacy — kept for /my/matches/ route)
# ═══════════════════════════════════════════════════════════════════════════

def _filter_matches_for_user(user, form: MyMatchesFilterForm):
    if not hasattr(form, "cleaned_data") or form.cleaned_data is None:
        form.is_valid()
    if not hasattr(form, "cleaned_data"):
        form.cleaned_data = {}
    # Tournament Match model is unavailable in vNext
    return None, [], []


@login_required
def my_matches_view(request: HttpRequest) -> HttpResponse:
    form = MyMatchesFilterForm(request.GET or None)
    form.is_valid()
    context = {"form": form, "matches": [], "team_fields": [], "tchoices": []}
    return render(request, "dashboard/my_matches.html", context)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD — COMPREHENSIVE COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════


@login_required
def competitive_hub_view(request: HttpRequest) -> HttpResponse:
    """DeltaCrown competitive hub.

    Pre-fetches everything the page needs to render its first paint:
    identity card, wallet ledger, primary team, captain authority,
    available teams + games for the create modals.  All grids hydrate
    via /api/v1/* after DOMContentLoaded.
    """
    from django.db.models import Q
    from apps.organizations.models import TeamMembership

    user = request.user

    # ── 1. Memberships (authority + non-authority) in one query ──
    memberships = list(
        TeamMembership.objects
        .filter(user=user, status='ACTIVE')
        .select_related('team')
        .order_by('id')
    )
    authority_membership = next(
        (
            m for m in memberships
            if m.team and (
                m.role in ('OWNER', 'MANAGER') or getattr(m, 'is_tournament_captain', False)
            )
        ),
        None,
    )

    if not memberships:
        user_state = 'SOLO'
    elif authority_membership is not None:
        user_state = 'TEAM_CAPTAIN'
    else:
        user_state = 'TEAM_MEMBER'

    # ── 2. Primary team for the hero / identity card ──
    primary = authority_membership or (memberships[0] if memberships else None)
    primary_team = None
    if primary and primary.team:
        t = primary.team
        primary_team = {
            'id': t.pk,
            'name': t.name,
            'slug': getattr(t, 'slug', '') or '',
            'tag': getattr(t, 'tag', '') or '',
            'role': primary.role,
            'is_captain': bool(getattr(primary, 'is_tournament_captain', False)),
        }

    # ── 3. Identity card ──
    profile = getattr(user, 'profile', None)
    display_name = (
        getattr(profile, 'display_name', '') or
        user.get_full_name() or
        user.username
    )
    avatar_url = ''
    try:
        avatar = getattr(profile, 'avatar', None) if profile else None
        if avatar and getattr(avatar, 'url', None):
            avatar_url = avatar.url
    except Exception:
        avatar_url = ''
    identity = {
        'name': primary_team['name'] if primary_team else display_name,
        'display_name': display_name,
        'username': user.username,
        'avatar_url': avatar_url,
        'role_label': (
            f"{primary_team['role'].title()}" if primary_team
            else 'Solo Agent'
        ),
    }

    # ── 4. Wallet snapshot ──
    wallet_snapshot = {
        'cached_balance': 0,
        'pending_balance': 0,
        'escrow_locked_dc': 0,
        'has_wallet': False,
    }
    try:
        from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
        wallet = DeltaCrownWallet.objects.filter(profile=profile).first() if profile else None
        if wallet:
            wallet_snapshot['cached_balance'] = int(wallet.cached_balance or 0)
            wallet_snapshot['pending_balance'] = int(wallet.pending_balance or 0)
            wallet_snapshot['has_wallet'] = True
            locked = (
                DeltaCrownTransaction.objects
                .filter(wallet=wallet, reason=DeltaCrownTransaction.Reason.ESCROW_LOCK)
                .order_by()
                .values_list('amount', flat=True)
            )
            refunded = (
                DeltaCrownTransaction.objects
                .filter(wallet=wallet, reason=DeltaCrownTransaction.Reason.ESCROW_REFUND)
                .order_by()
                .values_list('amount', flat=True)
            )
            wallet_snapshot['escrow_locked_dc'] = abs(sum(locked)) - sum(refunded)
    except Exception:
        pass

    # ── 5. Teams the user has authority on (for create modals) ──
    my_teams = []
    for m in memberships:
        if not m.team:
            continue
        if not (m.role in ('OWNER', 'MANAGER') or getattr(m, 'is_tournament_captain', False)):
            continue
        my_teams.append({
            'id': m.team.pk,
            'name': m.team.name,
            'slug': getattr(m.team, 'slug', '') or '',
            'tag': getattr(m.team, 'tag', '') or '',
            'game_id': m.game_id,
            'role': m.role,
        })

    # ── 6. Active games ──
    games = []
    try:
        Game = _safe_model('games.Game')
        if Game:
            for g in Game.objects.filter(is_active=True).only('id', 'display_name', 'short_code'):
                games.append({
                    'id': g.pk,
                    'name': getattr(g, 'display_name', '') or g.short_code or '',
                    'short_code': g.short_code or '',
                })
    except Exception:
        games = []

    return render(request, "dashboard/competitive_hub.html", {
        "hub_context": {
            "user_state": user_state,
            "can_issue": user_state == 'TEAM_CAPTAIN',
            "identity": identity,
            "primary_team": primary_team,
            "wallet": wallet_snapshot,
            "my_teams": my_teams,
            "games": games,
        },
    })


def _active_team_ids_for_user(user) -> set[int]:
    if not user or not user.is_authenticated:
        return set()
    from apps.organizations.choices import MembershipStatus
    from apps.organizations.models import TeamMembership

    return set(
        TeamMembership.objects.filter(user=user, status=MembershipStatus.ACTIVE)
        .values_list("team_id", flat=True)
    )


def _require_team_access(user, *team_ids: int | None) -> None:
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return
    wanted = {team_id for team_id in team_ids if team_id}
    if not wanted or not (wanted & _active_team_ids_for_user(user)):
        raise Http404("Competitive operation not found.")


def _match_room_url(match) -> str | None:
    if not match or not getattr(match, "tournament_id", None):
        return None
    tournament = getattr(match, "tournament", None)
    if not tournament or not getattr(tournament, "slug", ""):
        return None
    try:
        return reverse("tournaments:match_room", kwargs={"slug": tournament.slug, "match_id": match.id})
    except NoReverseMatch:
        return None


def _safe_match_workflow(match) -> dict:
    lobby_info = getattr(match, "lobby_info", None)
    if not isinstance(lobby_info, dict):
        return {}
    workflow = lobby_info.get("match_lobby_workflow") or lobby_info.get("premium_lobby_workflow")
    return workflow if isinstance(workflow, dict) else {}


def _match_review_state(match, *, viewer_team_id: int | None = None) -> dict:
    if not match:
        return {
            "state": "missing",
            "label": "Match Room Pending",
            "description": "The linked Match Room is still being prepared.",
            "submission_count": 0,
            "open_dispute_count": 0,
            "viewer_has_submission": False,
        }

    workflow = _safe_match_workflow(match)
    result_status = str(workflow.get("result_status") or "").strip().lower() or None
    match_state = str(getattr(match, "state", "") or "").strip().lower()
    submissions = list(getattr(match, "result_submissions", []).all())

    open_dispute_count = 0
    for submission in submissions:
        for dispute in getattr(submission, "disputes", []).all():
            is_open = getattr(dispute, "is_open", None)
            if callable(is_open):
                open_dispute_count += 1 if is_open() else 0
            else:
                open_dispute_count += 1 if str(getattr(dispute, "status", "")).lower() in {"open", "under_review", "escalated"} else 0

    viewer_has_submission = bool(
        viewer_team_id
        and any(getattr(submission, "submitted_by_team_id", None) == viewer_team_id for submission in submissions)
    )

    if open_dispute_count or match_state == "disputed" or result_status in {"mismatch", "tie_pending_review", "admin_tie_pending_review"}:
        state = "under_review"
        label = "Under Review"
        description = "A result or proof issue is being reviewed. Admin-only notes stay private."
    elif match_state == "completed" or result_status in {"verified", "verified_draw", "admin_overridden", "admin_overridden_draw"}:
        state = "finalized"
        label = "Result Confirmed"
        description = "The Match Room result has been confirmed. Settlement status is shown separately."
    elif submissions:
        state = "viewer_submitted" if viewer_has_submission else "opponent_submitted"
        label = "Proof Under Review" if viewer_has_submission else "Result Submitted"
        description = "Proof/result data exists in the Match Room and is waiting for confirmation or review."
    elif match_state == "pending_result" or str(workflow.get("phase") or "").lower() == "results":
        state = "result_needed"
        label = "Submit Result in Match Room"
        description = "The Match Room is ready for result and proof submission."
    else:
        state = "room_ready"
        label = "Match Room Ready"
        description = "Use the linked Match Room for lobby details, proof, result submission, and disputes."

    return {
        "state": state,
        "label": label,
        "description": description,
        "match_state": match_state or None,
        "result_status": result_status,
        "submission_count": len(submissions),
        "open_dispute_count": open_dispute_count,
        "viewer_has_submission": viewer_has_submission,
    }


def _format_dt(value) -> str:
    if not value:
        return ""
    return timezone.localtime(value).strftime("%b %d, %Y %I:%M %p")


def _status_label(value: str | None) -> str:
    return str(value or "").replace("_", " ").title()


def _timeline_item(label: str, state: str = "pending", at=None, note: str = "") -> dict:
    return {
        "label": label,
        "state": state,
        "at": _format_dt(at),
        "note": note,
    }


def _admin_change_url(obj) -> str:
    try:
        return reverse(
            f"admin:{obj._meta.app_label}_{obj._meta.model_name}_change",
            args=[obj.pk],
        )
    except Exception:
        return ""


def _file_url(file_field) -> str:
    try:
        return file_field.url if file_field else ""
    except Exception:
        return ""


def _submission_cards(submissions) -> list[dict]:
    cards = []
    for submission in submissions:
        team_name = getattr(getattr(submission, "team", None), "name", "") or ""
        if not team_name and getattr(submission, "submitted_by_team_id", None):
            team_name = f"Team #{submission.submitted_by_team_id}"
        cards.append({
            "team": team_name or "Submitted team",
            "status": _status_label(getattr(submission, "status", "")),
            "result": _status_label(getattr(submission, "result", "")),
            "score": getattr(submission, "score_details", None) or getattr(submission, "raw_result_payload", None) or {},
            "proof_url": getattr(submission, "evidence_url", "") or getattr(submission, "proof_screenshot_url", ""),
            "submitted_at": _format_dt(getattr(submission, "created_at", None)),
        })
    return cards


@staff_member_required
def competitive_review_workspace_view(request: HttpRequest) -> HttpResponse:
    """Lightweight staff workspace for review-needed competitive operations.

    The page intentionally links to existing Django admin/service-backed
    controls instead of duplicating settlement or dispute actions here.
    """
    groups: list[dict] = []

    def add_group(label: str, accent: str, items: list[dict]) -> None:
        groups.append({
            "label": label,
            "accent": accent,
            "items": items,
            "count": len(items),
        })

    try:
        from apps.competition.models import Challenge

        items = []
        qs = (
            Challenge.objects.filter(status="DISPUTED")
            .select_related("challenger_team", "challenged_team", "game")
            .order_by("-updated_at")[:25]
        )
        for showdown in qs:
            teams = " vs ".join(
                name for name in [
                    getattr(showdown.challenger_team, "name", ""),
                    getattr(showdown.challenged_team, "name", ""),
                ] if name
            )
            items.append({
                "type": "Showdown",
                "title": showdown.title or f"Showdown {showdown.reference_code}",
                "subject": teams or "Team match",
                "status": _status_label(showdown.status),
                "submitted_at": _format_dt(getattr(showdown, "updated_at", None)),
                "evidence": "Result conflict requires staff review.",
                "admin_url": _admin_change_url(showdown),
                "detail_url": reverse("dashboard:competitive_showdown_detail", args=[showdown.pk]),
                "action_label": "Resolve in Admin",
            })
        add_group("Disputed Showdowns", "cyan", items)
    except Exception:
        logger.debug("Review workspace: Showdown query failed", exc_info=True)
        add_group("Disputed Showdowns", "cyan", [])

    try:
        from apps.contracts.models import ContractProofSubmission

        items = []
        qs = (
            ContractProofSubmission.objects.filter(status="PENDING_REVIEW")
            .select_related("enrollment", "enrollment__template", "submitted_by")
            .order_by("-submitted_at")[:50]
        )
        for proof in qs:
            evidence_bits = []
            if proof.proof_url:
                evidence_bits.append("URL")
            if proof.proof_file:
                evidence_bits.append("file")
            items.append({
                "type": "Missions",
                "title": proof.enrollment.template.title,
                "subject": proof.submitted_by.get_username(),
                "status": _status_label(proof.status),
                "submitted_at": _format_dt(proof.submitted_at),
                "evidence": f"Proof submitted: {', '.join(evidence_bits) if evidence_bits else 'notes only'}",
                "proof_url": proof.proof_url,
                "proof_file_url": _file_url(proof.proof_file),
                "admin_url": _admin_change_url(proof),
                "detail_url": reverse("dashboard:competitive_mission_detail", args=[proof.enrollment_id]),
                "action_label": "Review Proof",
            })
        add_group("Pending Mission Proofs", "violet", items)
    except Exception:
        logger.debug("Review workspace: Mission proof query failed", exc_info=True)
        add_group("Pending Mission Proofs", "violet", [])

    try:
        from apps.competition.models import BountyClaim

        items = []
        qs = (
            BountyClaim.objects.filter(status="PENDING")
            .select_related("bounty", "bounty__issuer_team", "claiming_team")
            .order_by("-claimed_at")[:50]
        )
        for claim in qs:
            subject = " vs ".join(
                name for name in [
                    getattr(claim.claiming_team, "name", ""),
                    getattr(claim.bounty.issuer_team, "name", ""),
                ] if name
            )
            items.append({
                "type": "Bounty",
                "title": getattr(claim.bounty, "title", "Bounty claim"),
                "subject": subject or "Claim review",
                "status": _status_label(claim.status),
                "submitted_at": _format_dt(claim.claimed_at),
                "evidence": "Claim evidence submitted." if claim.evidence_url else "Claim waiting for operator verification.",
                "proof_url": claim.evidence_url,
                "admin_url": _admin_change_url(claim),
                "detail_url": reverse("dashboard:competitive_bounty_claim_detail", args=[claim.pk]),
                "action_label": "Verify Claim",
            })
        add_group("Pending Bounty Claims", "neon", items)
    except Exception:
        logger.debug("Review workspace: Bounty claim query failed", exc_info=True)
        add_group("Pending Bounty Claims", "neon", [])

    try:
        from apps.royale.models import RoyaleLobby

        items = []
        qs = (
            RoyaleLobby.objects.filter(status__in=["SCORING"])
            .select_related("game")
            .annotate(_reserved_count=Count(
                "entries",
                filter=Q(entries__status__in=["RESERVED", "CONFIRMED", "SCORED", "NO_SHOW"]),
            ))
            .order_by("-scheduled_at")[:25]
        )
        for lobby in qs:
            reserved_count = getattr(lobby, "_reserved_count", None)
            items.append({
                "type": "Dropzone",
                "title": lobby.title,
                "subject": getattr(lobby.game, "display_name", "") or getattr(lobby.game, "name", ""),
                "status": _status_label(lobby.status),
                "submitted_at": _format_dt(lobby.scheduled_at),
                "evidence": f"{reserved_count if reserved_count is not None else lobby.reserved_count}/{lobby.slot_capacity} slots reserved; scores require operator review.",
                "admin_url": _admin_change_url(lobby),
                "detail_url": reverse("dashboard:competitive_dropzone_lobby_detail", args=[lobby.pk]),
                "action_label": "Open Scoring",
            })
        add_group("Dropzone Scoring", "gold", items)
    except Exception:
        logger.debug("Review workspace: Dropzone query failed", exc_info=True)
        add_group("Dropzone Scoring", "gold", [])

    try:
        from apps.tournaments.models import DisputeRecord

        items = []
        qs = (
            DisputeRecord.objects.filter(status__in=["open", "under_review", "escalated"])
            .select_related(
                "submission",
                "submission__match",
                "submission__match__tournament",
                "opened_by_user",
            )
            .order_by("-opened_at")[:25]
        )
        for dispute in qs:
            match = getattr(dispute.submission, "match", None)
            tournament = getattr(match, "tournament", None)
            detail_url = ""
            if match and tournament and getattr(tournament, "slug", ""):
                detail_url = _match_room_url(match) or ""
            items.append({
                "type": "Tournament",
                "title": getattr(tournament, "name", "") or "Match dispute",
                "subject": dispute.opened_by_user.get_username() if dispute.opened_by_user_id else "Opened dispute",
                "status": _status_label(dispute.status),
                "submitted_at": _format_dt(dispute.opened_at),
                "evidence": dispute.get_reason_code_display(),
                "admin_url": _admin_change_url(dispute),
                "detail_url": detail_url,
                "action_label": "Review Dispute",
            })
        add_group("Tournament Match Disputes", "cyan", items)
    except Exception:
        logger.debug("Review workspace: tournament dispute query failed", exc_info=True)
        add_group("Tournament Match Disputes", "cyan", [])

    total_count = sum(group["count"] for group in groups)
    return render(request, "dashboard/competitive_review.html", {
        "review_groups": groups,
        "total_count": total_count,
    })


@login_required
def competitive_showdown_detail_view(request: HttpRequest, challenge_id) -> HttpResponse:
    from apps.competition.models import Challenge

    showdown = (
        Challenge.objects.select_related("challenger_team", "challenged_team", "game", "match__tournament")
        .prefetch_related("result_submissions__team", "match__result_submissions__disputes")
        .filter(pk=challenge_id)
        .first()
    )
    if not showdown:
        raise Http404("Showdown not found.")
    _require_team_access(request.user, showdown.challenger_team_id, showdown.challenged_team_id)

    team_ids = _active_team_ids_for_user(request.user)
    viewer_team_id = next(
        (team_id for team_id in (showdown.challenger_team_id, showdown.challenged_team_id) if team_id in team_ids),
        None,
    )
    review_state = _match_review_state(showdown.match, viewer_team_id=viewer_team_id)
    match_url = _match_room_url(showdown.match)
    submissions = list(showdown.result_submissions.all())
    if showdown.match:
        submissions.extend(list(showdown.match.result_submissions.all()))

    timeline = [
        _timeline_item("Created", "done", showdown.created_at),
        _timeline_item("Accepted", "done" if showdown.accepted_at else "pending", showdown.accepted_at),
        _timeline_item("Match Room Ready", "done" if match_url else "pending", note="Linked to tournament Match Room." if match_url else "Preparing linked room."),
        _timeline_item(
            "Result Submitted",
            "done" if review_state["submission_count"] or showdown.status in {"PENDING_CONFIRMATION", "COMPLETED", "SETTLED"} else "pending",
            showdown.completed_at,
        ),
        _timeline_item("Under Review", "active" if showdown.status == "DISPUTED" or review_state["state"] == "under_review" else "pending"),
        _timeline_item("Settled", "done" if showdown.settled_at else "pending", showdown.settled_at),
    ]

    return render(request, "dashboard/competitive_detail.html", {
        "detail_type": "Showdown",
        "accent": "cyan",
        "page_title": showdown.title or f"Showdown {showdown.reference_code}",
        "status_label": _status_label(showdown.status),
        "primary_action": {"label": "Enter Match Room", "url": match_url} if match_url else None,
        "hub_url": "/dashboard/competitive/#showdown",
        "summary_cards": [
            {"label": "Game", "value": getattr(showdown.game, "display_name", None) or getattr(showdown.game, "name", "")},
            {"label": "Entry Fee", "value": f"{showdown.entry_fee_dc or 0} DC"},
            {"label": "Reward", "value": f"{getattr(showdown, 'prize_pot_dc', 0) or 0} DC"},
            {"label": "Schedule", "value": _format_dt(showdown.scheduled_at) or "Not scheduled"},
        ],
        "participants": [
            {"label": "Issuing Team", "name": getattr(showdown.challenger_team, "name", "Team")},
            {"label": "Opponent Team", "name": getattr(showdown.challenged_team, "name", "Waiting for opponent")},
        ],
        "proof_state": review_state,
        "timeline": timeline,
        "submissions": _submission_cards(submissions),
    })


@login_required
def competitive_bounty_detail_view(request: HttpRequest, bounty_id) -> HttpResponse:
    from apps.competition.models import Bounty

    bounty = (
        Bounty.objects.select_related("issuer_team", "game")
        .prefetch_related("claims__claiming_team", "claims__match__tournament")
        .filter(pk=bounty_id)
        .first()
    )
    if not bounty:
        raise Http404("Bounty not found.")
    _require_team_access(request.user, bounty.issuer_team_id)

    claim_cards = []
    for claim in bounty.claims.all():
        claim_cards.append({
            "team": getattr(claim.claiming_team, "name", "Claiming team"),
            "status": _status_label(claim.status),
            "result": "Bounty claim",
            "score": {},
            "proof_url": claim.evidence_url or "",
            "submitted_at": _format_dt(claim.claimed_at),
            "detail_url": f"/dashboard/competitive/bounty-claims/{claim.id}/",
        })

    return render(request, "dashboard/competitive_detail.html", {
        "detail_type": "Bounty",
        "accent": "neon",
        "page_title": bounty.title,
        "status_label": _status_label(bounty.status),
        "hub_url": "/dashboard/competitive/#bounty",
        "summary_cards": [
            {"label": "Game", "value": getattr(bounty.game, "display_name", None) or getattr(bounty.game, "name", "")},
            {"label": "Reward", "value": f"{bounty.reward_amount_dc or 0} DC"},
            {"label": "Challenger Entry", "value": f"{bounty.challenger_entry_fee_dc or 0} DC"},
            {"label": "Created", "value": _format_dt(bounty.created_at)},
        ],
        "participants": [
            {"label": "Issuer Team", "name": getattr(bounty.issuer_team, "name", "Team")},
        ],
        "proof_state": {
            "label": "Bounty Board",
            "description": "Claims and proof status appear here without exposing private admin notes.",
            "submission_count": len(claim_cards),
            "open_dispute_count": 0,
        },
        "timeline": [
            _timeline_item("Placed", "done", bounty.created_at),
            _timeline_item("Claimed", "done" if bounty.status in {"CLAIMED", "VERIFIED", "PAID"} else "pending"),
            _timeline_item("Review", "active" if bounty.status in {"ACTIVE", "CLAIMED"} else "done"),
            _timeline_item("Settled", "done" if bounty.status in {"VERIFIED", "PAID"} else "pending"),
        ],
        "submissions": claim_cards,
    })


@login_required
def competitive_mission_detail_view(request: HttpRequest, enrollment_id) -> HttpResponse:
    from apps.contracts.models import ContractEnrollment
    from apps.contracts.services import ContractService

    enrollment = (
        ContractEnrollment.objects.select_related("user", "template", "template__game")
        .prefetch_related("proofs")
        .filter(pk=enrollment_id)
        .first()
    )
    if not enrollment:
        raise Http404("Mission not found.")
    if enrollment.user_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Mission not found.")

    if request.method == "POST":
        try:
            ContractService.submit_proof(
                enrollment_id=enrollment.pk,
                user=request.user,
                proof_url=request.POST.get("proof_url", ""),
                notes=request.POST.get("notes", ""),
                proof_file=request.FILES.get("proof_file"),
            )
            messages.success(request, "Mission proof submitted for review.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("dashboard:competitive_mission_detail", enrollment_id=enrollment.pk)

    template = enrollment.template
    now = timezone.now()
    if enrollment.status == "ACTIVE" and enrollment.deadline_at > now:
        remaining = enrollment.deadline_at - now
        hours = max(0, int(remaining.total_seconds() // 3600))
        minutes = max(0, int((remaining.total_seconds() % 3600) // 60))
        time_remaining = f"{hours}h {minutes}m remaining"
    elif enrollment.status == "ACTIVE":
        time_remaining = "Deadline passed"
    else:
        time_remaining = "Closed"

    progress = enrollment.progress if isinstance(enrollment.progress, dict) else {}
    progress_rows = [{"label": _status_label(key), "value": value} for key, value in progress.items()]
    if not progress_rows:
        progress_rows = [{"label": "Progress", "value": "No tracked progress yet"}]
    proofs = list(enrollment.proofs.all())
    latest_proof = proofs[0] if proofs else None
    can_submit_proof = enrollment.status == "ACTIVE" and not any(
        proof.status == "PENDING_REVIEW" for proof in proofs
    )

    review_label = {
        "ACTIVE": "Mission Active",
        "COMPLETED": "Mission Completed",
        "FAILED": "Mission Failed",
        "EXPIRED": "Expired",
        "CANCELLED": "Closed",
        "VOIDED": "Refunded",
    }.get(enrollment.status, "Mission Status")
    if latest_proof:
        review_label = {
            "PENDING_REVIEW": "Proof Under Review",
            "ACCEPTED": "Proof Accepted",
            "REJECTED": "Proof Rejected",
        }.get(latest_proof.status, review_label)
    review_description = {
        "ACTIVE": "Progress is tracked by the Mission verification workflow. Manual review can be handled by operators if needed.",
        "COMPLETED": "The Mission has been completed and reward handling has finished through the Mission service.",
        "FAILED": "The Mission goal was not completed successfully.",
        "EXPIRED": "The Mission deadline passed before completion.",
        "CANCELLED": "This Mission enrollment was closed.",
        "VOIDED": "This Mission enrollment was voided through operator remediation.",
    }.get(enrollment.status, "Mission state is available.")
    if latest_proof:
        review_description = {
            "PENDING_REVIEW": "Your latest Mission proof is waiting for operator review.",
            "ACCEPTED": "Your latest Mission proof was accepted. Mission completion still requires service-backed resolution.",
            "REJECTED": "Your latest Mission proof was rejected. You can submit updated proof while the Mission is active.",
        }.get(latest_proof.status, review_description)

    timeline = [
        _timeline_item("Enrolled", "done", enrollment.enrolled_at),
        _timeline_item("Active / Progress", "active" if enrollment.status == "ACTIVE" else "done"),
        _timeline_item(
            "Proof Submitted",
            "done" if latest_proof else ("pending" if enrollment.status == "ACTIVE" else "done"),
            getattr(latest_proof, "submitted_at", None),
        ),
        _timeline_item(
            "Review",
            "active" if latest_proof and latest_proof.status == "PENDING_REVIEW" else ("done" if latest_proof else "pending"),
            getattr(latest_proof, "reviewed_at", None),
        ),
        _timeline_item(
            "Closed",
            "done" if enrollment.status in {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED", "VOIDED"} else "pending",
            enrollment.resolved_at,
            _status_label(enrollment.closure_reason) if enrollment.closure_reason else "",
        ),
    ]

    return render(request, "dashboard/competitive_detail.html", {
        "detail_type": "Missions",
        "accent": "violet",
        "page_title": template.title,
        "status_label": _status_label(enrollment.status),
        "hub_url": "/dashboard/competitive/#missions",
        "summary_cards": [
            {"label": "Game", "value": getattr(template.game, "display_name", None) or getattr(template.game, "name", "")},
            {"label": "Entry Fee", "value": f"{template.entry_fee_dc or 0} DC"},
            {"label": "Reward", "value": f"{template.reward_dc or 0} DC"},
            {"label": "Deadline", "value": _format_dt(enrollment.deadline_at)},
        ],
        "participants": [
            {"label": "Player", "name": enrollment.user.get_username()},
            {"label": "Reference", "name": enrollment.reference_code},
        ],
        "proof_state": {
            "label": review_label,
            "description": review_description,
            "submission_count": len(proofs),
            "open_dispute_count": 0,
        },
        "timeline": timeline,
        "mission": {
            "description": template.description,
            "goal_type": template.get_goal_type_display(),
            "goal_spec": template.goal_spec if isinstance(template.goal_spec, dict) else {},
            "progress_rows": progress_rows,
            "time_remaining": time_remaining,
            "closure": _status_label(enrollment.closure_reason),
            "closure_note": enrollment.closure_note,
            "can_submit_proof": can_submit_proof,
            "proofs": [
                {
                    "status": _status_label(proof.status),
                    "proof_url": proof.proof_url,
                    "proof_file_url": _file_url(proof.proof_file),
                    "notes": proof.notes,
                    "submitted_at": _format_dt(proof.submitted_at),
                    "reviewed_at": _format_dt(proof.reviewed_at),
                }
                for proof in proofs[:5]
            ],
        },
        "submissions": [],
    })


@login_required
def competitive_bounty_claim_detail_view(request: HttpRequest, claim_id) -> HttpResponse:
    from apps.competition.models import BountyClaim

    claim = (
        BountyClaim.objects.select_related(
            "bounty",
            "bounty__issuer_team",
            "bounty__game",
            "claiming_team",
            "challenge",
            "challenge__match__tournament",
            "match__tournament",
        )
        .prefetch_related("match__result_submissions__disputes", "challenge__match__result_submissions__disputes")
        .filter(pk=claim_id)
        .first()
    )
    if not claim:
        raise Http404("Bounty claim not found.")
    _require_team_access(request.user, claim.bounty.issuer_team_id, claim.claiming_team_id)

    team_ids = _active_team_ids_for_user(request.user)
    viewer_team_id = claim.claiming_team_id if claim.claiming_team_id in team_ids else claim.bounty.issuer_team_id
    match = claim.match or getattr(claim.challenge, "match", None)
    match_url = _match_room_url(match)
    review_state = _match_review_state(match, viewer_team_id=viewer_team_id)
    submissions = list(match.result_submissions.all()) if match else []
    if claim.evidence_url:
        submissions.append(claim)

    return render(request, "dashboard/competitive_detail.html", {
        "detail_type": "Bounty Claim",
        "accent": "neon",
        "page_title": claim.bounty.title,
        "status_label": _status_label(claim.status),
        "primary_action": {"label": "Enter Match Room", "url": match_url} if match_url else None,
        "hub_url": "/dashboard/competitive/#bounty",
        "summary_cards": [
            {"label": "Game", "value": getattr(claim.bounty.game, "display_name", None) or getattr(claim.bounty.game, "name", "")},
            {"label": "Reward", "value": f"{claim.bounty.reward_amount_dc or 0} DC"},
            {"label": "Claimed", "value": _format_dt(claim.claimed_at)},
            {"label": "Verified", "value": _format_dt(claim.verified_at) or "Pending review"},
        ],
        "participants": [
            {"label": "Issuer Team", "name": getattr(claim.bounty.issuer_team, "name", "Team")},
            {"label": "Claiming Team", "name": getattr(claim.claiming_team, "name", "Team")},
        ],
        "proof_state": review_state,
        "timeline": [
            _timeline_item("Bounty Placed", "done", claim.bounty.created_at),
            _timeline_item("Claim Submitted", "done", claim.claimed_at),
            _timeline_item("Match Room Ready", "done" if match_url else "pending"),
            _timeline_item("Proof Review", "active" if claim.status == "PENDING" else "done"),
            _timeline_item("Settled", "done" if claim.status in {"VERIFIED", "PAID"} else "pending", claim.verified_at),
        ],
        "submissions": _submission_cards(submissions),
    })


@login_required
def competitive_dropzone_lobby_detail_view(request: HttpRequest, lobby_id) -> HttpResponse:
    from apps.royale.models import RoyaleEntry, RoyaleLobby

    lobby = (
        RoyaleLobby.objects.select_related("game", "tournament")
        .prefetch_related("entries__user")
        .filter(pk=lobby_id)
        .first()
    )
    if not lobby:
        raise Http404("Dropzone lobby not found.")

    user_entry = None
    if request.user.is_authenticated:
        user_entry = next((entry for entry in lobby.entries.all() if entry.user_id == request.user.id), None)
    if not lobby.is_public and not user_entry and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Dropzone lobby not found.")

    now = timezone.now()
    credential_entry_statuses = {"RESERVED", "CONFIRMED", "SCORED", "NO_SHOW"}
    credentials_visible = bool(
        user_entry
        and user_entry.status in credential_entry_statuses
        and lobby.scheduled_at <= now
        and (lobby.room_id or lobby.room_password)
    )
    if credentials_visible:
        credential_status = "Room credentials are available for your entry."
    elif not (lobby.room_id or lobby.room_password):
        credential_status = "Room credentials have not been published yet."
    else:
        credential_status = f"Room credentials unlock at {_format_dt(lobby.scheduled_at)} for eligible entrants."

    distribution = lobby.prize_distribution if isinstance(lobby.prize_distribution, dict) else {}
    splits = distribution.get("splits") if isinstance(distribution.get("splits"), dict) else {}
    mode = distribution.get("mode") or ""
    suffix = "%" if mode == "PERCENT" else " DC"
    reward_rules = [f"#{place}: {amount}{suffix}" for place, amount in list(splits.items())[:8]]

    entries = list(lobby.entries.all())
    has_scores = any(entry.placement is not None or entry.kills is not None for entry in entries)
    show_results = has_scores or lobby.status in {"SCORING", "SETTLED"}
    result_entries = []
    if show_results:
        for entry in sorted(entries, key=lambda item: (item.placement is None, item.placement or 9999, -(item.kills or 0))):
            result_entries.append({
                "player": entry.user.get_username(),
                "placement": entry.placement,
                "kills": entry.kills,
                "status": _status_label(entry.status),
                "is_current_user": entry.user_id == request.user.id,
            })

    user_entry_url = f"/dashboard/competitive/dropzone/entries/{user_entry.id}/" if user_entry else ""

    return render(request, "dashboard/competitive_detail.html", {
        "detail_type": "Dropzone Lobby",
        "accent": "gold",
        "page_title": lobby.title,
        "status_label": _status_label(lobby.status),
        "hub_url": "/dashboard/competitive/#dropzone",
        "summary_cards": [
            {"label": "Game", "value": getattr(lobby.game, "display_name", None) or getattr(lobby.game, "name", "")},
            {"label": "Schedule", "value": _format_dt(lobby.scheduled_at)},
            {"label": "Capacity", "value": f"{lobby.reserved_count}/{lobby.slot_capacity} reserved"},
            {"label": "Entry Fee", "value": f"{lobby.entry_fee_dc or 0} DC"},
        ],
        "participants": [
            {"label": "Lobby", "name": lobby.reference_code},
            {"label": "Your Entry", "name": _status_label(user_entry.status) if user_entry else "No entry reserved"},
        ],
        "proof_state": {
            "label": "Scoring Complete" if lobby.status == "SETTLED" else ("Scoring In Progress" if show_results else "Lobby Scheduled"),
            "description": "Dropzone scoring is operator-recorded from placement and kills. Private operator notes are not shown.",
            "submission_count": len(result_entries),
            "open_dispute_count": 0,
        },
        "timeline": [
            _timeline_item("Announced", "done", lobby.created_at),
            _timeline_item("Reservations", "active" if lobby.status in {"ANNOUNCED", "FILLING", "FULL"} else "done"),
            _timeline_item("Room Reveal", "done" if credentials_visible or lobby.scheduled_at <= now else "pending", lobby.scheduled_at, credential_status),
            _timeline_item("Live / Scoring", "active" if lobby.status in {"LIVE", "SCORING"} else ("done" if lobby.status == "SETTLED" else "pending")),
            _timeline_item("Settled", "done" if lobby.status == "SETTLED" else "pending"),
        ],
        "dropzone_lobby": {
            "credential_status": credential_status,
            "credentials_visible": credentials_visible,
            "room_id": lobby.room_id if credentials_visible else "",
            "room_password": lobby.room_password if credentials_visible else "",
            "reward_rules": reward_rules,
            "user_entry_url": user_entry_url,
            "user_entry_status": _status_label(user_entry.status) if user_entry else "",
            "show_results": show_results,
            "result_entries": result_entries,
        },
        "submissions": [],
    })


@login_required
def competitive_dropzone_entry_detail_view(request: HttpRequest, entry_id) -> HttpResponse:
    from apps.royale.models import RoyaleEntry

    entry = (
        RoyaleEntry.objects.select_related("lobby", "lobby__game", "lobby__tournament", "user")
        .filter(pk=entry_id)
        .first()
    )
    if not entry:
        raise Http404("Dropzone entry not found.")
    if entry.user_id != request.user.id and not (request.user.is_staff or request.user.is_superuser):
        raise Http404("Dropzone entry not found.")

    lobby = entry.lobby
    now = timezone.now()
    credentials_visible = bool(
        entry.user_id == request.user.id
        and entry.status in {"RESERVED", "CONFIRMED", "SCORED", "NO_SHOW"}
        and lobby.scheduled_at <= now
        and (lobby.room_id or lobby.room_password)
    )
    credential_status = (
        "Room credentials are available."
        if credentials_visible
        else f"Room credentials unlock at {_format_dt(lobby.scheduled_at)}."
    )
    if not (lobby.room_id or lobby.room_password):
        credential_status = "Room credentials have not been published yet."

    timeline = [
        _timeline_item("Reserved", "done", entry.reserved_at),
        _timeline_item("Room Reveal", "done" if credentials_visible else "pending", lobby.scheduled_at, credential_status),
        _timeline_item("Live / Scoring", "active" if lobby.status in {"LIVE", "SCORING"} else ("done" if lobby.status == "SETTLED" else "pending")),
        _timeline_item("Settled", "done" if lobby.status == "SETTLED" or entry.resolved_at else "pending", entry.resolved_at),
    ]

    rules_summary = []
    distribution = lobby.prize_distribution or {}
    splits = distribution.get("splits") if isinstance(distribution, dict) else {}
    mode = distribution.get("mode") if isinstance(distribution, dict) else ""
    if splits:
        suffix = "%" if mode == "PERCENT" else " DC"
        rules_summary = [f"#{place}: {amount}{suffix}" for place, amount in list(splits.items())[:6]]

    return render(request, "dashboard/competitive_detail.html", {
        "detail_type": "Dropzone",
        "accent": "gold",
        "page_title": lobby.title,
        "status_label": _status_label(entry.status),
        "hub_url": "/dashboard/competitive/#dropzone",
        "summary_cards": [
            {"label": "Game", "value": getattr(lobby.game, "display_name", None) or getattr(lobby.game, "name", "")},
            {"label": "Schedule", "value": _format_dt(lobby.scheduled_at)},
            {"label": "Slots", "value": f"{lobby.reserved_count}/{lobby.slot_capacity} reserved"},
            {"label": "Entry Fee", "value": f"{lobby.entry_fee_dc or 0} DC"},
        ],
        "participants": [
            {"label": "Entry", "name": request.user.get_username()},
            {"label": "Lobby", "name": lobby.reference_code},
        ],
        "proof_state": {
            "label": "Dropzone Entry",
            "description": "Placement and kill scoring are recorded by operators after the lobby is played.",
            "submission_count": 1 if entry.placement is not None else 0,
            "open_dispute_count": 0,
        },
        "timeline": timeline,
        "dropzone": {
            "placement": entry.placement,
            "kills": entry.kills,
            "entry_status": _status_label(entry.status),
            "lobby_status": _status_label(lobby.status),
            "closure": _status_label(entry.closure_reason or lobby.closure_reason),
            "credential_status": credential_status,
            "credentials_visible": credentials_visible,
            "room_id": lobby.room_id if credentials_visible else "",
            "room_password": lobby.room_password if credentials_visible else "",
            "rules_summary": rules_summary,
        },
        "submissions": [],
    })


@login_required
def dashboard_index(request: HttpRequest) -> HttpResponse:
    """
    Comprehensive Dashboard — the user's command center.

    Pulls data from every major subsystem with graceful degradation:
    teams, invites, tournaments, matches, leaderboards, economy,
    notifications, profile, achievements.
    """
    from apps.organizations.models import Team
    from apps.organizations.models.membership import TeamMembership
    from apps.organizations.models.team_invite import TeamInvite
    from apps.organizations.choices import MembershipStatus
    from apps.notifications.models import Notification

    user = request.user
    now = timezone.now()
    game_map = _build_game_lookup()

    # Detailed game lookup with icons/colors
    game_detail_map = {}
    try:
        Game = _safe_model("games.Game")
        if Game:
            for g in Game.objects.all().only("id", "name", "icon", "logo", "primary_color", "short_code"):
                game_detail_map[g.id] = {
                    "name": g.name,
                    "icon": _img_url(g, "icon"),
                    "logo": _img_url(g, "logo"),
                    "color": getattr(g, "primary_color", "#6366F1") or "#6366F1",
                    "code": getattr(g, "short_code", "") or "",
                }
    except Exception:
        pass

    # ── 1. USER PROFILE ─────────────────────────────────────────────────
    profile = None
    profile_data = {}
    try:
        Profile = _safe_model("user_profile.UserProfile")
        if Profile:
            profile = Profile.objects.filter(user=user).first()
        if profile:
            avatar = _img_url(profile, "avatar")
            banner = _img_url(profile, "banner")
            profile_data = {
                "display_name": getattr(profile, "display_name", "") or user.get_full_name() or user.username,
                "avatar_url": avatar,
                "banner_url": banner,
                "slug": getattr(profile, "slug", user.username),
                "lft_status": getattr(profile, "lft_status", None) or getattr(profile, "LFTStatus", None),
                "kyc_status": getattr(profile, "kyc_status", ""),
                "reputation_score": getattr(profile, "reputation_score", 100),
                "level": getattr(profile, "level", 1),
                "xp": getattr(profile, "xp", 0),
            }
        else:
            profile_data = {
                "display_name": user.get_full_name() or user.username,
                "avatar_url": None,
                "slug": user.username,
                "lft_status": None,
                "kyc_status": "",
            }
    except Exception:
        profile_data = {
            "display_name": user.get_full_name() or user.username,
            "avatar_url": None,
            "slug": user.username,
            "lft_status": None,
            "kyc_status": "",
        }

    # ── 2. MY TEAMS ─────────────────────────────────────────────────────
    my_teams = []
    try:
        memberships = (
            TeamMembership.objects.filter(user=user, status=MembershipStatus.ACTIVE)
            .select_related("team", "team__organization")
            .order_by("-joined_at")[:8]
        )
        for m in memberships:
            t = m.team
            member_ct = _safe_int(
                lambda: TeamMembership.objects.filter(team=t, status=MembershipStatus.ACTIVE).count()
            )
            # Pending join request count for admins/owners
            jr_count = 0
            if m.role in ('OWNER', 'MANAGER'):
                try:
                    from apps.organizations.models.join_request import TeamJoinRequest
                    jr_count = TeamJoinRequest.objects.filter(
                        team=t,
                        status__in=['PENDING', 'TRYOUT_SCHEDULED', 'TRYOUT_COMPLETED', 'OFFER_SENT'],
                    ).count()
                except Exception:
                    pass
            # Organization association
            org_obj = getattr(t, 'organization', None)
            team_org = None
            if org_obj:
                team_org = {
                    "name": org_obj.name,
                    "slug": getattr(org_obj, "slug", ""),
                    "logo": _img_url(org_obj),
                    "verified": getattr(org_obj, "is_verified", False),
                }
            gd = game_detail_map.get(t.game_id, {})
            my_teams.append({
                "id": t.id, "name": t.name, "slug": t.slug,
                "logo_url": _img_url(t),
                "role": m.role,
                "game_name": game_map.get(t.game_id, ""),
                "game_icon": gd.get("icon", ""),
                "game_color": gd.get("color", "#6366F1"),
                "member_count": member_ct,
                "tag": getattr(t, "tag", "") or "",
                "status": getattr(t, "status", ""),
                "pending_jr_count": jr_count,
                "org": team_org,
            })
    except Exception:
        logger.debug("Dashboard: teams query failed", exc_info=True)

    # Batch-fetch roster data for team cards
    try:
        if my_teams:
            team_id_list = [t["id"] for t in my_teams]
            roster_qs = (
                TeamMembership.objects.filter(
                    team_id__in=team_id_list,
                    status=MembershipStatus.ACTIVE,
                )
                .select_related("user")
                .order_by("team_id", "joined_at")
            )

            # Batch-load user avatars
            member_user_ids = [rm.user_id for rm in roster_qs]
            Profile = _safe_model("user_profile.UserProfile")
            avatar_map = {}
            if Profile and member_user_ids:
                for p in Profile.objects.filter(user_id__in=member_user_ids).only("user_id", "avatar"):
                    avatar_map[p.user_id] = _img_url(p, "avatar")

            roster_data = {}
            for rm in roster_qs:
                lst = roster_data.setdefault(rm.team_id, [])
                if len(lst) < 5:
                    uname = rm.user.username
                    initials = ''.join([w[0] for w in uname.split()[:2]]).upper() or 'U'
                    avatar = avatar_map.get(rm.user_id) or (
                        'https://ui-avatars.com/api/?name=%s&background=222&color=fff&size=64' % initials
                    )
                    lst.append({
                        "name": "You" if rm.user_id == user.id else uname,
                        "isCaptain": rm.role in ("OWNER", "CAPTAIN"),
                        "avatar": avatar,
                        "role": rm.role,
                    })
            for t in my_teams:
                t["roster"] = roster_data.get(t["id"], [])
    except Exception:
        logger.debug("Dashboard: roster query failed", exc_info=True)

    # ── 3. PENDING INVITES ──────────────────────────────────────────────
    pending_invites = []
    try:
        invites = (
            TeamInvite.objects.filter(
                invited_user=user, status="PENDING", expires_at__gt=now,
            )
            .select_related("team", "inviter")
            .order_by("-created_at")[:5]
        )
        for inv in invites:
            pending_invites.append({
                "id": inv.id,
                "team_name": inv.team.name,
                "team_slug": inv.team.slug,
                "team_logo": _img_url(inv.team),
                "role": inv.role,
                "inviter": inv.inviter.username if inv.inviter else "Unknown",
                "created_at": inv.created_at,
                "expires_at": inv.expires_at,
            })
    except Exception:
        logger.debug("Dashboard: invites query failed", exc_info=True)

    # ── 4. RECENT MATCHES (competition.MatchReport) ─────────────────────
    recent_matches = []
    try:
        MatchReport = _safe_model("competition.MatchReport")
        if MatchReport:
            team_ids = [t["id"] for t in my_teams]
            if team_ids:
                reports = (
                    MatchReport.objects.filter(
                        Q(team1_id__in=team_ids) | Q(team2_id__in=team_ids)
                    )
                    .select_related("team1", "team2")
                    .order_by("-created_at")[:6]
                )
                for r in reports:
                    t1_name = getattr(r.team1, "name", "TBD") if r.team1 else "TBD"
                    t2_name = getattr(r.team2, "name", "TBD") if r.team2 else "TBD"
                    recent_matches.append({
                        "id": r.id,
                        "team1_name": t1_name,
                        "team2_name": t2_name,
                        "result": getattr(r, "result", ""),
                        "match_type": getattr(r, "match_type", ""),
                        "game_name": game_map.get(getattr(r, "game_id", None), ""),
                        "game_icon": game_detail_map.get(getattr(r, "game_id", None), {}).get("icon", ""),
                        "created_at": r.created_at,
                        "score_team1": getattr(r, "score_team1", None),
                        "score_team2": getattr(r, "score_team2", None),
                    })
    except Exception:
        logger.debug("Dashboard: matches query failed", exc_info=True)

    # ── 5. MATCH STATS (W / L / D) ──────────────────────────────────────
    match_stats = {"wins": 0, "losses": 0, "draws": 0, "total": 0, "win_rate": 0}
    try:
        MatchReport = _safe_model("competition.MatchReport")
        if MatchReport and my_teams:
            team_ids = [t["id"] for t in my_teams]
            all_reports = MatchReport.objects.filter(
                Q(team1_id__in=team_ids) | Q(team2_id__in=team_ids)
            )
            for r in all_reports:
                result = str(getattr(r, "result", "")).upper()
                is_team1 = r.team1_id in team_ids
                if result == "WIN":
                    if is_team1:
                        match_stats["wins"] += 1
                    else:
                        match_stats["losses"] += 1
                elif result == "LOSS":
                    if is_team1:
                        match_stats["losses"] += 1
                    else:
                        match_stats["wins"] += 1
                elif result == "DRAW":
                    match_stats["draws"] += 1
                match_stats["total"] += 1
            if match_stats["total"] > 0:
                match_stats["win_rate"] = round(
                    match_stats["wins"] / match_stats["total"] * 100
                )
    except Exception:
        logger.debug("Dashboard: match stats query failed", exc_info=True)

    # ── 6. TOURNAMENTS ───────────────────────────────────────────────────
    active_tournaments = []
    tournament_count = 0
    next_match_info = None  # User's upcoming match with room link
    imminent_lobby_alert = None
    try:
        Registration = _safe_model("tournaments.Registration")
        Tournament = _safe_model("tournaments.Tournament")
        Match = _safe_model("tournaments.Match")
        TournamentStaffAssignment = _safe_model("tournaments.TournamentStaffAssignment")
        if Registration and Tournament:
            excluded_statuses = ["cancelled", "rejected", "draft"]
            reg_filter = Q(is_deleted=False)
            reg_filter &= ~Q(status__in=excluded_statuses)
            reg_filter &= (Q(user=user) | Q(team_id__in=[t["id"] for t in my_teams])) if my_teams else Q(user=user)

            regs = list(
                Registration.objects.filter(reg_filter)
                .select_related("tournament", "tournament__game")
                .order_by("-created_at")[:8]
            )
            tournament_ids = [r.tournament_id for r in regs if getattr(r, "tournament_id", None)]
            vnext_staff_tournament_ids = set()

            if tournament_ids and TournamentStaffAssignment:
                try:
                    vnext_staff_tournament_ids = set(
                        TournamentStaffAssignment.objects.filter(
                            user=user,
                            is_active=True,
                            tournament_id__in=tournament_ids,
                        ).values_list("tournament_id", flat=True)
                    )
                except Exception:
                    vnext_staff_tournament_ids = set()

            for reg in regs:
                t = reg.tournament
                if t:
                    can_manage = bool(
                        user.is_staff
                        or getattr(t, "organizer_id", None) == user.id
                        or t.id in vnext_staff_tournament_ids
                    )
                    _eff = t.get_effective_status() if hasattr(t, 'get_effective_status') else getattr(t, "status", "")
                    _cur_stage = t.get_current_stage() if hasattr(t, 'get_current_stage') else ''
                    active_tournaments.append({
                        "id": t.id,
                        "name": t.name,
                        "slug": getattr(t, "slug", ""),
                        "status": _eff,
                        "current_stage": _cur_stage or '',
                        "game_name": t.game.display_name if t.game else game_map.get(getattr(t, "game_id", None), ""),
                        "game_icon": _img_url(t.game, "icon") if t.game else None,
                        "banner_url": _img_url(t, "banner_image"),
                        "thumbnail_url": _img_url(t, "thumbnail_image"),
                        "scheduled_at": getattr(t, "scheduled_at", None),
                        "tournament_start": getattr(t, "tournament_start", None),
                        "prize_pool": getattr(t, "prize_pool", None),
                        "format": getattr(t, "format", ""),
                        "reg_status": getattr(reg, "status", ""),
                        "is_live": _eff == "live",
                        "platform": getattr(t, "platform", ""),
                        "max_participants": getattr(t, "max_participants", 0),
                        "can_manage": can_manage,
                    })
            tournament_count = (
                Registration.objects.filter(reg_filter)
                .values("tournament").distinct().count()
            )

        # Find user's next upcoming match across all tournaments
        if Match:
            upcoming_states = ["scheduled", "check_in", "ready", "live"]
            user_team_ids = [t["id"] for t in my_teams]
            q_participant = Q(participant1_id=user.id) | Q(participant2_id=user.id)
            if user_team_ids:
                q_participant |= Q(participant1_id__in=user_team_ids) | Q(participant2_id__in=user_team_ids)
            # Participant IDs may store Registration.id — include those too
            try:
                user_reg_ids = list(
                    Registration.objects.filter(
                        user=user, is_deleted=False,
                    ).values_list("id", flat=True)
                )
                if user_reg_ids:
                    q_participant |= Q(participant1_id__in=user_reg_ids) | Q(participant2_id__in=user_reg_ids)
            except Exception:
                user_reg_ids = []
            nm = (
                Match.objects.filter(q_participant, state__in=upcoming_states, is_deleted=False)
                .select_related("tournament")
                .order_by("scheduled_time", "round_number", "match_number")
                .first()
            )
            if nm:
                from apps.tournaments.services.match_lobby_service import resolve_lobby_state
                nm_lobby = resolve_lobby_state(nm, now=now)
                nm_lobby_info = nm.lobby_info if isinstance(nm.lobby_info, dict) else {}
                nm_lobby_code = (nm_lobby_info.get('lobby_code') or nm_lobby_info.get('code') or '').strip()
                all_participant_ids = set([user.id] + user_team_ids + user_reg_ids)
                next_match_info = {
                    "match_id": nm.id,
                    "tournament_name": nm.tournament.name if nm.tournament else "",
                    "tournament_slug": nm.tournament.slug if nm.tournament else "",
                    "opponent_name": nm.participant2_name if nm.participant1_id in all_participant_ids else nm.participant1_name,
                    "scheduled_time": nm.scheduled_time,
                    "state": nm.state,
                    "is_live": nm.state == "live",
                    "match_room_url": '/tournaments/%s/matches/%s/room/' % (nm.tournament.slug, nm.id) if nm.tournament else '',
                    "lobby_code": nm_lobby_code,
                    "lobby_status": nm_lobby['state'],
                    "lobby_open": nm_lobby['is_open'],
                    "lobby_state": nm_lobby['state'],
                    "game_icon": _img_url(nm.tournament.game, "icon") if nm.tournament and nm.tournament.game else None,
                }

            window_start = now - timedelta(minutes=5)
            window_end = now + timedelta(minutes=60)
            window_matches = (
                Match.objects.filter(
                    q_participant,
                    state__in=["scheduled", "check_in", "ready", "live"],
                    is_deleted=False,
                    scheduled_time__gte=window_start,
                    scheduled_time__lte=window_end,
                )
                .select_related("tournament", "tournament__game")
                .order_by("scheduled_time", "round_number", "match_number")[:8]
            )
            for wm in window_matches:
                from apps.tournaments.services.match_lobby_service import resolve_lobby_state
                wm_lobby = resolve_lobby_state(wm, now=now)
                lobby_info = wm.lobby_info if isinstance(wm.lobby_info, dict) else {}
                lobby_code = (lobby_info.get('lobby_code') or lobby_info.get('code') or '').strip()

                starts_in_minutes = max(int((wm.scheduled_time - now).total_seconds() // 60), 0)

                all_participant_ids = set([user.id] + user_team_ids + user_reg_ids)
                imminent_lobby_alert = {
                    "match_id": wm.id,
                    "tournament_name": wm.tournament.name if wm.tournament else "",
                    "tournament_slug": wm.tournament.slug if wm.tournament else "",
                    "opponent_name": wm.participant2_name if wm.participant1_id in all_participant_ids else wm.participant1_name,
                    "scheduled_time": wm.scheduled_time,
                    "starts_in_minutes": starts_in_minutes,
                    "lobby_code": lobby_code,
                    "lobby_status": wm_lobby['state'],
                    "lobby_open": wm_lobby['is_open'],
                    "lobby_state": wm_lobby['state'],
                    "match_room_url": '/tournaments/%s/matches/%s/room/' % (wm.tournament.slug, wm.id) if wm.tournament else '',
                    "game_icon": _img_url(wm.tournament.game, "icon") if wm.tournament and wm.tournament.game else None,
                    "match_state": wm.state,
                }
                break
    except Exception:
        logger.debug("Dashboard: tournaments query failed", exc_info=True)

    # ── 7. LEADERBOARD POSITION ──────────────────────────────────────────
    leaderboard_data = []
    try:
        LeaderboardEntry = _safe_model("leaderboards.LeaderboardEntry")
        if LeaderboardEntry:
            entries = (
                LeaderboardEntry.objects.filter(player=user)
                .order_by("rank")[:3]
            )
            for e in entries:
                leaderboard_data.append({
                    "rank": e.rank,
                    "points": getattr(e, "points", 0),
                    "leaderboard_type": getattr(e, "leaderboard_type", ""),
                    "game_name": game_map.get(getattr(e, "game_id", None), ""),
                    "wins": getattr(e, "wins", 0),
                    "losses": getattr(e, "losses", 0),
                    "win_rate": getattr(e, "win_rate", 0),
                })
    except Exception:
        logger.debug("Dashboard: leaderboard query failed", exc_info=True)

    # ── SECTIONS 8–19: Secondary data (wallet, badges, social, etc.) ────
    from .secondary_data import load_secondary_data
    secondary = load_secondary_data(
        user,
        profile=profile,
        my_teams=my_teams,
        game_detail_map=game_detail_map,
    )

    # ── ASSEMBLE CONTEXT ─────────────────────────────────────────────────
    context = {
        # Profile
        "profile": profile_data,
        # Teams
        "my_teams": my_teams,
        "team_count": len(my_teams),
        # Invites
        "pending_invites": pending_invites,
        "invite_count": len(pending_invites),
        # Matches
        "recent_matches": recent_matches,
        "match_stats": match_stats,
        # Tournaments
        "active_tournaments": active_tournaments,
        "tournament_count": tournament_count,
        "next_match_info": next_match_info,
        "imminent_lobby_alert": imminent_lobby_alert,
        # Leaderboard
        "leaderboard_data": leaderboard_data,
        # Games map (for template use)
        "games": list(game_map.values()),
    }
    # Merge secondary data (wallet, badges, notifications, social, etc.)
    context.update(secondary)

    # ── BUILD COMMAND CENTER DATA ────────────────────────────────────────
    context["cc_data"] = _build_cc_data(context, user, now)

    return render(request, "dashboard/index.html", context)
