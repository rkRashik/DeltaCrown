"""
TOC Sprint 11 — Audit Log & Real-Time API Views
=================================================
S11-B2  Audit log endpoint
"""

from django.db import transaction
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from apps.tournaments.models.registration import Registration

from .base import TOCBaseView
from .audit_service import TOCAuditService


class AuditLogView(TOCBaseView):
    """GET — filterable audit log for this tournament."""

    def get(self, request, slug):
        can_view_logs = (
            request.user.is_superuser
            or request.user.is_staff
            or self.tournament.organizer_id == request.user.id
        )
        if not can_view_logs:
            raise PermissionDenied('You do not have access to logs for this tournament.')

        svc = TOCAuditService(self.tournament)
        filters = {
            "action": request.query_params.get("action"),
            "user_id": request.query_params.get("user_id"),
            "tab": request.query_params.get("tab"),
            "since": request.query_params.get("since"),
            "limit": request.query_params.get("limit", 100),
        }
        rows = svc.get_audit_log(filters)
        include_summary = str(request.query_params.get('include_summary', '')).lower() in {'1', 'true', 'yes'}
        if not include_summary:
            return Response(rows)

        return Response(
            {
                'rows': rows,
                'anomaly_summary': svc.get_anomaly_summary(),
            }
        )


class CapacityOverflowRepairView(TOCBaseView):
    """POST — dry-run/apply safe repair for over-cap active registrations."""

    ACTIVE_STATUSES = (
        Registration.PENDING,
        Registration.PAYMENT_SUBMITTED,
        Registration.CONFIRMED,
    )

    def post(self, request, slug):
        can_view_logs = (
            request.user.is_superuser
            or request.user.is_staff
            or self.tournament.organizer_id == request.user.id
        )
        if not can_view_logs:
            raise PermissionDenied('You do not have access to this operation.')

        apply_fix = bool(request.data.get('apply', False))
        reason = (request.data.get('reason') or '').strip() or 'Restored disqualification after accidental reactivation.'

        active_qs = Registration.objects.filter(
            tournament=self.tournament,
            is_deleted=False,
            status__in=self.ACTIVE_STATUSES,
        )
        active_count = active_qs.count()
        max_participants = int(getattr(self.tournament, 'max_participants', 0) or 0)
        overflow = max(0, active_count - max_participants)

        if max_participants <= 0:
            return Response({
                'ok': False,
                'applied': False,
                'overflow': 0,
                'message': 'Tournament has no positive capacity configured.',
                'candidates': [],
            }, status=400)

        candidates = self._find_safe_candidates(overflow)
        payload = {
            'ok': True,
            'applied': False,
            'overflow': overflow,
            'active_count': active_count,
            'before_active_count': active_count,
            'max_participants': max_participants,
            'safe_candidate_count': len(candidates),
            'candidates': [
                {
                    'id': r.id,
                    'username': r.user.username if r.user else None,
                    'status': r.status,
                }
                for r in candidates
            ],
        }
        planned = candidates[:overflow] if overflow > 0 else []
        payload['after_active_count'] = max(0, active_count - len(planned))
        payload['repaired_usernames'] = [
            r.user.username
            for r in planned
            if r.user and getattr(r.user, 'username', None)
        ]

        if overflow <= 0:
            payload['message'] = 'No capacity overflow detected.'
            return Response(payload)

        if len(candidates) < overflow:
            payload['ok'] = False
            payload['message'] = 'Not enough safe candidates found for auto-repair. Manual review required.'
            return Response(payload, status=400)

        if not apply_fix:
            payload['message'] = 'Dry-run complete. Re-run with apply=true to persist repair.'
            return Response(payload)

        with transaction.atomic():
            selected = candidates[:overflow]
            now_iso = timezone.now().isoformat()
            for reg in selected:
                data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
                data['disqualified_at'] = data.get('disqualified_at') or now_iso
                data['disqualified_by'] = data.get('disqualified_by') or 'toc-capacity-repair'
                data['disqualification_reason'] = reason
                data['capacity_repair'] = {
                    'at': now_iso,
                    'source': 'toc_logs_repair',
                    'by': request.user.username,
                }
                reg.status = Registration.REJECTED
                reg.checked_in = False
                reg.checked_in_at = None
                reg.checked_in_by = None
                reg.slot_number = None
                reg.waitlist_position = None
                reg.registration_data = data
                reg.save(update_fields=[
                    'status',
                    'checked_in',
                    'checked_in_at',
                    'checked_in_by',
                    'slot_number',
                    'waitlist_position',
                    'registration_data',
                    'updated_at',
                ])

        new_active = Registration.objects.filter(
            tournament=self.tournament,
            is_deleted=False,
            status__in=self.ACTIVE_STATUSES,
        ).count()

        payload['applied'] = True
        payload['repaired'] = overflow
        payload['new_active_count'] = new_active
        payload['after_active_count'] = new_active
        payload['repaired_usernames'] = [
            reg.user.username
            for reg in selected
            if reg.user and getattr(reg.user, 'username', None)
        ]
        payload['message'] = 'Capacity overflow repair applied.'
        return Response(payload)

    def _find_safe_candidates(self, overflow):
        if overflow <= 0:
            return []

        confirmed_regs = list(
            Registration.objects.filter(
                tournament=self.tournament,
                is_deleted=False,
                status=Registration.CONFIRMED,
            ).select_related('user').order_by('-updated_at', '-id')
        )

        suspicious = []
        for reg in confirmed_regs:
            data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
            has_disq_meta = bool(data.get('disqualified_at') or data.get('disqualification_reason'))
            was_rejected_before = bool(data.get('previous_status') == Registration.REJECTED)
            if has_disq_meta or was_rejected_before:
                suspicious.append(reg)
        return suspicious
