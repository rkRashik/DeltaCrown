"""
TOC API — Participant endpoints.

Sprint 2: S2-B1 through S2-B9
PRD: §3.1–§3.9

Endpoints:
  GET    /api/toc/<slug>/participants/                  — Paginated, filterable list
  GET    /api/toc/<slug>/participants/<id>/              — Detail (drawer payload)
  POST   /api/toc/<slug>/participants/<id>/approve/      — Approve registration
  POST   /api/toc/<slug>/participants/<id>/reject/       — Reject with reason
  POST   /api/toc/<slug>/participants/<id>/disqualify/   — DQ with reason
  POST   /api/toc/<slug>/participants/<id>/verify-payment/ — Manual payment verify
  POST   /api/toc/<slug>/participants/<id>/toggle-checkin/ — Toggle check-in
  POST   /api/toc/<slug>/participants/bulk-action/       — Bulk approve/reject/DQ/checkin
  GET    /api/toc/<slug>/participants/export/             — CSV export
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.participants_service import TOCParticipantService
from apps.tournaments.api.toc.serializers import (
    BulkActionInputSerializer,
    BulkActionResultSerializer,
    ParticipantDetailSerializer,
    ParticipantListSerializer,
    ParticipantRowSerializer,
    RejectInputSerializer,
)


class ParticipantListView(TOCBaseView):
    """
    GET /api/toc/<slug>/participants/
    S2-B1: Paginated, filterable, searchable participant list.
    """

    def get(self, request, slug):
        page = int(request.query_params.get('page', 1))
        data = TOCParticipantService.get_participant_list(
            tournament=self.tournament,
            page=page,
            status=request.query_params.get('status'),
            payment=request.query_params.get('payment'),
            checkin=request.query_params.get('checkin'),
            search=request.query_params.get('search'),
            ordering=request.query_params.get('ordering', '-registered_at'),
        )
        serializer = ParticipantListSerializer(data)
        return Response(serializer.data)


class ParticipantDetailView(TOCBaseView):
    """
    GET /api/toc/<slug>/participants/<id>/
    S2-B8: Full participant detail for drawer.
    """

    def get(self, request, slug, pk):
        try:
            data = TOCParticipantService.get_participant_detail(
                tournament=self.tournament,
                registration_id=pk,
            )
            serializer = ParticipantDetailSerializer(data)
            return Response(serializer.data)
        except DjangoValidationError as e:
            return Response(
                {'error': e.message if hasattr(e, 'message') else str(e)},
                status=status.HTTP_404_NOT_FOUND,
            )


class ApproveView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/approve/
    S2-B2: Approve a pending registration.
    """

    def post(self, request, slug, pk):
        try:
            row = TOCParticipantService.approve_registration(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
            )
            return Response({
                'ok': True,
                'message': 'Registration approved.',
                'participant': ParticipantRowSerializer(row).data,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RejectView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/reject/
    S2-B3: Reject a registration with optional reason.
    """

    def post(self, request, slug, pk):
        ser = RejectInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            row = TOCParticipantService.reject_registration(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
                reason=ser.validated_data.get('reason', ''),
            )
            return Response({
                'ok': True,
                'message': 'Registration rejected.',
                'participant': ParticipantRowSerializer(row).data,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DisqualifyView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/disqualify/
    S2-B4: Disqualify with reason and evidence.
    """

    def post(self, request, slug, pk):
        ser = RejectInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            row = TOCParticipantService.disqualify_registration(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
                reason=ser.validated_data.get('reason', ''),
                evidence=ser.validated_data.get('evidence', ''),
            )
            return Response({
                'ok': True,
                'message': 'Participant disqualified.',
                'participant': ParticipantRowSerializer(row).data,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerifyPaymentView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/verify-payment/
    S2-B6: Manual payment verification.
    """

    def post(self, request, slug, pk):
        try:
            row = TOCParticipantService.verify_payment(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
            )
            return Response({
                'ok': True,
                'message': 'Payment verified.',
                'participant': ParticipantRowSerializer(row).data,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ToggleCheckinView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/toggle-checkin/
    S2-B7: Toggle check-in status.
    """

    def post(self, request, slug, pk):
        try:
            row = TOCParticipantService.toggle_checkin(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
            )
            return Response({
                'ok': True,
                'message': 'Check-in toggled.',
                'participant': ParticipantRowSerializer(row).data,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class BulkActionView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/bulk-action/
    S2-B5: Bulk approve/reject/DQ/check-in.
    """

    def post(self, request, slug):
        ser = BulkActionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = TOCParticipantService.bulk_action(
                tournament=self.tournament,
                action=ser.validated_data['action'],
                registration_ids=ser.validated_data['ids'],
                actor=request.user,
                reason=ser.validated_data.get('reason', ''),
            )
            return Response(BulkActionResultSerializer(result).data)
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ExportCSVView(TOCBaseView):
    """
    GET /api/toc/<slug>/participants/export/
    S2-B9: CSV export of all participants.
    """

    def get(self, request, slug):
        csv_content = TOCParticipantService.export_csv(self.tournament)
        response = HttpResponse(csv_content, content_type='text/csv')
        filename = f"{self.tournament.slug}_participants.csv"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
