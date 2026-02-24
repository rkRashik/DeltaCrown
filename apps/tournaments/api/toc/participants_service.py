"""
TOC Service Layer — Participant Grid & Registration Ops.

Wraps existing RegistrationService, CheckinService, and
RegistrationVerificationService for the TOC Participants tab.

Sprint 2: S2-S1 (service wrappers), S2-S2 (filtering/ordering)
PRD: §3.1–§3.9
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, CharField, F, Q, Value, When
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone

from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.payment_verification import PaymentVerification
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.registration_service import RegistrationService
from apps.tournaments.services.checkin_service import CheckinService

logger = logging.getLogger(__name__)


class TOCParticipantService:
    """
    High-level service for the Participants tab.

    All methods are @classmethod. Returns plain dicts — no model leaking.
    """

    # ── Page size ─────────────────────────────────────────────────────
    PAGE_SIZE = 50

    # ── Status groups for quick-filter presets ────────────────────────
    STATUS_ACTIVE = [
        Registration.CONFIRMED,
        Registration.AUTO_APPROVED,
        Registration.PAYMENT_SUBMITTED,
    ]
    STATUS_PENDING = [
        Registration.PENDING,
        Registration.NEEDS_REVIEW,
        Registration.SUBMITTED,
    ]
    STATUS_INACTIVE = [
        Registration.REJECTED,
        Registration.CANCELLED,
        Registration.NO_SHOW,
    ]

    # ── S2-S2: Filtered / Ordered Queryset ────────────────────────────

    @classmethod
    def get_participant_list(
        cls,
        tournament: Tournament,
        *,
        page: int = 1,
        status: Optional[str] = None,
        payment: Optional[str] = None,
        checkin: Optional[str] = None,
        search: Optional[str] = None,
        ordering: str = '-registered_at',
    ) -> Dict[str, Any]:
        """
        Return paginated, filtered participant list.

        Filters:
            status  — exact status value OR 'active'/'pending'/'inactive' preset
            payment — 'verified'/'pending'/'none'
            checkin — 'yes'/'no'
            search  — searches team name (registration_data), username, reg number

        Ordering:
            Any Registration field prefixed with - for descending.
            Default: -registered_at (newest first)

        Returns: {results: [...], total, page, pages, page_size}
        """
        qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).select_related('user').prefetch_related('payment_verification')

        # ── Status filter ──
        if status:
            if status == 'active':
                qs = qs.filter(status__in=cls.STATUS_ACTIVE)
            elif status == 'pending':
                qs = qs.filter(status__in=cls.STATUS_PENDING)
            elif status == 'inactive':
                qs = qs.filter(status__in=cls.STATUS_INACTIVE)
            elif status == 'waitlisted':
                qs = qs.filter(status=Registration.WAITLISTED)
            else:
                qs = qs.filter(status=status)

        # ── Payment filter ──
        if payment == 'verified':
            qs = qs.filter(
                payment_verification__status=PaymentVerification.Status.VERIFIED,
            )
        elif payment == 'pending':
            qs = qs.filter(
                payment_verification__status=PaymentVerification.Status.PENDING,
            )
        elif payment == 'none':
            qs = qs.filter(payment_verification__isnull=True)

        # ── Check-in filter ──
        if checkin == 'yes':
            qs = qs.filter(checked_in=True)
        elif checkin == 'no':
            qs = qs.filter(checked_in=False)

        # ── Search (team name in registration_data, username, reg number) ──
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(user__username__icontains=search)
                | Q(registration_number__icontains=search)
                | Q(registration_data__team_name__icontains=search)
                | Q(registration_data__guest_team__team_name__icontains=search)
            )

        # ── Ordering ──
        allowed_orderings = {
            'registered_at', '-registered_at',
            'status', '-status',
            'seed', '-seed',
            'slot_number', '-slot_number',
            'checked_in', '-checked_in',
            'user__username', '-user__username',
        }
        if ordering not in allowed_orderings:
            ordering = '-registered_at'
        qs = qs.order_by(ordering)

        # ── Pagination ──
        total = qs.count()
        pages = max(1, (total + cls.PAGE_SIZE - 1) // cls.PAGE_SIZE)
        page = max(1, min(page, pages))
        offset = (page - 1) * cls.PAGE_SIZE
        registrations = qs[offset:offset + cls.PAGE_SIZE]

        results = [cls._serialize_participant_row(r) for r in registrations]

        return {
            'results': results,
            'total': total,
            'page': page,
            'pages': pages,
            'page_size': cls.PAGE_SIZE,
        }

    @classmethod
    def get_participant_detail(
        cls, tournament: Tournament, registration_id: int
    ) -> Dict[str, Any]:
        """
        Return full participant detail for the drawer.

        Includes registration data, payment info, verification status,
        lineup/roster, audit timestamps.
        """
        try:
            reg = Registration.objects.select_related('user').prefetch_related(
                'payment_verification',
            ).get(
                id=registration_id,
                tournament=tournament,
                is_deleted=False,
            )
        except Registration.DoesNotExist:
            raise ValidationError("Registration not found.")

        # Payment info
        payment_info = cls._get_payment_info(reg)

        return {
            'id': reg.id,
            'registration_number': reg.registration_number or '',
            'participant_name': cls._participant_name(reg),
            'user_id': reg.user_id,
            'username': reg.user.username if reg.user else None,
            'team_id': reg.team_id,
            'status': reg.status,
            'status_display': reg.get_status_display(),
            'registered_at': reg.registered_at.isoformat() if reg.registered_at else None,
            'checked_in': reg.checked_in,
            'checked_in_at': reg.checked_in_at.isoformat() if reg.checked_in_at else None,
            'seed': reg.seed,
            'slot_number': reg.slot_number,
            'waitlist_position': reg.waitlist_position,
            'is_guest_team': reg.is_guest_team,
            'completion_percentage': float(reg.completion_percentage),
            'registration_data': reg.registration_data or {},
            'lineup_snapshot': reg.lineup_snapshot or [],
            'payment': payment_info,
            'created_at': reg.created_at.isoformat() if reg.created_at else None,
            'updated_at': reg.updated_at.isoformat() if reg.updated_at else None,
        }

    # ── S2-S1: Action Wrappers ────────────────────────────────────────

    @classmethod
    def approve_registration(
        cls, tournament: Tournament, registration_id: int, actor
    ) -> Dict[str, Any]:
        """Approve a pending registration via RegistrationService."""
        reg = cls._get_registration(tournament, registration_id)
        RegistrationService.approve_registration(
            registration_id=reg.id,
            organizer=actor,
        )
        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def reject_registration(
        cls, tournament: Tournament, registration_id: int, actor, reason: str = ''
    ) -> Dict[str, Any]:
        """Reject a registration with optional reason."""
        reg = cls._get_registration(tournament, registration_id)
        RegistrationService.reject_registration(
            registration_id=reg.id,
            organizer=actor,
            reason=reason,
        )
        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def disqualify_registration(
        cls, tournament: Tournament, registration_id: int, actor,
        reason: str = '', evidence: str = ''
    ) -> Dict[str, Any]:
        """Disqualify a confirmed registration."""
        reg = cls._get_registration(tournament, registration_id)
        RegistrationService.disqualify_registration(
            registration_id=reg.id,
            actor=actor,
            reason=reason,
        )
        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def verify_payment(
        cls, tournament: Tournament, registration_id: int, actor
    ) -> Dict[str, Any]:
        """Manually verify a payment."""
        reg = cls._get_registration(tournament, registration_id)
        RegistrationService.verify_payment(
            registration_id=reg.id,
            admin=actor,
            reason='Verified via TOC',
        )
        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def toggle_checkin(
        cls, tournament: Tournament, registration_id: int, actor
    ) -> Dict[str, Any]:
        """Toggle check-in status (organizer override)."""
        reg = cls._get_registration(tournament, registration_id)
        CheckinService.organizer_toggle_checkin(
            registration=reg,
            actor=actor,
        )
        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def bulk_action(
        cls,
        tournament: Tournament,
        action: str,
        registration_ids: List[int],
        actor,
        reason: str = '',
    ) -> Dict[str, Any]:
        """
        Bulk action on multiple registrations.

        Supported actions: approve, reject, disqualify, checkin
        Returns: {processed: int, errors: [...]}
        """
        valid_actions = {'approve', 'reject', 'disqualify', 'checkin'}
        if action not in valid_actions:
            raise ValidationError(f"Invalid bulk action: {action}")

        # Validate all IDs belong to this tournament
        regs = Registration.objects.filter(
            id__in=registration_ids,
            tournament=tournament,
            is_deleted=False,
        )
        found_ids = set(regs.values_list('id', flat=True))
        missing = set(registration_ids) - found_ids
        if missing:
            raise ValidationError(f"Registrations not found: {missing}")

        processed = 0
        errors = []

        for reg_id in registration_ids:
            try:
                if action == 'approve':
                    cls.approve_registration(tournament, reg_id, actor)
                elif action == 'reject':
                    cls.reject_registration(tournament, reg_id, actor, reason)
                elif action == 'disqualify':
                    cls.disqualify_registration(tournament, reg_id, actor, reason)
                elif action == 'checkin':
                    cls.toggle_checkin(tournament, reg_id, actor)
                processed += 1
            except Exception as e:
                errors.append({'id': reg_id, 'error': str(e)})
                logger.warning(
                    "Bulk %s failed for registration %s: %s",
                    action, reg_id, e,
                )

        return {
            'action': action,
            'processed': processed,
            'errors': errors,
            'total_requested': len(registration_ids),
        }

    @classmethod
    def export_csv(cls, tournament: Tournament) -> str:
        """
        Export all participants as CSV string.

        Returns CSV text ready to be served as a file download.
        """
        qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).select_related('user').prefetch_related(
            'payment_verification',
        ).order_by('slot_number', 'registered_at')

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            'Reg #', 'Participant', 'Username', 'Team ID',
            'Status', 'Payment', 'Checked In', 'Seed',
            'Slot', 'Waitlist Pos', 'Guest Team',
            'Registered At', 'Game ID',
        ])

        for reg in qs:
            payment_status = cls._payment_status_label(reg)
            game_id = (reg.registration_data or {}).get('game_id', '')
            writer.writerow([
                reg.registration_number or '',
                cls._participant_name(reg),
                reg.user.username if reg.user else '',
                reg.team_id or '',
                reg.get_status_display(),
                payment_status,
                'Yes' if reg.checked_in else 'No',
                reg.seed or '',
                reg.slot_number or '',
                reg.waitlist_position or '',
                'Yes' if reg.is_guest_team else 'No',
                reg.registered_at.strftime('%Y-%m-%d %H:%M') if reg.registered_at else '',
                game_id,
            ])

        return output.getvalue()

    # ── Private Helpers ───────────────────────────────────────────────

    @classmethod
    def _get_registration(cls, tournament: Tournament, reg_id: int) -> Registration:
        """Fetch a single registration, validate it belongs to the tournament."""
        try:
            return Registration.objects.select_related('user').get(
                id=reg_id,
                tournament=tournament,
                is_deleted=False,
            )
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration {reg_id} not found in this tournament.")

    @classmethod
    def _serialize_participant_row(cls, reg: Registration) -> Dict[str, Any]:
        """Serialize a registration to a grid-row dict."""
        payment_status = cls._payment_status_label(reg)
        game_id = (reg.registration_data or {}).get('game_id', '')
        team_name = cls._participant_name(reg)

        return {
            'id': reg.id,
            'registration_number': reg.registration_number or '',
            'participant_name': team_name,
            'username': reg.user.username if reg.user else None,
            'team_id': reg.team_id,
            'status': reg.status,
            'status_display': reg.get_status_display(),
            'payment_status': payment_status,
            'checked_in': reg.checked_in,
            'seed': reg.seed,
            'slot_number': reg.slot_number,
            'waitlist_position': reg.waitlist_position,
            'is_guest_team': reg.is_guest_team,
            'game_id': game_id,
            'registered_at': reg.registered_at.isoformat() if reg.registered_at else None,
        }

    @classmethod
    def _participant_name(cls, reg: Registration) -> str:
        """Best-effort display name for a participant row."""
        data = reg.registration_data or {}
        # Check for team name in reg data
        team_name = data.get('team_name', '')
        if not team_name:
            guest = data.get('guest_team', {})
            if isinstance(guest, dict):
                team_name = guest.get('team_name', '')
        if team_name:
            return team_name
        # Fall back to username
        if reg.user:
            return reg.user.username
        return f"Registration #{reg.id}"

    @classmethod
    def _payment_status_label(cls, reg: Registration) -> str:
        """Get human-readable payment status for a registration."""
        try:
            pv = reg.payment_verification
            return pv.get_status_display() if pv else 'None'
        except Exception:
            return 'None'

    @classmethod
    def _get_payment_info(cls, reg: Registration) -> Optional[Dict[str, Any]]:
        """Full payment detail for the drawer."""
        try:
            pv = reg.payment_verification
        except Exception:
            pv = None

        if not pv:
            return None

        return {
            'status': pv.status,
            'status_display': pv.get_status_display(),
            'method': pv.method,
            'amount_bdt': str(pv.amount_bdt) if pv.amount_bdt else None,
            'transaction_id': pv.transaction_id or '',
            'payer_account_number': pv.payer_account_number or '',
            'reference_number': pv.reference_number or '',
            'proof_image': pv.proof_image.url if pv.proof_image else None,
            'verified_by': pv.verified_by.username if pv.verified_by_id else None,
            'verified_at': pv.verified_at.isoformat() if pv.verified_at else None,
            'reject_reason': pv.reject_reason or '',
            'created_at': pv.created_at.isoformat() if pv.created_at else None,
        }
