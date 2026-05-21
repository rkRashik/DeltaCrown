"""Mobile tournament browse, detail, and join endpoints."""
from __future__ import annotations

from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated

from apps.tournaments.models import Registration, Tournament

from ..base import MobileApiView
from ..responses import error_response, success_response
from .serializers import paginate_queryset, tournament_card, tournament_detail
from .services import build_eligibility, join_tournament, resolve_tournament


class MobileTournamentListView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Tournament.objects.filter(is_deleted=False).select_related("game", "organizer")
        queryset = queryset.exclude(status__in=[Tournament.DRAFT, Tournament.PENDING_APPROVAL, Tournament.ARCHIVED])

        game = request.query_params.get("game")
        if game:
            if str(game).isdigit():
                queryset = queryset.filter(game_id=int(game))
            else:
                queryset = queryset.filter(game__slug=game)

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)

        page = _positive_int(request.query_params.get("page"), 1)
        page_size = _positive_int(request.query_params.get("page_size"), 20)
        page_obj, pagination = paginate_queryset(queryset.order_by("-tournament_start"), page, page_size)
        return success_response(
            {
                "tournaments": [tournament_card(tournament, request.user) for tournament in page_obj.object_list],
                "pagination": pagination,
            }
        )


class MobileTournamentDetailView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_or_slug: str):
        tournament = resolve_tournament(id_or_slug)
        if tournament is None:
            return error_response("not_found", "Tournament not found.", status=http_status.HTTP_404_NOT_FOUND)
        eligibility = build_eligibility(tournament, request.user)
        return success_response(tournament_detail(tournament, request.user, eligibility))


class MobileTournamentJoinView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id_or_slug: str):
        tournament = resolve_tournament(id_or_slug)
        if tournament is None:
            return error_response("not_found", "Tournament not found.", status=http_status.HTTP_404_NOT_FOUND)
        team_id = request.data.get("team_id")
        team_id = _positive_int(team_id, None) if team_id not in (None, "") else None
        payload, status_code = join_tournament(tournament, request.user, team_id=team_id)
        return success_response(payload, status=status_code)


class MobileMyTournamentsView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        registrations = (
            Registration.objects.filter(user=request.user, is_deleted=False)
            .select_related("tournament__game", "tournament__organizer")
            .order_by("-updated_at", "-id")
        )
        return success_response(
            {
                "registrations": [
                    {
                        "registration": {
                            "id": registration.id,
                            "status": registration.status,
                            "current_step": registration.current_step,
                            "next_action": _next_action_for_registration(registration),
                            "checked_in": registration.checked_in,
                        },
                        "tournament": tournament_card(registration.tournament, request.user),
                        "match_status": None,
                        "lobby_status": None,
                    }
                    for registration in registrations
                ]
            }
        )


def _positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _next_action_for_registration(registration: Registration) -> str:
    if registration.status in [Registration.PENDING, Registration.PAYMENT_SUBMITTED] and registration.tournament.has_entry_fee:
        return "web_payment_required"
    if registration.status == Registration.CONFIRMED:
        return "view_registration"
    if registration.status == Registration.WAITLISTED:
        return "waitlist"
    return "view_registration"
