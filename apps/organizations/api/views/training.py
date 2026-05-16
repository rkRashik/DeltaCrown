"""
Team HQ training API endpoints.

These endpoints power non-reward team operations: Scrims, Tryouts, Practice,
and VOD Reviews. They do not interact with DeltaCoin, escrow, or settlement.
"""

import json
from datetime import datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.organizations.choices import TeamStatus
from apps.organizations.models import Team, TeamMembership
from apps.organizations.models.join_request import TeamJoinRequest
from apps.organizations.models.training import (
    PracticeSession,
    ScrimBooking,
    ScrimRequest,
    TryoutApplication,
    TryoutSession,
    VodReview,
)
from apps.organizations.services.training_service import (
    TeamTrainingService,
    match_room_url,
)
from apps.organizations.api.views.team_manage import api_login_required


@api_login_required
@require_http_methods(["GET"])
def training_overview(request, slug):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    if not TeamTrainingService.user_can_view_team_ops(request.user, team):
        return _error("You are not allowed to view this team's training area.", 403)
    can_manage = TeamTrainingService.has_team_ops_authority(request.user, team)

    game = TeamTrainingService.default_game_for_team(team)
    scrims = ScrimRequest.objects.filter(requesting_team=team).select_related(
        "requesting_team", "accepted_team", "game", "booking__match", "booking__match__tournament"
    )[:12]
    inbound_scrims = ScrimRequest.objects.filter(status=ScrimRequest.Status.OPEN)
    if game:
        inbound_scrims = inbound_scrims.filter(game_id=game.pk)
    else:
        inbound_scrims = inbound_scrims.none()
    inbound_scrims = inbound_scrims.exclude(requesting_team=team).select_related("requesting_team", "game")[:12]
    bookings = ScrimBooking.objects.filter(
        models_team_booking_filter(team)
    ).select_related("requesting_team", "accepted_team", "scrim_request", "match", "match__tournament")[:12]
    if can_manage:
        tryouts = TryoutApplication.objects.filter(team=team).select_related(
            "applicant", "reviewed_by", "game", "join_request"
        )[:16]
        tryout_sessions = TryoutSession.objects.filter(team=team).select_related(
            "application", "applicant", "match", "match__tournament"
        )[:12]
    else:
        tryouts = TryoutApplication.objects.none()
        tryout_sessions = TryoutSession.objects.none()
    practices = PracticeSession.objects.filter(team=team).select_related("game")[:12]
    vods = VodReview.objects.filter(team=team).select_related(
        "reviewer", "linked_match", "linked_match__tournament"
    )[:12]

    return JsonResponse({
        "success": True,
        "team": {"id": team.pk, "name": team.name, "slug": team.slug},
        "permissions": {
            "can_manage_training": can_manage,
        },
        "scrims": [_scrim_request_payload(item, include_private=can_manage) for item in scrims],
        "open_scrims": [_scrim_request_payload(item, include_private=False) for item in inbound_scrims],
        "scrim_bookings": [_scrim_booking_payload(item, include_private=can_manage) for item in bookings],
        "tryout_applications": [_tryout_application_payload(item, include_private=can_manage) for item in tryouts],
        "tryout_sessions": [_tryout_session_payload(item, include_private=can_manage) for item in tryout_sessions],
        "practice_sessions": [_practice_payload(item, include_private=can_manage) for item in practices],
        "vod_reviews": [_vod_payload(item, include_private=can_manage) for item in vods],
        "stats": {
            "open_scrims": ScrimRequest.objects.filter(requesting_team=team, status=ScrimRequest.Status.OPEN).count(),
            "pending_tryouts": TryoutApplication.objects.filter(
                team=team,
                status__in=[
                    TryoutApplication.Status.PENDING,
                    TryoutApplication.Status.REVIEWING,
                    TryoutApplication.Status.INVITED,
                    TryoutApplication.Status.SCHEDULED,
                    TryoutApplication.Status.OBSERVATION,
                ],
            ).count(),
            "upcoming_practice": PracticeSession.objects.filter(
                team=team,
                status=PracticeSession.Status.SCHEDULED,
                scheduled_at__gte=timezone.now(),
            ).count(),
            "open_vods": VodReview.objects.filter(team=team, status=VodReview.Status.OPEN).count(),
        },
    })


@api_login_required
@require_http_methods(["GET", "POST"])
def scrim_requests(request, slug):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    if request.method == "GET":
        if not TeamTrainingService.user_can_view_team_ops(request.user, team):
            return _error("You are not allowed to view scrims for this team.", 403)
        can_manage = TeamTrainingService.has_team_ops_authority(request.user, team)
        items = ScrimRequest.objects.filter(requesting_team=team).select_related(
            "requesting_team", "accepted_team", "game", "booking__match", "booking__match__tournament"
        )[:30]
        return JsonResponse({"success": True, "scrims": [_scrim_request_payload(item, include_private=can_manage) for item in items]})

    try:
        data = _json_body(request)
        scrim = TeamTrainingService.create_scrim_request(
            team=team,
            actor=request.user,
            scheduled_at=_parse_scheduled_at(data),
            title=data.get("title") or "",
            format=(data.get("format") or "BO3").upper(),
            skill_level=data.get("skill_level") or data.get("rank_preference") or "",
            server_region=data.get("server_region") or data.get("region") or "",
            visibility=(data.get("visibility") or "PUBLIC").upper(),
            notes=data.get("notes") or "",
        )
        return JsonResponse({"success": True, "scrim": _scrim_request_payload(scrim), "message": "Scrim request posted."})
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


@api_login_required
@require_http_methods(["POST"])
def accept_scrim(request, slug, scrim_id):
    accepting_team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    scrim = get_object_or_404(ScrimRequest, pk=scrim_id)
    try:
        data = _json_body(request)
        booking = TeamTrainingService.accept_scrim_request(
            scrim_request=scrim,
            accepting_team=accepting_team,
            actor=request.user,
            room_details=data.get("room_details") or "",
        )
        return JsonResponse({
            "success": True,
            "booking": _scrim_booking_payload(booking),
            "message": "Scrim booking created.",
        })
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


@api_login_required
@require_http_methods(["GET", "POST"])
def tryout_applications(request, slug):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)

    if request.method == "GET":
        if not TeamTrainingService.has_team_ops_authority(request.user, team):
            return _error("You are not allowed to view tryouts for this team.", 403)
        qs = TryoutApplication.objects.filter(team=team).select_related("applicant", "reviewed_by", "game", "join_request")[:40]
        return JsonResponse({"success": True, "tryouts": [_tryout_application_payload(item, include_private=True) for item in qs]})

    try:
        data = _json_body(request)
        game = _resolve_tryout_game(team, data)
        invite_user_id = data.get("applicant_user_id") or data.get("user_id")
        if invite_user_id:
            TeamTrainingService.verify_team_ops_authority(request.user, team, "invite players to tryouts")
            from django.contrib.auth import get_user_model

            applicant = get_object_or_404(get_user_model(), pk=invite_user_id)
            app = TeamTrainingService.invite_for_tryout(
                team=team,
                applicant=applicant,
                actor=request.user,
                preferred_role=data.get("preferred_role") or "",
                notes=data.get("notes") or "",
                game=game,
            )
            return JsonResponse({"success": True, "tryout": _tryout_application_payload(app), "message": "Tryout invite created."})

        active_join_statuses = [
            TeamJoinRequest.Status.PENDING,
            TeamJoinRequest.Status.TRYOUT_SCHEDULED,
            TeamJoinRequest.Status.TRYOUT_COMPLETED,
            TeamJoinRequest.Status.OFFER_SENT,
        ]
        if TeamJoinRequest.objects.filter(team=team, user=request.user, status__in=active_join_statuses).exists():
            return _error(
                "You already have an active join request for this team. Track it from the team page or wait for team review.",
                400,
            )

        app = TeamTrainingService.apply_for_tryout(
            team=team,
            applicant=request.user,
            ign=data.get("ign") or "",
            preferred_role=data.get("preferred_role") or data.get("role") or "",
            rank_tier=data.get("rank_tier") or data.get("rank") or "",
            availability=data.get("availability") or "",
            profile_links=data.get("profile_links") or data.get("links") or [],
            notes=data.get("notes") or data.get("message") or "",
            game=game,
        )
        return JsonResponse({"success": True, "tryout": _tryout_application_payload(app), "message": "Tryout application submitted."})
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


@api_login_required
@require_http_methods(["GET"])
def tryout_status(request, slug):
    """Return applicant-safe status for the current user's join/tryout state."""
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    tryout_statuses = [
        TryoutApplication.Status.PENDING,
        TryoutApplication.Status.REVIEWING,
        TryoutApplication.Status.INVITED,
        TryoutApplication.Status.SCHEDULED,
        TryoutApplication.Status.OBSERVATION,
        TryoutApplication.Status.ACCEPTED,
        TryoutApplication.Status.REJECTED,
    ]
    join_statuses = [
        TeamJoinRequest.Status.PENDING,
        TeamJoinRequest.Status.TRYOUT_SCHEDULED,
        TeamJoinRequest.Status.TRYOUT_COMPLETED,
        TeamJoinRequest.Status.OFFER_SENT,
        TeamJoinRequest.Status.ACCEPTED,
        TeamJoinRequest.Status.DECLINED,
    ]
    tryout = (
        TryoutApplication.objects.filter(team=team, applicant=request.user, status__in=tryout_statuses)
        .select_related("applicant", "game", "join_request")
        .prefetch_related("sessions")
        .order_by("-created_at")
        .first()
    )
    join_request = (
        TeamJoinRequest.objects.filter(team=team, user=request.user, status__in=join_statuses)
        .order_by("-created_at")
        .first()
    )
    session = next(iter(tryout.sessions.all()), None) if tryout else None
    return JsonResponse({
        "success": True,
        "tryout": _tryout_application_payload(tryout, include_private=False) if tryout else None,
        "tryout_session": _tryout_session_payload(session, include_private=False) if session else None,
        "join_request": _join_request_status_payload(join_request) if join_request else None,
        "applicant_status": _applicant_status_payload(tryout, join_request, session),
    })


@api_login_required
@require_http_methods(["GET"])
def my_team_applications(request):
    """Return the current user's team applications, tryouts, and offers."""
    session_qs = TryoutSession.objects.order_by("-scheduled_at", "-created_at")
    tryouts = list(
        TryoutApplication.objects.filter(applicant=request.user)
        .select_related("team", "team__organization", "game", "join_request", "join_request__team")
        .prefetch_related(Prefetch("sessions", queryset=session_qs))
        .order_by("-created_at")[:80]
    )
    linked_join_request_ids = {
        item.join_request_id for item in tryouts if item.join_request_id
    }
    join_requests = list(
        TeamJoinRequest.objects.filter(user=request.user)
        .exclude(pk__in=linked_join_request_ids)
        .select_related("team", "team__organization")
        .prefetch_related(
            Prefetch(
                "tryout_applications",
                queryset=TryoutApplication.objects.select_related("game").prefetch_related(
                    Prefetch("sessions", queryset=session_qs)
                ),
            )
        )
        .order_by("-created_at")[:80]
    )

    items = [_applicant_history_tryout_payload(item) for item in tryouts]
    items.extend(_applicant_history_join_payload(item) for item in join_requests)
    items.sort(key=lambda item: item.get("submitted_at") or "", reverse=True)

    return JsonResponse({
        "success": True,
        "count": len(items),
        "results": items,
    })


@api_login_required
@require_http_methods(["POST"])
def review_tryout(request, slug, application_id):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    application = get_object_or_404(TryoutApplication, pk=application_id, team=team)
    try:
        data = _json_body(request)
        status = (data.get("status") or data.get("action") or "").upper()
        status_aliases = {
            "ACCEPT": TryoutApplication.Status.ACCEPTED,
            "REJECT": TryoutApplication.Status.REJECTED,
            "OBSERVE": TryoutApplication.Status.OBSERVATION,
            "REVIEW": TryoutApplication.Status.REVIEWING,
        }
        app = TeamTrainingService.review_tryout_application(
            application=application,
            actor=request.user,
            status=status_aliases.get(status, status),
            review_notes=data.get("review_notes") or data.get("notes") or "",
        )
        return JsonResponse({"success": True, "tryout": _tryout_application_payload(app), "message": "Tryout updated."})
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


@api_login_required
@require_http_methods(["POST"])
def schedule_tryout_session(request, slug, application_id):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    application = get_object_or_404(TryoutApplication, pk=application_id, team=team)
    try:
        data = _json_body(request)
        session = TeamTrainingService.schedule_tryout_session(
            application=application,
            actor=request.user,
            scheduled_at=_parse_scheduled_at(data),
            format=data.get("format") or "",
            room_details=data.get("room_details") or "",
        )
        return JsonResponse({"success": True, "session": _tryout_session_payload(session), "message": "Tryout session scheduled."})
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


@api_login_required
@require_http_methods(["POST"])
def send_tryout_join_offer(request, slug, application_id):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    application = get_object_or_404(TryoutApplication, pk=application_id, team=team)
    try:
        data = _json_body(request)
        join_request, app = TeamTrainingService.move_tryout_to_join_pipeline(
            application=application,
            actor=request.user,
            notes=data.get("notes") or data.get("review_notes") or "",
        )
        return JsonResponse({
            "success": True,
            "tryout": _tryout_application_payload(app, include_private=True),
            "join_request": _join_request_status_payload(join_request),
            "message": "Join offer moved into the roster pipeline.",
        })
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


@api_login_required
@require_http_methods(["GET", "POST"])
def practice_sessions(request, slug):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    if request.method == "GET":
        if not TeamTrainingService.user_can_view_team_ops(request.user, team):
            return _error("You are not allowed to view practice sessions for this team.", 403)
        can_manage = TeamTrainingService.has_team_ops_authority(request.user, team)
        qs = PracticeSession.objects.filter(team=team).select_related("game")[:40]
        return JsonResponse({"success": True, "practice_sessions": [_practice_payload(item, include_private=can_manage) for item in qs]})

    try:
        data = _json_body(request)
        session = TeamTrainingService.create_practice_session(
            team=team,
            actor=request.user,
            title=data.get("title") or "",
            scheduled_at=_parse_scheduled_at(data),
            duration_minutes=data.get("duration_minutes") or data.get("duration") or 60,
            session_type=(data.get("session_type") or data.get("type") or "PRACTICE").upper(),
            focus=data.get("focus") or "",
            goals=data.get("goals") or data.get("notes") or "",
            participant_ids=data.get("participant_ids") or [],
        )
        return JsonResponse({"success": True, "practice": _practice_payload(session), "message": "Practice session scheduled."})
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


@api_login_required
@require_http_methods(["GET", "POST"])
def vod_reviews(request, slug):
    team = get_object_or_404(Team, slug=slug, status=TeamStatus.ACTIVE)
    if request.method == "GET":
        if not TeamTrainingService.user_can_view_team_ops(request.user, team):
            return _error("You are not allowed to view VOD reviews for this team.", 403)
        can_manage = TeamTrainingService.has_team_ops_authority(request.user, team)
        qs = VodReview.objects.filter(team=team).select_related("reviewer", "linked_match", "linked_match__tournament")[:40]
        return JsonResponse({"success": True, "vod_reviews": [_vod_payload(item, include_private=can_manage) for item in qs]})

    try:
        data = _json_body(request)
        review = TeamTrainingService.create_vod_review(
            team=team,
            actor=request.user,
            title=data.get("title") or "",
            external_url=data.get("external_url") or data.get("url") or "",
            category=data.get("category") or "analysis",
            notes=data.get("notes") or "",
            visibility=(data.get("visibility") or "TEAM_ONLY").upper(),
            assigned_player_ids=data.get("assigned_player_ids") or [],
        )
        return JsonResponse({"success": True, "vod": _vod_payload(review), "message": "VOD review added."})
    except (ValidationError, PermissionDenied) as exc:
        return _exception(exc)


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except (json.JSONDecodeError, ValueError):
        raise ValidationError("Invalid JSON payload.")


def _parse_scheduled_at(data):
    raw = data.get("scheduled_at") or data.get("tryout_date")
    if not raw and data.get("date") and data.get("time"):
        raw = f"{data.get('date')}T{data.get('time')}:00"
    if not raw:
        raise ValidationError("scheduled_at is required.")
    try:
        value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValidationError("Invalid scheduled_at format.")
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _resolve_tryout_game(team, data):
    raw_game_id = data.get("game_id") or data.get("game")
    if not raw_game_id:
        return None
    try:
        game_id = int(raw_game_id)
    except (TypeError, ValueError):
        raise ValidationError("Invalid game_id.")
    if team.game_id and team.game_id != game_id:
        raise ValidationError("Tryout game must match the team game.")
    from apps.games.models import Game

    game = Game.objects.filter(pk=game_id).first()
    if not game:
        raise ValidationError("Selected game was not found.")
    return game


def _scrim_request_payload(item, *, include_private=True):
    booking = getattr(item, "booking", None)
    local_time = timezone.localtime(item.scheduled_at) if item.scheduled_at else None
    return {
        "id": item.pk,
        "title": item.title,
        "requesting_team_id": item.requesting_team_id,
        "requesting_team_name": item.requesting_team.name if item.requesting_team_id else "",
        "accepted_team_id": item.accepted_team_id,
        "accepted_team_name": item.accepted_team.name if item.accepted_team_id else "",
        "game": item.game.display_name if item.game_id else "",
        "format": item.format,
        "skill_level": item.skill_level,
        "server_region": item.server_region,
        "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
        "date": local_time.date().isoformat() if local_time else "",
        "time": local_time.strftime("%H:%M") if local_time else "",
        "visibility": item.visibility,
        "notes": item.notes if include_private or item.visibility == "PUBLIC" else "",
        "status": item.status,
        "booking_id": booking.pk if booking else None,
        "match_room_url": match_room_url(booking.match) if booking and booking.match_id else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _scrim_booking_payload(item, *, include_private=True):
    return {
        "id": item.pk,
        "scrim_request_id": item.scrim_request_id,
        "requesting_team_name": item.requesting_team.name,
        "accepted_team_name": item.accepted_team.name,
        "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
        "room_details": item.room_details if include_private else "",
        "status": item.status,
        "match_room_url": match_room_url(item.match) if item.match_id else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _tryout_application_payload(item, *, include_private=True):
    return {
        "id": item.pk,
        "team_id": item.team_id,
        "applicant_id": item.applicant_id,
        "applicant_username": item.applicant.username,
        "game": item.game.display_name if item.game_id else "",
        "ign": item.ign,
        "preferred_role": item.preferred_role,
        "rank_tier": item.rank_tier,
        "availability": item.availability,
        "profile_links": item.profile_links,
        "notes": item.notes if include_private else "",
        "review_notes": item.review_notes if include_private else "",
        "reviewed_by": item.reviewed_by.username if item.reviewed_by_id else "",
        "status": item.status,
        "join_request_id": item.join_request_id,
        "join_request_status": item.join_request.status if item.join_request_id else "",
        "join_request_status_label": item.join_request.get_status_display() if item.join_request_id else "",
        "has_join_offer": bool(item.join_request_id and item.join_request.status == TeamJoinRequest.Status.OFFER_SENT),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _join_request_status_payload(item):
    return {
        "id": item.pk,
        "status": item.status,
        "status_label": item.get_status_display(),
        "applied_position": item.applied_position,
        "scheduled_at": item.tryout_date.isoformat() if item.tryout_date else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _applicant_status_payload(tryout=None, join_request=None, session=None):
    linked_join_request = getattr(tryout, "join_request", None) if tryout else None
    if linked_join_request:
        status = _applicant_status_payload(None, linked_join_request, session)
        status["kind"] = "tryout"
        status["tryout_application_id"] = tryout.pk
        return status
    if tryout:
        title_map = {
            TryoutApplication.Status.PENDING: "Tryout Applied",
            TryoutApplication.Status.REVIEWING: "Under Review",
            TryoutApplication.Status.INVITED: "Tryout Invite",
            TryoutApplication.Status.SCHEDULED: "Tryout Scheduled",
            TryoutApplication.Status.OBSERVATION: "Under Review",
            TryoutApplication.Status.ACCEPTED: "Offer Sent",
            TryoutApplication.Status.REJECTED: "Not Selected",
        }
        return {
            "has_any": True,
            "kind": "tryout",
            "title": title_map.get(tryout.status, tryout.get_status_display()),
            "status": tryout.status,
            "status_label": tryout.get_status_display(),
            "scheduled_at": session.scheduled_at.isoformat() if session and session.scheduled_at else None,
            "created_at": tryout.created_at.isoformat() if tryout.created_at else None,
        }
    if join_request:
        title_map = {
            TeamJoinRequest.Status.PENDING: "Join Request Pending",
            TeamJoinRequest.Status.TRYOUT_SCHEDULED: "Tryout Scheduled",
            TeamJoinRequest.Status.TRYOUT_COMPLETED: "Tryout Completed",
            TeamJoinRequest.Status.OFFER_SENT: "Offer Sent",
            TeamJoinRequest.Status.ACCEPTED: "Offer Accepted",
            TeamJoinRequest.Status.DECLINED: "Offer Declined",
        }
        return {
            "has_any": True,
            "kind": "join_request",
            "join_request_id": join_request.pk,
            "title": title_map.get(join_request.status, join_request.get_status_display()),
            "status": join_request.status,
            "status_label": join_request.get_status_display(),
            "scheduled_at": join_request.tryout_date.isoformat() if join_request.tryout_date else None,
            "created_at": join_request.created_at.isoformat() if join_request.created_at else None,
            "can_accept_offer": join_request.status == TeamJoinRequest.Status.OFFER_SENT,
            "can_decline_offer": join_request.status == TeamJoinRequest.Status.OFFER_SENT,
            "offer_action_url": f"/api/vnext/teams/{join_request.team.slug}/apply/offers/{join_request.pk}/",
        }
    return {"has_any": False}


def _tryout_session_payload(item, *, include_private=True):
    return {
        "id": item.pk,
        "application_id": item.application_id,
        "applicant_id": item.applicant_id,
        "applicant_username": item.applicant.username,
        "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
        "format": item.format,
        "room_details": item.room_details if include_private else "",
        "review_notes": item.review_notes if include_private else "",
        "status": item.status,
        "match_room_url": match_room_url(item.match) if item.match_id else None,
    }


def _applicant_history_tryout_payload(item):
    session = _latest_tryout_session(item)
    join_request = getattr(item, "join_request", None)
    status_label = _history_tryout_status_label(item, join_request, session)
    actions = _offer_actions(join_request)
    scheduled_at = session.scheduled_at if session and session.scheduled_at else None
    return {
        "id": f"tryout-{item.pk}",
        "source_type": "tryout",
        "tryout_application_id": item.pk,
        "join_request_id": join_request.pk if join_request else None,
        "team": _history_team_payload(item.team),
        "team_name": item.team.name if item.team_id else "",
        "team_url": _team_public_url(item.team),
        "game": _game_display_name(item.game),
        "role": item.preferred_role,
        "position": item.preferred_role,
        "status": status_label,
        "status_code": join_request.status if join_request else item.status,
        "raw_tryout_status": item.status,
        "raw_join_request_status": join_request.status if join_request else "",
        "submitted_at": item.created_at.isoformat() if item.created_at else None,
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "applicant_safe_note": item.notes,
        "session": _history_session_payload(session),
        "linked_offer": _history_join_offer_payload(join_request),
        "actions": actions,
        "action_label": actions[0]["label"] if actions else "",
        "action_url": actions[0]["url"] if actions else "",
    }


def _applicant_history_join_payload(item):
    linked_tryout = next(iter(item.tryout_applications.all()), None)
    session = _latest_tryout_session(linked_tryout) if linked_tryout else None
    actions = _offer_actions(item)
    scheduled_at = session.scheduled_at if session and session.scheduled_at else item.tryout_date
    return {
        "id": f"join-{item.pk}",
        "source_type": "join_request",
        "join_request_id": item.pk,
        "tryout_application_id": linked_tryout.pk if linked_tryout else None,
        "team": _history_team_payload(item.team),
        "team_name": item.team.name if item.team_id else "",
        "team_url": _team_public_url(item.team),
        "game": _game_display_name(getattr(item.team, "game", None)),
        "role": item.applied_position,
        "position": item.applied_position,
        "status": _history_join_status_label(item.status),
        "status_code": item.status,
        "raw_tryout_status": linked_tryout.status if linked_tryout else "",
        "raw_join_request_status": item.status,
        "submitted_at": item.created_at.isoformat() if item.created_at else None,
        "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
        "applicant_safe_note": item.message,
        "session": _history_session_payload(session),
        "linked_offer": _history_join_offer_payload(item),
        "actions": actions,
        "action_label": actions[0]["label"] if actions else "",
        "action_url": actions[0]["url"] if actions else "",
    }


def _history_tryout_status_label(item, join_request=None, session=None):
    if join_request:
        return _history_join_status_label(join_request.status)
    if session and session.status == TryoutSession.Status.SCHEDULED:
        return "Tryout Scheduled"
    title_map = {
        TryoutApplication.Status.PENDING: "Applied",
        TryoutApplication.Status.REVIEWING: "Under Review",
        TryoutApplication.Status.INVITED: "Under Review",
        TryoutApplication.Status.SCHEDULED: "Tryout Scheduled",
        TryoutApplication.Status.OBSERVATION: "Under Review",
        TryoutApplication.Status.ACCEPTED: "Offer Sent",
        TryoutApplication.Status.REJECTED: "Declined / Not Selected",
        TryoutApplication.Status.WITHDRAWN: "Withdrawn / Closed",
    }
    return title_map.get(item.status, item.get_status_display())


def _history_join_status_label(status):
    title_map = {
        TeamJoinRequest.Status.PENDING: "Applied",
        TeamJoinRequest.Status.TRYOUT_SCHEDULED: "Tryout Scheduled",
        TeamJoinRequest.Status.TRYOUT_COMPLETED: "Under Review",
        TeamJoinRequest.Status.OFFER_SENT: "Offer Sent",
        TeamJoinRequest.Status.ACCEPTED: "Accepted / Signed",
        TeamJoinRequest.Status.DECLINED: "Declined / Not Selected",
        TeamJoinRequest.Status.WITHDRAWN: "Withdrawn / Closed",
    }
    return title_map.get(status, status.replace("_", " ").title() if status else "")


def _latest_tryout_session(application):
    if not application:
        return None
    return next(iter(application.sessions.all()), None)


def _history_session_payload(session):
    if not session:
        return None
    return {
        "id": session.pk,
        "scheduled_at": session.scheduled_at.isoformat() if session.scheduled_at else None,
        "format": session.format,
        "status": session.status,
    }


def _history_join_offer_payload(join_request):
    if not join_request:
        return None
    return {
        "id": join_request.pk,
        "status": join_request.status,
        "status_label": _history_join_status_label(join_request.status),
        "can_accept": join_request.status == TeamJoinRequest.Status.OFFER_SENT,
        "can_decline": join_request.status == TeamJoinRequest.Status.OFFER_SENT,
        "action_url": f"/api/vnext/teams/{join_request.team.slug}/apply/offers/{join_request.pk}/",
    }


def _offer_actions(join_request):
    if not join_request or join_request.status != TeamJoinRequest.Status.OFFER_SENT:
        return []
    url = f"/api/vnext/teams/{join_request.team.slug}/apply/offers/{join_request.pk}/"
    return [
        {"label": "Accept Offer", "action": "accept", "url": url, "style": "primary"},
        {"label": "Decline Offer", "action": "decline", "url": url, "style": "secondary"},
    ]


def _history_team_payload(team):
    if not team:
        return {"id": None, "name": "", "slug": "", "logo_url": "", "url": ""}
    return {
        "id": team.pk,
        "name": team.name,
        "slug": team.slug,
        "logo_url": _media_url(team, "logo", "logo_image", "avatar"),
        "url": _team_public_url(team),
    }


def _team_public_url(team):
    return f"/teams/{team.slug}/" if team and getattr(team, "slug", "") else ""


def _game_display_name(game):
    if not game:
        return ""
    return (
        getattr(game, "display_name", "")
        or getattr(game, "name", "")
        or getattr(game, "short_code", "")
        or ""
    )


def _media_url(obj, *field_names):
    for field_name in field_names:
        field = getattr(obj, field_name, None)
        try:
            if field and getattr(field, "url", None):
                return field.url
        except Exception:
            continue
    return ""


def _practice_payload(item, *, include_private=True):
    local_time = timezone.localtime(item.scheduled_at) if item.scheduled_at else None
    return {
        "id": item.pk,
        "title": item.title,
        "game": item.game.display_name if item.game_id else "",
        "session_type": item.session_type,
        "scheduled_at": item.scheduled_at.isoformat() if item.scheduled_at else None,
        "date": local_time.date().isoformat() if local_time else "",
        "time": local_time.strftime("%H:%M") if local_time else "",
        "duration_minutes": item.duration_minutes,
        "duration": item.duration_minutes,
        "focus": item.focus,
        "goals": item.goals if include_private else "",
        "type": item.session_type,
        "status": item.status,
        "notes": item.notes if include_private else "",
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def _vod_payload(item, *, include_private=True):
    return {
        "id": item.pk,
        "title": item.title,
        "external_url": item.external_url,
        "url": item.external_url,
        "category": item.category,
        "notes": item.notes if include_private else "",
        "reviewer": item.reviewer.username if item.reviewer_id else "",
        "visibility": item.visibility,
        "status": item.status,
        "match_room_url": match_room_url(item.linked_match) if item.linked_match_id else None,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def models_team_booking_filter(team):
    from django.db.models import Q

    return Q(requesting_team=team) | Q(accepted_team=team)


def _exception(exc):
    if isinstance(exc, PermissionDenied):
        return _error(str(exc), 403)
    if isinstance(exc, ValidationError):
        message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
        return _error(message, 400)
    return _error(str(exc), 400)


def _error(message, status):
    return JsonResponse({"success": False, "error": message}, status=status)
