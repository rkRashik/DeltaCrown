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
from django.core.cache import cache
from django.db import models
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from apps.tournaments.api.toc.base import TOCBaseView
from apps.tournaments.api.toc.cache_utils import bump_toc_scopes, toc_cache_key
from apps.tournaments.api.toc.participants_service import TOCParticipantService
from apps.tournaments.api.toc.serializers import (
    BulkActionInputSerializer,
    BulkActionResultSerializer,
    ParticipantNotifyInputSerializer,
    RejectInputSerializer,
)


class ParticipantListView(TOCBaseView):
    """
    GET /api/toc/<slug>/participants/
    S2-B1: Paginated, filterable, searchable participant list.
    """

    def get(self, request, slug):
        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        page = max(1, page)

        cache_bucket = int(timezone.now().timestamp() // 8)
        query_sig = request.META.get('QUERY_STRING', '')
        cache_key = toc_cache_key('participants', self.tournament.id, cache_bucket, page, query_sig)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCParticipantService.get_participant_list(
            tournament=self.tournament,
            page=page,
            status=request.query_params.get('status'),
            payment=request.query_params.get('payment'),
            checkin=request.query_params.get('checkin'),
            search=request.query_params.get('search'),
            ordering=request.query_params.get('ordering', '-registered_at'),
        )
        payload = data
        cache.set(cache_key, payload, timeout=12)
        return Response(payload)


class ParticipantDetailView(TOCBaseView):
    """
    GET /api/toc/<slug>/participants/<id>/
    S2-B8: Full participant detail for drawer.
    """

    def get(self, request, slug, pk):
        try:
            cache_bucket = int(timezone.now().timestamp() // 10)
            cache_key = toc_cache_key('participants', self.tournament.id, 'detail', pk, cache_bucket)
            cached = cache.get(cache_key)
            if cached is not None:
                return Response(cached)

            data = TOCParticipantService.get_participant_detail(
                tournament=self.tournament,
                registration_id=pk,
            )
            payload = data
            cache.set(cache_key, payload, timeout=15)
            return Response(payload)
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
            bump_toc_scopes(self.tournament.id, 'participants', 'participants_adv', 'overview', 'analytics')
            return Response({
                'ok': True,
                'message': 'Registration approved.',
                'participant': row,
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
            bump_toc_scopes(self.tournament.id, 'participants', 'participants_adv', 'overview', 'analytics')
            return Response({
                'ok': True,
                'message': 'Registration rejected.',
                'participant': row,
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
                auto_refund=request.data.get('auto_refund', False),
            )
            bump_toc_scopes(self.tournament.id, 'participants', 'participants_adv', 'overview', 'analytics', 'payments')
            return Response({
                'ok': True,
                'message': 'Participant disqualified.',
                'participant': row,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class HardBlockView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/hard-block/
    Permanently block participant/team from re-registration in this tournament.
    """

    def post(self, request, slug, pk):
        ser = RejectInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reason = (ser.validated_data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'ok': False, 'error': 'Block reason is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            row = TOCParticipantService.hard_block_registration(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
                reason=reason,
                auto_refund=bool(request.data.get('auto_refund', False)),
            )
            bump_toc_scopes(self.tournament.id, 'participants', 'participants_adv', 'overview', 'analytics', 'payments')
            return Response({
                'ok': True,
                'message': 'Participant hard-blocked from this tournament.',
                'participant': row,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UnblockView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/unblock/
    Lift tournament-specific hard block for this participant/team.
    """

    def post(self, request, slug, pk):
        ser = RejectInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            row = TOCParticipantService.unblock_registration(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
                reason=ser.validated_data.get('reason', ''),
            )
            bump_toc_scopes(self.tournament.id, 'participants', 'participants_adv', 'overview', 'analytics')
            return Response({
                'ok': True,
                'message': 'Participant block removed.',
                'participant': row,
            })
        except (DjangoValidationError, Exception) as e:
            msg = e.message if hasattr(e, 'message') else str(e)
            return Response(
                {'ok': False, 'error': msg},
                status=status.HTTP_400_BAD_REQUEST,
            )


class NotifyParticipantView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/<id>/notify/
    Send direct alert/message to participant roster.
    """

    def post(self, request, slug, pk):
        ser = ParticipantNotifyInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            result = TOCParticipantService.notify_participant(
                tournament=self.tournament,
                registration_id=pk,
                actor=request.user,
                subject=ser.validated_data.get('subject', 'TOC Alert'),
                message=ser.validated_data['message'],
            )
            bump_toc_scopes(self.tournament.id, 'participants', 'notifications', 'overview')
            return Response({
                'ok': True,
                'message': f"Alert sent to {result.get('recipient_count', 0)} recipient(s).",
                'recipient_count': result.get('recipient_count', 0),
                'participant': result.get('participant'),
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
            bump_toc_scopes(self.tournament.id, 'participants', 'payments', 'overview', 'analytics')
            return Response({
                'ok': True,
                'message': 'Payment verified.',
                'participant': row,
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
            bump_toc_scopes(self.tournament.id, 'participants', 'overview', 'analytics')
            return Response({
                'ok': True,
                'message': 'Check-in toggled.',
                'participant': row,
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
            bump_toc_scopes(self.tournament.id, 'participants', 'participants_adv', 'overview', 'analytics', 'payments')
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


class ImportCSVView(TOCBaseView):
    """
    POST /api/toc/<slug>/participants/import/
    S28: Bulk import participants from CSV.
    Expects CSV with columns: username (or email), team_name (optional), seed (optional).
    """

    def post(self, request, slug):
        import csv
        import io

        csv_file = request.FILES.get('file')
        if not csv_file:
            csv_text = request.data.get('csv_text', '')
            if not csv_text:
                return Response({'error': 'No file or csv_text provided'}, status=400)
            reader = csv.DictReader(io.StringIO(csv_text))
        else:
            decoded = csv_file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(decoded))

        results = {'imported': 0, 'skipped': 0, 'errors': []}

        from django.contrib.auth import get_user_model
        User = get_user_model()

        for row_num, row in enumerate(reader, start=2):
            try:
                username = (row.get('username') or row.get('email') or '').strip()
                if not username:
                    results['errors'].append(f'Row {row_num}: Missing username/email')
                    results['skipped'] += 1
                    continue

                # Find user by username or email
                user = User.objects.filter(
                    models.Q(username__iexact=username) | models.Q(email__iexact=username)
                ).first()

                if not user:
                    results['errors'].append(f'Row {row_num}: User "{username}" not found')
                    results['skipped'] += 1
                    continue

                # Check for existing registration
                from apps.tournaments.models.registration import Registration
                existing = Registration.objects.filter(
                    tournament=self.tournament, user=user,
                ).exists()

                if existing:
                    results['errors'].append(f'Row {row_num}: "{username}" already registered')
                    results['skipped'] += 1
                    continue

                # Create registration
                reg = Registration.objects.create(
                    tournament=self.tournament,
                    user=user,
                    status='approved',
                    source='csv_import',
                )

                # Seed if provided
                seed = (row.get('seed') or '').strip()
                if seed and seed.isdigit():
                    reg.seed = int(seed)
                    reg.save(update_fields=['seed'])

                results['imported'] += 1

            except Exception as exc:
                results['errors'].append(f'Row {row_num}: {str(exc)}')
                results['skipped'] += 1

        results['total'] = results['imported'] + results['skipped']
        if results['imported'] > 0:
            bump_toc_scopes(self.tournament.id, 'participants', 'participants_adv', 'overview', 'analytics')
        return Response(results)


class SystemChecksView(TOCBaseView):
    """
    GET /api/toc/<slug>/participants/system-checks/
    Run automated verification checks across all registrations.
    Returns per-registration flags + summary.
    """

    def get(self, request, slug):
        cache_bucket = int(timezone.now().timestamp() // 20)
        cache_key = toc_cache_key('participants', self.tournament.id, 'system_checks', cache_bucket)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        data = TOCParticipantService.get_system_checks(self.tournament)
        cache.set(cache_key, data, timeout=25)
        return Response(data)

