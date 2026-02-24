"""
TOC Brackets & Competition Engine API Views — Sprint 5.

S5-B1  POST  brackets/generate/       — Generate bracket
S5-B2  POST  brackets/reset/          — Reset bracket
S5-B3  POST  brackets/publish/        — Publish bracket
S5-B4  PUT   brackets/seeds/          — Reorder seeding
S5-B5  GET   brackets/                — Current bracket state
S5-B6  POST  schedule/auto-generate/  — Auto-schedule
S5-B7  POST  schedule/bulk-shift/     — Bulk shift times
S5-B8  POST  schedule/add-break/      — Insert break
S5-B9  GET   schedule/                — Full schedule
S5-B10       groups/                  — Group stage CRUD
S5-B11       pipelines/               — Qualifier pipeline CRUD
"""

from rest_framework import status
from rest_framework.response import Response

from .base import TOCBaseView
from .brackets_service import TOCBracketsService
from .serializers import (
    AutoScheduleInputSerializer,
    BreakInsertInputSerializer,
    BulkShiftInputSerializer,
    GroupConfigInputSerializer,
    GroupDrawInputSerializer,
    PipelineCreateInputSerializer,
    SeedReorderInputSerializer,
)


# ── Bracket endpoints ──────────────────────────────────────────

class BracketGetView(TOCBaseView):
    """S5-B5: GET /api/toc/<slug>/brackets/"""

    def get(self, request, slug):
        data = TOCBracketsService.get_bracket(self.tournament)
        return Response(data)


class BracketGenerateView(TOCBaseView):
    """S5-B1: POST /api/toc/<slug>/brackets/generate/"""

    def post(self, request, slug):
        try:
            data = TOCBracketsService.generate_bracket(
                self.tournament, request.user
            )
            return Response(data, status=status.HTTP_201_CREATED)
        except (ValueError, Exception) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class BracketResetView(TOCBaseView):
    """S5-B2: POST /api/toc/<slug>/brackets/reset/"""

    def post(self, request, slug):
        data = TOCBracketsService.reset_bracket(self.tournament, request.user)
        return Response(data)


class BracketPublishView(TOCBaseView):
    """S5-B3: POST /api/toc/<slug>/brackets/publish/"""

    def post(self, request, slug):
        try:
            data = TOCBracketsService.publish_bracket(
                self.tournament, request.user
            )
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class BracketSeedsView(TOCBaseView):
    """S5-B4: PUT /api/toc/<slug>/brackets/seeds/"""

    def put(self, request, slug):
        ser = SeedReorderInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.reorder_seeds(
                self.tournament, ser.validated_data["seeds"], request.user
            )
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


# ── Schedule endpoints ─────────────────────────────────────────

class ScheduleGetView(TOCBaseView):
    """S5-B9: GET /api/toc/<slug>/schedule/"""

    def get(self, request, slug):
        data = TOCBracketsService.get_schedule(self.tournament)
        return Response(data)


class ScheduleAutoGenerateView(TOCBaseView):
    """S5-B6: POST /api/toc/<slug>/schedule/auto-generate/"""

    def post(self, request, slug):
        ser = AutoScheduleInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = TOCBracketsService.auto_schedule(
            self.tournament, ser.validated_data, request.user
        )
        return Response(data)


class ScheduleBulkShiftView(TOCBaseView):
    """S5-B7: POST /api/toc/<slug>/schedule/bulk-shift/"""

    def post(self, request, slug):
        ser = BulkShiftInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.bulk_shift(
                self.tournament, ser.validated_data, request.user
            )
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class ScheduleAddBreakView(TOCBaseView):
    """S5-B8: POST /api/toc/<slug>/schedule/add-break/"""

    def post(self, request, slug):
        ser = BreakInsertInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = TOCBracketsService.add_break(
            self.tournament, ser.validated_data, request.user
        )
        return Response(data)


# ── Group Stage endpoints ──────────────────────────────────────

class GroupStageView(TOCBaseView):
    """S5-B10: GET /api/toc/<slug>/groups/"""

    def get(self, request, slug):
        data = TOCBracketsService.get_groups(self.tournament)
        return Response(data)


class GroupConfigureView(TOCBaseView):
    """S5-B10: POST /api/toc/<slug>/groups/configure/"""

    def post(self, request, slug):
        ser = GroupConfigInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.configure_groups(
                self.tournament, ser.validated_data, request.user
            )
            return Response(data)
        except (ValueError, Exception) as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class GroupDrawView(TOCBaseView):
    """S5-B10: POST /api/toc/<slug>/groups/draw/"""

    def post(self, request, slug):
        ser = GroupDrawInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            data = TOCBracketsService.draw_groups(
                self.tournament, ser.validated_data, request.user
            )
            return Response(data)
        except ValueError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


class GroupStandingsView(TOCBaseView):
    """S5-B10: GET /api/toc/<slug>/groups/standings/"""

    def get(self, request, slug):
        data = TOCBracketsService.get_group_standings(self.tournament)
        return Response(data)


# ── Qualifier Pipeline endpoints ───────────────────────────────

class PipelineListCreateView(TOCBaseView):
    """S5-B11: GET/POST /api/toc/<slug>/pipelines/"""

    def get(self, request, slug):
        data = TOCBracketsService.list_pipelines(self.tournament)
        return Response(data)

    def post(self, request, slug):
        ser = PipelineCreateInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = TOCBracketsService.create_pipeline(
            self.tournament, ser.validated_data, request.user
        )
        return Response(data, status=status.HTTP_201_CREATED)


class PipelineDetailView(TOCBaseView):
    """S5-B11: PATCH/DELETE /api/toc/<slug>/pipelines/<id>/"""

    def patch(self, request, slug, pipeline_id):
        try:
            data = TOCBracketsService.update_pipeline(
                self.tournament, str(pipeline_id), request.data
            )
            return Response(data)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    def delete(self, request, slug, pipeline_id):
        TOCBracketsService.delete_pipeline(
            self.tournament, str(pipeline_id)
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
