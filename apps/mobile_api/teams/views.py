"""Mobile team endpoints."""
from __future__ import annotations

from django.db.models import Q
from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated

from apps.games.models import Game
from apps.organizations.choices import TeamStatus
from apps.organizations.models import Team

from ..base import MobileApiView
from ..responses import error_response, success_response
from ..tournaments.serializers import paginate_queryset
from .serializers import MobileTeamCreateSerializer, join_request_summary, team_card, team_detail
from .services import (
    MobileTeamValidation,
    accept_join_request,
    apply_to_team,
    create_independent_team,
    decline_join_request,
    resolve_team,
    team_status_for_user,
)


class MobileTeamStatusView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return success_response(team_status_for_user(request.user))


class MobileTeamListView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Team.objects.filter(status=TeamStatus.ACTIVE, visibility="PUBLIC").select_related("organization")

        search = request.query_params.get("search")
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(tag__icontains=search))

        game_param = request.query_params.get("game")
        if game_param:
            if str(game_param).isdigit():
                queryset = queryset.filter(game_id=int(game_param))
            else:
                game = Game.objects.filter(slug=game_param).first()
                queryset = queryset.filter(game_id=game.id if game else -1)

        page = _positive_int(request.query_params.get("page"), 1)
        page_size = _positive_int(request.query_params.get("page_size"), 20)
        page_obj, pagination = paginate_queryset(queryset.order_by("name"), page, page_size)
        games = _games_for_teams(page_obj.object_list)
        return success_response(
            {
                "teams": [team_card(team, request.user, games.get(team.game_id)) for team in page_obj.object_list],
                "pagination": pagination,
            }
        )


class MobileTeamCreateView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = MobileTeamCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return _field_error_response(serializer.errors)

        try:
            team = create_independent_team(user=request.user, validated_data=serializer.validated_data)
        except MobileTeamValidation as exc:
            return error_response(exc.code, exc.message, status=exc.status_code)

        return success_response(
            {"team": team_card(team, request.user, serializer.validated_data["game_obj"])},
            status=http_status.HTTP_201_CREATED,
        )


class MobileTeamDetailView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id_or_slug: str):
        team = resolve_team(id_or_slug)
        if team is None:
            return error_response("not_found", "Team not found.", status=http_status.HTTP_404_NOT_FOUND)
        game = Game.objects.filter(id=team.game_id).first()
        return success_response(team_detail(team, request.user, game))


class MobileTeamApplyView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id_or_slug: str):
        team = resolve_team(id_or_slug)
        if team is None:
            return error_response("not_found", "Team not found.", status=http_status.HTTP_404_NOT_FOUND)
        try:
            join_request, created = apply_to_team(
                team=team,
                user=request.user,
                message=request.data.get("message") or "",
            )
        except MobileTeamValidation as exc:
            return error_response(exc.code, exc.message, status=exc.status_code)

        return success_response(
            {
                "status": "created" if created else "pending",
                "join_request": join_request_summary(join_request),
            },
            status=http_status.HTTP_201_CREATED if created else http_status.HTTP_200_OK,
        )


class MobileTeamRequestAcceptView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id_or_slug: str, request_id: int):
        return _review_request(request, id_or_slug, request_id, action="accept")


class MobileTeamRequestDeclineView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id_or_slug: str, request_id: int):
        return _review_request(request, id_or_slug, request_id, action="decline")


def _review_request(request, id_or_slug: str, request_id: int, *, action: str):
    team = resolve_team(id_or_slug)
    if team is None:
        return error_response("not_found", "Team not found.", status=http_status.HTTP_404_NOT_FOUND)

    try:
        if action == "accept":
            payload = accept_join_request(team=team, join_request_id=request_id, actor=request.user)
        else:
            payload = decline_join_request(team=team, join_request_id=request_id, actor=request.user)
    except MobileTeamValidation as exc:
        return error_response(exc.code, exc.message, status=exc.status_code)

    status_label = "accepted" if action == "accept" else "declined"
    return success_response({"status": status_label, **payload})


def _games_for_teams(teams) -> dict[int, Game]:
    game_ids = {team.game_id for team in teams}
    return {game.id: game for game in Game.objects.filter(id__in=game_ids)}


def _positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default


def _field_error_response(details):
    return error_response(
        "validation_error",
        "Validation failed.",
        details=details if isinstance(details, dict) else {"detail": details},
        status=http_status.HTTP_400_BAD_REQUEST,
    )
