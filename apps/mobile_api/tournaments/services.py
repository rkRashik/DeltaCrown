"""Mobile-safe tournament join helpers."""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.organizations.models import Team, TeamMembership
from apps.tournaments.models import Registration, Tournament
from apps.tournaments.services.registration_service import RegistrationService
from apps.user_profile.models import GameProfile, UserProfile

from .serializers import ACTIVE_REGISTRATION_STATUSES, registration_summary


def resolve_tournament(id_or_slug: str) -> Tournament | None:
    queryset = Tournament.objects.select_related("game", "organizer")
    if str(id_or_slug).isdigit():
        return queryset.filter(id=int(id_or_slug), is_deleted=False).first()
    return queryset.filter(slug=id_or_slug, is_deleted=False).first()


def eligible_team_for_user(tournament: Tournament, user):
    if tournament.participation_type != Tournament.TEAM:
        return None
    return (
        Team.objects.filter(
            game_id=tournament.game_id,
            vnext_memberships__user=user,
            vnext_memberships__status=TeamMembership.Status.ACTIVE,
            status="ACTIVE",
        )
        .distinct()
        .order_by("id")
        .first()
    )


def current_registration(tournament: Tournament, user):
    return (
        Registration.objects.filter(tournament=tournament, user=user, is_deleted=False)
        .exclude(status__in=[Registration.CANCELLED, Registration.REJECTED])
        .order_by("-updated_at", "-id")
        .first()
    )


def build_eligibility(tournament: Tournament, user) -> dict:
    existing = current_registration(tournament, user)
    if existing:
        return _state(
            False,
            "already_joined",
            "You are already registered for this tournament.",
            "view_registration",
            existing,
        )

    if tournament.status not in [Tournament.REGISTRATION_OPEN]:
        return _state(False, "closed", "Registration is not open for this tournament.", "none")

    if not tournament.is_registration_open():
        return _state(False, "closed", "Registration is outside the active registration window.", "none")

    if tournament.is_full() and tournament.max_waitlist_size == 0:
        return _state(False, "full", "This tournament is full.", "none")

    if not UserProfile.objects.filter(user=user).exists():
        return _state(False, "profile_required", "Complete your profile before joining.", "complete_profile")

    if not GameProfile.objects.filter(user=user, game=tournament.game).exists():
        return _state(
            False,
            "game_passport_required",
            f"Add a {tournament.game.display_name} game passport before joining.",
            "add_game_passport",
        )

    if tournament.participation_type == Tournament.TEAM and eligible_team_for_user(tournament, user) is None:
        return _state(
            False,
            "team_required",
            "Create or join an eligible team for this game before joining.",
            "create_or_join_team",
        )

    return _state(True, "joinable", "You can join this tournament.", "join")


def join_tournament(tournament: Tournament, user, team_id: int | None = None) -> tuple[dict, int]:
    existing = current_registration(tournament, user)
    if existing:
        return (
            {
                "joined": False,
                "registration": registration_summary(existing),
                "eligibility": _state(
                    False,
                    "already_joined",
                    "You are already registered for this tournament.",
                    "view_registration",
                    existing,
                ),
            },
            200,
        )

    eligibility = build_eligibility(tournament, user)
    if not eligibility["can_join"]:
        return {"joined": False, "eligibility": eligibility}, 400

    selected_team_id = None
    if tournament.participation_type == Tournament.TEAM:
        if team_id is not None:
            selected_team_id = team_id
        else:
            team = eligible_team_for_user(tournament, user)
            selected_team_id = team.id if team else None
        if selected_team_id is None:
            return {"joined": False, "eligibility": eligibility}, 400

    try:
        registration = RegistrationService.register_participant(
            tournament_id=tournament.id,
            user=user,
            team_id=selected_team_id,
            registration_data={"source": "mobile_api"},
        )
    except (ValidationError, IntegrityError) as exc:
        existing = current_registration(tournament, user)
        if existing:
            return (
                {
                    "joined": False,
                    "registration": registration_summary(existing),
                    "eligibility": _state(
                        False,
                        "already_joined",
                        "You are already registered for this tournament.",
                        "view_registration",
                        existing,
                    ),
                },
                200,
            )
        return {"joined": False, "eligibility": _validation_error_state(exc)}, 400

    next_action = "web_payment_required" if tournament.has_entry_fee else "view_registration"
    status = "payment_required" if tournament.has_entry_fee else "already_joined"
    return (
        {
            "joined": True,
            "registration": registration_summary(registration),
            "eligibility": _state(
                False,
                status,
                "Payment is required to complete registration." if tournament.has_entry_fee else "Registration started.",
                next_action,
                registration,
            ),
        },
        201,
    )


def _state(can_join: bool, status: str, message: str, next_action: str, registration=None) -> dict:
    data = {
        "can_join": can_join,
        "status": status,
        "message": message,
        "next_action": next_action,
    }
    if registration is not None:
        data["registration"] = registration_summary(registration)
    return data


def _validation_error_state(exc) -> dict:
    message = "; ".join(getattr(exc, "messages", []) or [str(exc)])
    lowered = message.lower()
    if "team" in lowered:
        status, next_action = "team_required", "create_or_join_team"
    elif "passport" in lowered or "game" in lowered:
        status, next_action = "game_passport_required", "add_game_passport"
    elif "profile" in lowered:
        status, next_action = "profile_required", "complete_profile"
    elif "already" in lowered:
        status, next_action = "already_joined", "view_registration"
    elif "not accepting" in lowered or "closed" in lowered or "opens" in lowered:
        status, next_action = "closed", "none"
    else:
        status, next_action = "unknown", "none"
    return _state(False, status, message, next_action)
