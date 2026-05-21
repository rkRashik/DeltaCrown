"""Mobile match, lobby, check-in, result, and proof endpoints."""
from __future__ import annotations

from rest_framework import status as http_status
from rest_framework.permissions import IsAuthenticated

from apps.tournaments.models import Match

from ..base import MobileApiView
from ..responses import error_response, success_response
from ..tournaments.serializers import paginate_queryset
from .serializers import lobby_detail, match_card, match_detail, polling_status, user_can_access_match
from .services import MobileMatchValidation, check_in_match, matches_for_user, submit_match_result, upload_match_proof


class MobileMyMatchesView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = matches_for_user(request.user).select_related("tournament__game").order_by("-scheduled_time", "-id")

        status_filter = request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(state=status_filter)

        tournament = request.query_params.get("tournament")
        if tournament:
            if str(tournament).isdigit():
                queryset = queryset.filter(tournament_id=int(tournament))
            else:
                queryset = queryset.filter(tournament__slug=tournament)

        page = _positive_int(request.query_params.get("page"), 1)
        page_size = _positive_int(request.query_params.get("page_size"), 20)
        page_obj, pagination = paginate_queryset(queryset, page, page_size)
        return success_response(
            {
                "matches": [match_card(match, request.user) for match in page_obj.object_list],
                "pagination": pagination,
            }
        )


class MobileMatchDetailView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request, match_id: int):
        match = _get_match(match_id)
        if match is None:
            return error_response("not_found", "Match not found.", status=http_status.HTTP_404_NOT_FOUND)
        if not user_can_access_match(match, request.user):
            return error_response("permission_denied", "You cannot access this match.", status=http_status.HTTP_403_FORBIDDEN)
        return success_response(match_detail(match, request.user))


class MobileMatchLobbyView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request, match_id: int):
        match = _get_match(match_id)
        if match is None:
            return error_response("not_found", "Match not found.", status=http_status.HTTP_404_NOT_FOUND)
        if not user_can_access_match(match, request.user):
            return error_response("permission_denied", "You cannot access this lobby.", status=http_status.HTTP_403_FORBIDDEN)
        return success_response(lobby_detail(match, request.user))


class MobileMatchCheckInView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id: int):
        match = _get_match(match_id)
        if match is None:
            return error_response("not_found", "Match not found.", status=http_status.HTTP_404_NOT_FOUND)
        try:
            check_in = check_in_match(match, request.user)
        except MobileMatchValidation as exc:
            return error_response(exc.code, exc.message, status=exc.status_code)
        match.refresh_from_db()
        return success_response({"check_in": check_in, "lobby": lobby_detail(match, request.user)})


class MobileMatchSubmitResultView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id: int):
        match = _get_match(match_id)
        if match is None:
            return error_response("not_found", "Match not found.", status=http_status.HTTP_404_NOT_FOUND)
        try:
            submission = submit_match_result(
                match,
                request.user,
                request.data,
                proof_url=request.data.get("proof_url") or request.data.get("proof_screenshot_url") or "",
                proof_file=request.FILES.get("proof_file"),
            )
        except MobileMatchValidation as exc:
            return error_response(exc.code, exc.message, status=exc.status_code)
        match.refresh_from_db()
        return success_response(
            {
                "state": "pending",
                "submission": {
                    "id": submission.id,
                    "status": submission.status,
                    "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                },
                "match": match_card(match, request.user),
            },
            status=http_status.HTTP_201_CREATED,
        )


class MobileMatchUploadProofView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id: int):
        match = _get_match(match_id)
        if match is None:
            return error_response("not_found", "Match not found.", status=http_status.HTTP_404_NOT_FOUND)
        proof_url = request.data.get("proof_url") or request.data.get("proof_screenshot_url") or ""
        proof_file = request.FILES.get("proof_file")
        if not proof_url and proof_file is None:
            return error_response("validation_error", "proof_url or proof_file is required.")
        try:
            payload = upload_match_proof(match, request.user, proof_url=proof_url, proof_file=proof_file)
        except MobileMatchValidation as exc:
            return error_response(exc.code, exc.message, status=exc.status_code)
        return success_response(payload)


class MobileMatchStatusView(MobileApiView):
    permission_classes = [IsAuthenticated]

    def get(self, request, match_id: int):
        match = _get_match(match_id)
        if match is None:
            return error_response("not_found", "Match not found.", status=http_status.HTTP_404_NOT_FOUND)
        if not user_can_access_match(match, request.user):
            return error_response("permission_denied", "You cannot access this match.", status=http_status.HTTP_403_FORBIDDEN)
        return success_response(polling_status(match, request.user))


def _get_match(match_id: int) -> Match | None:
    return Match.objects.select_related("tournament__game").filter(id=match_id, is_deleted=False).first()


def _positive_int(value, default):
    try:
        parsed = int(value)
        return parsed if parsed > 0 else default
    except (TypeError, ValueError):
        return default
