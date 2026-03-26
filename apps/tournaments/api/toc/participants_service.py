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
import time
from typing import Any, Dict, List, Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Case, CharField, F, Q, Value, When
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone

from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.payment_verification import PaymentVerification
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.api.toc.notifications_service import TOCNotificationsService
from apps.tournaments.services.registration_service import RegistrationService
from apps.tournaments.services.checkin_service import CheckinService
from apps.tournaments.services.registration_verification import RegistrationVerificationService

try:
    from apps.organizations.models.team import Team as OrgTeam
except ImportError:
    OrgTeam = None

logger = logging.getLogger(__name__)


class TOCParticipantService:
    """
    High-level service for the Participants tab.

    All methods are @classmethod. Returns plain dicts — no model leaking.
    """

    # ── Page size ─────────────────────────────────────────────────────
    PAGE_SIZE = 50
    SLOW_LIST_MS = 180

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
        t0 = time.perf_counter()

        qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).select_related(
            'user',
            'user__profile',
            'payment_verification',
        ).only(
            'id',
            'registration_number',
            'team_id',
            'status',
            'checked_in',
            'seed',
            'slot_number',
            'waitlist_position',
            'is_guest_team',
            'registered_at',
            'registration_data',
            'lineup_snapshot',
            'user__id',
            'user__username',
            'user__profile__avatar',
            'payment_verification__id',
            'payment_verification__status',
            'payment_verification__transaction_id',
            'payment_verification__payer_account_number',
            'payment_verification__amount_bdt',
            'payment_verification__method',
            'payment_verification__proof_image',
        )
        t_base_qs = time.perf_counter()

        # Default operational view hides inactive/disqualified rows.
        if not status:
            qs = qs.exclude(status__in=cls.STATUS_INACTIVE)

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
                Q(payment_verification__status=PaymentVerification.Status.VERIFIED)
                | Q(
                    payment_verification__isnull=True,
                    payment__status__in=[Payment.VERIFIED, Payment.WAIVED],
                )
            )
        elif payment == 'pending':
            qs = qs.filter(
                Q(payment_verification__status=PaymentVerification.Status.PENDING)
                | Q(
                    payment_verification__isnull=True,
                    payment__status__in=[Payment.PENDING, Payment.SUBMITTED],
                )
            )
        elif payment == 'none':
            qs = qs.filter(
                payment_verification__isnull=True,
                payment__isnull=True,
            )

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
        t_filtered = time.perf_counter()

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
        t_ordered = time.perf_counter()

        # ── Pagination ──
        # Fast-path: for first page, avoid COUNT(*) when the full result fits one page.
        if page == 1:
            first_page_probe = list(qs[: cls.PAGE_SIZE + 1])
            if len(first_page_probe) <= cls.PAGE_SIZE:
                total = len(first_page_probe)
                pages = 1
                registrations = first_page_probe
            else:
                total = qs.count()
                pages = max(1, (total + cls.PAGE_SIZE - 1) // cls.PAGE_SIZE)
                registrations = first_page_probe[: cls.PAGE_SIZE]
        else:
            total = qs.count()
            pages = max(1, (total + cls.PAGE_SIZE - 1) // cls.PAGE_SIZE)
            page = min(page, pages)
            offset = (page - 1) * cls.PAGE_SIZE
            registrations = list(qs[offset:offset + cls.PAGE_SIZE])

        page = max(1, min(page, pages))
        t_paged = time.perf_counter()

        # Build bulk team cache for this page (avoids N+1 for team tournaments)
        team_cache = cls._build_team_cache(registrations)
        t_team_cache = time.perf_counter()

        # Build IGL user_id → game IGN map for team registrations (avoids N+1)
        user_ign_map = cls._build_igl_ign_map(registrations, tournament)
        t_ign_map = time.perf_counter()

        # Build Payment fallback map only for rows without PaymentVerification.
        needs_payment_fallback = any(
            getattr(r, 'payment_verification', None) is None
            for r in registrations
        )
        payment_map = cls._build_latest_payment_map(registrations) if needs_payment_fallback else {}
        t_enriched = time.perf_counter()

        results = [
            cls._serialize_participant_row(
                r,
                team_cache=team_cache,
                user_ign_map=user_ign_map,
                payment_map=payment_map,
            )
            for r in registrations
        ]
        t_serialized = time.perf_counter()

        total_ms = (t_serialized - t0) * 1000
        if total_ms >= cls.SLOW_LIST_MS:
            logger.info(
                "TOC participants list latency ms total=%.2f build_qs=%.2f filters=%.2f ordering=%.2f page_slice=%.2f enrich=%.2f serialize=%.2f page=%s total=%s search=%s status=%s payment=%s checkin=%s",
                total_ms,
                (t_base_qs - t0) * 1000,
                (t_filtered - t_base_qs) * 1000,
                (t_ordered - t_filtered) * 1000,
                (t_paged - t_ordered) * 1000,
                (t_enriched - t_paged) * 1000,
                (t_serialized - t_enriched) * 1000,
                page,
                total,
                bool(search),
                status or '',
                payment or '',
                checkin or '',
            )
            logger.info(
                "TOC participants enrich breakdown ms team_cache=%.2f ign_map=%.2f payment_map=%.2f fallback_needed=%s",
                (t_team_cache - t_paged) * 1000,
                (t_ign_map - t_team_cache) * 1000,
                (t_enriched - t_ign_map) * 1000,
                needs_payment_fallback,
            )

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
            reg = Registration.objects.select_related(
                'user',
                'user__profile',
                'payment_verification',
                'payment_verification__verified_by',
            ).get(
                id=registration_id,
                tournament=tournament,
                is_deleted=False,
            )
        except Registration.DoesNotExist:
            raise ValidationError("Registration not found.")

        # Payment info
        payment_info = cls._get_payment_info(reg)

        # ── Enrich lineup snapshot with GameProfile IGNs ──
        enriched_snapshot = cls._enrich_lineup_snapshot(reg, tournament)

        # ── Team metadata ──
        team_info = None
        team_slug = ''
        if reg.team_id and OrgTeam is not None:
            try:
                obj = OrgTeam.objects.filter(id=reg.team_id).only(
                    'id', 'name', 'tag', 'slug', 'logo', 'primary_color',
                    'discord_url', 'twitter_url', 'website_url',
                ).first()
                if obj:
                    logo_url = ''
                    try:
                        logo_url = obj.logo.url if obj.logo else ''
                    except Exception:
                        pass
                    team_info = {
                        'name': obj.name or '',
                        'tag': getattr(obj, 'tag', '') or '',
                        'slug': obj.slug or '',
                        'logo_url': logo_url,
                        'primary_color': getattr(obj, 'primary_color', '') or '',
                        'discord_url': getattr(obj, 'discord_url', '') or '',
                        'twitter_url': getattr(obj, 'twitter_url', '') or '',
                        'website_url': getattr(obj, 'website_url', '') or '',
                    }
                    team_slug = obj.slug or ''
            except Exception:
                pass

        # ── Coordinator / IGL info ──
        coordinator_info = cls._get_coordinator_info(reg, enriched_snapshot)

        # ── Communication channels from form config ──
        comm_channels = cls._get_communication_channels(tournament, reg)

        # ── Game metadata ──
        game_meta = cls._get_game_meta(tournament)
        reg_data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
        block_meta = reg_data.get('tournament_block') if isinstance(reg_data.get('tournament_block'), dict) else {}
        is_hard_blocked = bool(block_meta.get('active'))

        return {
            'id': reg.id,
            'registration_number': reg.registration_number or '',
            'participant_name': cls._participant_name(reg),
            'user_id': reg.user_id,
            'username': reg.user.username if reg.user else None,
            'profile_avatar_url': cls._user_avatar_url(reg.user),
            'team_id': reg.team_id,
            'team_info': team_info,
            'team_slug': team_slug,
            'status': reg.status,
            'status_display': reg.get_status_display(),
            'is_hard_blocked': is_hard_blocked,
            'hard_block_reason': block_meta.get('reason', '') if is_hard_blocked else '',
            'registered_at': reg.registered_at.isoformat() if reg.registered_at else None,
            'checked_in': reg.checked_in,
            'checked_in_at': reg.checked_in_at.isoformat() if reg.checked_in_at else None,
            'seed': reg.seed,
            'slot_number': reg.slot_number,
            'waitlist_position': reg.waitlist_position,
            'is_guest_team': reg.is_guest_team,
            'completion_percentage': float(reg.completion_percentage),
            'registration_data': reg.registration_data or {},
            'lineup_snapshot': enriched_snapshot,
            'coordinator': coordinator_info,
            'communication_channels': comm_channels,
            'game_meta': game_meta,
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
            registration=reg,
            approved_by=actor,
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
            registration=reg,
            rejected_by=actor,
        )
        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def disqualify_registration(
        cls, tournament: Tournament, registration_id: int, actor,
        reason: str = '', evidence: str = '', auto_refund: bool = False
    ) -> Dict[str, Any]:
        """Disqualify a confirmed registration. Optionally auto-refund payment."""
        reg = cls._get_registration(tournament, registration_id)
        RegistrationService.disqualify_registration(
            registration=reg,
            reason=reason,
            disqualified_by=actor,
            auto_refund=auto_refund,
        )
        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def verify_payment(
        cls, tournament: Tournament, registration_id: int, actor
    ) -> Dict[str, Any]:
        """Manually verify a payment."""
        reg = cls._get_registration(tournament, registration_id)
        # RegistrationService.verify_payment expects a Payment ID, not Registration ID
        try:
            payment = reg.payment
        except Payment.DoesNotExist:
            payment = None
        if not payment:
            raise ValidationError("No payment found for this registration.")
        RegistrationService.verify_payment(
            payment_id=payment.id,
            verified_by=actor,
            admin_notes='Verified via TOC',
        )

        # Sync PaymentVerification status so participants tab reflects change
        cls._sync_payment_verification(reg, "verified", actor)

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
    def hard_block_registration(
        cls,
        tournament: Tournament,
        registration_id: int,
        actor,
        *,
        reason: str,
        auto_refund: bool = False,
    ) -> Dict[str, Any]:
        """
        Permanently block this participant from re-registering in this tournament.

        Uses registration_data.tournament_block metadata so eligibility checks can
        deny future registration attempts for this participant scope.
        """
        reg = cls._get_registration(tournament, registration_id)
        if not reason or not reason.strip():
            raise ValidationError("A block reason is required.")

        # Ensure current registration is not active in the bracket flow.
        if reg.status not in [Registration.REJECTED, Registration.CANCELLED]:
            RegistrationService.disqualify_registration(
                registration=reg,
                reason=reason,
                disqualified_by=actor,
                auto_refund=auto_refund,
            )
            reg.refresh_from_db()
        elif auto_refund:
            try:
                payment = reg.payment
            except Payment.DoesNotExist:
                payment = None
            if payment and payment.status == Payment.VERIFIED:
                RegistrationService.refund_payment(
                    payment_id=payment.id,
                    refunded_by=actor,
                    reason=f'Auto-refund: hard-block — {reason}',
                )
                reg.refresh_from_db()

        data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
        data['tournament_block'] = {
            'active': True,
            'scope': 'team' if reg.team_id else 'user',
            'reason': reason.strip(),
            'blocked_at': timezone.now().isoformat(),
            'blocked_by': getattr(actor, 'username', str(actor)),
        }
        reg.registration_data = data
        reg.save(update_fields=['registration_data', 'updated_at'])

        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def unblock_registration(
        cls,
        tournament: Tournament,
        registration_id: int,
        actor,
        *,
        reason: str = '',
    ) -> Dict[str, Any]:
        """Lift a previously applied tournament-level hard block."""
        reg = cls._get_registration(tournament, registration_id)
        data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
        block = data.get('tournament_block') if isinstance(data.get('tournament_block'), dict) else {}
        if not block or not block.get('active'):
            raise ValidationError("This participant is not hard-blocked.")

        block['active'] = False
        block['unblocked_at'] = timezone.now().isoformat()
        block['unblocked_by'] = getattr(actor, 'username', str(actor))
        if reason:
            block['unblock_reason'] = reason.strip()
        data['tournament_block'] = block
        reg.registration_data = data
        reg.save(update_fields=['registration_data', 'updated_at'])

        reg.refresh_from_db()
        return cls._serialize_participant_row(reg)

    @classmethod
    def notify_participant(
        cls,
        tournament: Tournament,
        registration_id: int,
        actor,
        *,
        message: str,
        subject: str = '',
    ) -> Dict[str, Any]:
        """Send a direct TOC alert/message to a participant or team roster."""
        reg = cls._get_registration(tournament, registration_id)
        body = (message or '').strip()
        if not body:
            raise ValidationError("Message is required.")

        recipients = set()
        if reg.user_id:
            recipients.add(reg.user_id)
        for entry in (reg.lineup_snapshot or []):
            uid = entry.get('user_id') if isinstance(entry, dict) else None
            if uid:
                recipients.add(uid)

        if not recipients:
            raise ValidationError("No reachable participant accounts found for this registration.")

        notif = TOCNotificationsService.send_notification(
            tournament,
            {
                'subject': (subject or 'TOC Alert').strip(),
                'body': body,
                'target': sorted(recipients),
                'force_email': True,
            },
        )

        # Keep a minimal audit trace on the registration JSON blob.
        data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
        history = data.get('toc_alerts') if isinstance(data.get('toc_alerts'), list) else []
        history.append({
            'at': timezone.now().isoformat(),
            'by': getattr(actor, 'username', str(actor)),
            'subject': (subject or 'TOC Alert').strip(),
            'message': body,
            'recipient_count': notif.get('recipient_count', 0),
        })
        data['toc_alerts'] = history[-20:]
        reg.registration_data = data
        reg.save(update_fields=['registration_data', 'updated_at'])

        reg.refresh_from_db()
        return {
            'participant': cls._serialize_participant_row(reg),
            'recipient_count': notif.get('recipient_count', 0),
        }

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
        ).select_related('user')
        reg_map = {r.id: r for r in regs}
        found_ids = set(reg_map.keys())
        missing = set(registration_ids) - found_ids
        if missing:
            raise ValidationError(f"Registrations not found: {missing}")

        processed = 0
        errors = []

        for reg_id in registration_ids:
            try:
                reg = reg_map.get(reg_id)
                if not reg:
                    raise ValidationError(f"Registration {reg_id} not found in this tournament.")

                cls._perform_bulk_action_on_registration(
                    reg,
                    action=action,
                    actor=actor,
                    reason=reason,
                )
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
    def _perform_bulk_action_on_registration(
        cls,
        reg: Registration,
        *,
        action: str,
        actor,
        reason: str = '',
    ) -> None:
        """Execute a supported bulk action on a pre-fetched registration object."""
        if action == 'approve':
            RegistrationService.approve_registration(
                registration=reg,
                approved_by=actor,
            )
            return

        if action == 'reject':
            RegistrationService.reject_registration(
                registration=reg,
                rejected_by=actor,
            )
            return

        if action == 'disqualify':
            RegistrationService.disqualify_registration(
                registration=reg,
                reason=reason,
                disqualified_by=actor,
                auto_refund=False,
            )
            return

        if action == 'checkin':
            CheckinService.organizer_toggle_checkin(
                registration=reg,
                actor=actor,
            )
            return

        raise ValidationError(f"Invalid bulk action: {action}")

    # ── System Verification Checks ────────────────────────────────────

    @classmethod
    def get_system_checks(cls, tournament: Tournament) -> Dict[str, Any]:
        """
        Run RegistrationVerificationService and return per-registration flags.

        Returns: {flags: [...], summary: {...}, per_registration: {reg_id: [flags]}}
        """
        try:
            result = RegistrationVerificationService.verify_tournament(tournament)
            return result
        except Exception as e:
            logger.error("System checks failed for tournament %s: %s", tournament.id, e)
            return {
                'flags': [],
                'summary': {'critical': 0, 'warning': 0, 'info': 0, 'clean': 0, 'total_registrations': 0},
                'per_registration': {},
            }

    @classmethod
    def export_csv(cls, tournament: Tournament) -> str:
        """
        Export all participants as CSV string.

        Returns CSV text ready to be served as a file download.
        Includes registration form answers, payment transaction IDs,
        and phone/WhatsApp for LAN desk-check-ins.
        """
        qs = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).select_related(
            'user',
            'payment_verification',
        ).order_by('slot_number', 'registered_at')

        # Collect all unique registration_data keys across all rows
        reg_data_keys: list[str] = []
        all_regs = list(qs)
        seen_keys: set[str] = set()
        for reg in all_regs:
            for k in (reg.registration_data or {}).keys():
                if k not in seen_keys:
                    seen_keys.add(k)
                    reg_data_keys.append(k)

        output = io.StringIO()
        writer = csv.writer(output)

        # Header row — base fields + payment details + all registration form fields
        writer.writerow([
            'Reg #', 'Participant', 'Username', 'Team ID',
            'Status', 'Payment Status', 'Payment Method', 'Transaction ID',
            'Sender Phone', 'Amount (BDT)', 'Checked In', 'Seed',
            'Slot', 'Waitlist Pos', 'Guest Team',
            'Registered At', 'Game ID',
        ] + [k.replace('_', ' ').title() for k in reg_data_keys])

        payment_map = cls._build_latest_payment_map(all_regs)

        for reg in all_regs:
            payment_status = cls._payment_status_label(reg, payment_map=payment_map)
            game_id = (reg.registration_data or {}).get('game_id', '')
            reg_data = reg.registration_data or {}

            # Get payment details
            txn_id = ''
            sender_phone = ''
            pay_method = ''
            pay_amount = ''
            try:
                pv = reg.payment_verification
                if pv:
                    txn_id = pv.transaction_id or ''
                    sender_phone = pv.payer_account_number or ''
                    pay_method = pv.method or ''
                    pay_amount = str(pv.amount_bdt) if pv.amount_bdt else ''
            except Exception:
                pass
            # Fallback to Payment model
            if not txn_id:
                pay = payment_map.get(reg.id)
                if pay:
                    txn_id = pay.transaction_id or ''
                    sender_phone = getattr(pay, 'payer_account_number', '') or ''
                    pay_method = pay.payment_method or ''
                    pay_amount = str(pay.amount_bdt) if getattr(pay, 'amount_bdt', None) else str(pay.amount or '')

            # Base fields
            row = [
                reg.registration_number or '',
                cls._participant_name(reg),
                reg.user.username if reg.user else '',
                reg.team_id or '',
                reg.get_status_display(),
                payment_status,
                pay_method,
                txn_id,
                sender_phone,
                pay_amount,
                'Yes' if reg.checked_in else 'No',
                reg.seed or '',
                reg.slot_number or '',
                reg.waitlist_position or '',
                'Yes' if reg.is_guest_team else 'No',
                reg.registered_at.strftime('%Y-%m-%d %H:%M') if reg.registered_at else '',
                game_id,
            ]
            # Append all registration form answer values
            for k in reg_data_keys:
                val = reg_data.get(k, '')
                if isinstance(val, (dict, list)):
                    val = str(val)
                row.append(val)
            writer.writerow(row)

        return output.getvalue()

    # ── Private Helpers ───────────────────────────────────────────────

    @classmethod
    def _get_registration(cls, tournament: Tournament, reg_id: int) -> Registration:
        """Fetch a single registration, validate it belongs to the tournament."""
        try:
            return Registration.objects.select_related(
                'user',
                'user__profile',
                'payment_verification',
                'payment_verification__verified_by',
            ).get(
                id=reg_id,
                tournament=tournament,
                is_deleted=False,
            )
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration {reg_id} not found in this tournament.")

    @classmethod
    def _serialize_participant_row(
        cls,
        reg: Registration,
        team_cache: dict = None,
        user_ign_map: dict = None,
        payment_map: dict = None,
    ) -> Dict[str, Any]:
        """Serialize a registration to a grid-row dict."""
        payment_status = cls._payment_status_label(reg, payment_map=payment_map)
        reg_data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
        block_meta = reg_data.get('tournament_block') if isinstance(reg_data.get('tournament_block'), dict) else {}
        is_hard_blocked = bool(block_meta.get('active'))
        game_id = (reg.registration_data or {}).get('game_id', '')
        team_info = (team_cache or {}).get(reg.team_id) if reg.team_id else None
        team_name = cls._participant_name(reg, team_info=team_info)

        # For team registrations derive coordinator (IGL/captain) from lineup_snapshot
        coordinator = ''
        coordinator_game_id = ''
        if reg.team_id:
            snap = reg.lineup_snapshot or []
            captain = next(
                (e for e in snap if e.get('role') == 'OWNER' or e.get('is_igl') or e.get('is_tournament_captain')),
                snap[0] if snap else None,
            )
            if captain:
                coordinator = captain.get('display_name') or captain.get('username', '')
                # Look up IGL's game-specific IGN from pre-built map
                cap_uid = captain.get('user_id')
                if cap_uid and user_ign_map:
                    coordinator_game_id = user_ign_map.get(cap_uid, '')

        # Quick-review payment data (for inline expand)
        qr_payment = cls._get_quick_review_payment(reg, payment_map=payment_map)

        return {
            'id': reg.id,
            'registration_number': reg.registration_number or '',
            'participant_name': team_name,
            'team_name': team_info['name'] if team_info else '',
            'team_tag': team_info['tag'] if team_info else '',
            'team_logo_url': team_info.get('logo_url', '') if team_info else '',
            'profile_avatar_url': cls._user_avatar_url(reg.user),
            'coordinator': coordinator,
            'coordinator_game_id': coordinator_game_id,
            'username': reg.user.username if reg.user else None,
            'team_id': reg.team_id,
            'status': reg.status,
            'status_display': reg.get_status_display(),
            'is_hard_blocked': is_hard_blocked,
            'hard_block_reason': block_meta.get('reason', '') if is_hard_blocked else '',
            'payment_status': payment_status,
            'checked_in': reg.checked_in,
            'seed': reg.seed,
            'slot_number': reg.slot_number,
            'waitlist_position': reg.waitlist_position,
            'is_guest_team': reg.is_guest_team,
            'game_id': game_id,
            'registered_at': reg.registered_at.isoformat() if reg.registered_at else None,
            'quick_payment': qr_payment,
        }

    @classmethod
    def _get_quick_review_payment(
        cls,
        reg: Registration,
        payment_map: Optional[Dict[int, Payment]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Lightweight payment data for inline quick-review panel."""
        # Try PaymentVerification first
        try:
            pv = reg.payment_verification
            if pv:
                proof_url = None
                if pv.proof_image:
                    try:
                        proof_url = pv.proof_image.url
                    except (ValueError, AttributeError):
                        pass
                return {
                    'transaction_id': pv.transaction_id or '',
                    'payer_account_number': pv.payer_account_number or '',
                    'amount_bdt': str(pv.amount_bdt) if pv.amount_bdt else None,
                    'method': pv.method or '',
                    'proof_url': proof_url,
                }
        except Exception:
            pass

        # Fallback: Payment model
        payment = None
        if payment_map is not None:
            payment = payment_map.get(reg.id)
        if payment is None:
            try:
                payment = reg.payment
            except Payment.DoesNotExist:
                payment = None
        if not payment:
            return None

        proof_url = None
        try:
            if payment.payment_proof and hasattr(payment.payment_proof, 'url'):
                proof_url = payment.payment_proof.url
        except (ValueError, AttributeError):
            pass

        return {
            'transaction_id': payment.transaction_id or '',
            'payer_account_number': getattr(payment, 'payer_account_number', '') or '',
            'amount_bdt': str(payment.amount_bdt) if getattr(payment, 'amount_bdt', None) else str(payment.amount or ''),
            'method': payment.payment_method or '',
            'proof_url': proof_url,
        }

    @classmethod
    def _build_latest_payment_map(cls, registrations) -> Dict[int, Payment]:
        """Build {registration_id: Payment} map in one query for a registration batch."""
        reg_ids = [r.id for r in registrations if getattr(r, 'id', None)]
        if not reg_ids:
            return {}

        # Payment is OneToOne with Registration, so this returns at most one row per registration.
        payments = Payment.objects.filter(registration_id__in=reg_ids)
        return {payment.registration_id: payment for payment in payments}

    @classmethod
    def _enrich_lineup_snapshot(cls, reg: Registration, tournament: Tournament) -> List[Dict]:
        """Enrich lineup_snapshot entries with GameProfile IGNs and user profile URLs."""
        snapshot = reg.lineup_snapshot or []
        if not snapshot:
            return snapshot

        # Get game display name for GameProfile lookup
        game_dn = ""
        try:
            game_dn = getattr(tournament.game, "display_name", "") or ""
        except Exception:
            pass

        user_ids = [e.get("user_id") for e in snapshot if e.get("user_id")]
        # Batch-load GameProfile IGNs
        ign_map: Dict[int, str] = {}
        if game_dn and user_ids:
            try:
                from apps.user_profile.models import GameProfile
                for row in GameProfile.objects.filter(
                    game_display_name__iexact=game_dn,
                    user_id__in=user_ids,
                ).exclude(ign="").values("user_id", "ign"):
                    ign_map[row["user_id"]] = row["ign"]
            except Exception:
                pass

        # Batch-load user slugs for profile links
        slug_map: Dict[int, str] = {}
        if user_ids:
            try:
                from apps.user_profile.models import UserProfile
                for row in UserProfile.objects.filter(
                    user_id__in=user_ids
                ).values("user_id", "slug"):
                    if row.get("slug"):
                        slug_map[row["user_id"]] = row["slug"]
            except Exception:
                pass

        enriched = []
        for entry in snapshot:
            e = dict(entry)  # shallow copy
            uid = e.get("user_id")
            if uid:
                e["game_id"] = ign_map.get(uid, "")
                e["profile_slug"] = slug_map.get(uid, "")
            else:
                e.setdefault("game_id", "")
                e.setdefault("profile_slug", "")
            enriched.append(e)
        return enriched

    @classmethod
    def _get_coordinator_info(cls, reg: Registration, enriched_snapshot: List[Dict]) -> Dict[str, Any]:
        """Extract coordinator / IGL info from lineup snapshot."""
        snap = enriched_snapshot or []
        coordinator = {}
        for entry in snap:
            is_igl = (
                entry.get("role") == "OWNER"
                or bool(entry.get("is_igl"))
                or bool(entry.get("is_tournament_captain"))
            )
            if is_igl:
                coordinator = {
                    "user_id": entry.get("user_id"),
                    "display_name": entry.get("display_name") or entry.get("username", ""),
                    "game_id": entry.get("game_id", ""),
                    "role": "IGL / Captain",
                    "profile_slug": entry.get("profile_slug", ""),
                }
                break
        if not coordinator and snap:
            e = snap[0]
            coordinator = {
                "user_id": e.get("user_id"),
                "display_name": e.get("display_name") or e.get("username", ""),
                "game_id": e.get("game_id", ""),
                "role": "Coordinator",
                "profile_slug": e.get("profile_slug", ""),
            }
        return coordinator

    @classmethod
    def _get_communication_channels(cls, tournament: Tournament, reg: Registration) -> List[Dict]:
        """Get communication channel values for this registration.

        Pulls channel definitions from TournamentFormConfiguration and
        values from registration_data.
        """
        channels = []
        try:
            from apps.tournaments.models.form_configuration import TournamentFormConfiguration
            fc = TournamentFormConfiguration.objects.filter(tournament=tournament).first()
            if fc and fc.communication_channels:
                rd = reg.registration_data or {}
                comm_data = rd.get("communication_channels", {})
                for ch in fc.communication_channels:
                    key = ch.get("key", "")
                    channels.append({
                        "key": key,
                        "label": ch.get("label", key),
                        "icon": ch.get("icon", ""),
                        "value": comm_data.get(key, "") if isinstance(comm_data, dict) else "",
                    })
        except Exception:
            pass
        return channels

    @classmethod
    def _get_game_meta(cls, tournament: Tournament) -> Dict[str, Any]:
        """Return game metadata useful for display (label, placeholder, type)."""
        try:
            g = tournament.game
            return {
                "display_name": getattr(g, "display_name", "") or "",
                "game_id_label": getattr(g, "game_id_label", "Game ID") or "Game ID",
                "game_id_placeholder": getattr(g, "game_id_placeholder", "") or "",
                "game_type": getattr(g, "game_type", "") or "",
                "category": getattr(g, "category", "") or "",
            }
        except Exception:
            return {}

    @classmethod
    def _participant_name(cls, reg: Registration, team_info: dict = None) -> str:
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
        # Use pre-fetched org Team info (avoids extra query)
        if team_info and team_info.get('name'):
            return team_info['name']
        # Fallback DB lookup for org Team by team_id
        if reg.team_id and OrgTeam is not None:
            try:
                obj = OrgTeam.objects.filter(id=reg.team_id).values('name').first()
                if obj and obj.get('name'):
                    return obj['name']
            except Exception:
                pass
        # Fall back to username
        if reg.user:
            return reg.user.username
        return f"Registration #{reg.id}"

    @classmethod
    def _build_team_cache(cls, registrations) -> Dict[int, Any]:
        """
        Bulk-fetch org Team rows for a list of registrations and return
        a dict keyed by team_id ready to pass to _serialize_participant_row.
        """
        if OrgTeam is None:
            return {}
        team_ids = list({r.team_id for r in registrations if r.team_id})
        if not team_ids:
            return {}
        try:
            cache: Dict[int, Any] = {}
            for obj in OrgTeam.objects.filter(id__in=team_ids).select_related('organization').only(
                'id',
                'name',
                'tag',
                'logo',
                'organization__enforce_brand',
                'organization__logo',
            ):
                logo_url = ''
                try:
                    # Only use actual uploaded logos, not default placeholders
                    if obj.logo:
                        logo_url = obj.logo.url
                    elif obj.organization and getattr(obj.organization, 'enforce_brand', False) and getattr(obj.organization, 'logo', None):
                        logo_url = obj.organization.logo.url
                except (ValueError, Exception):
                    pass
                cache[obj.id] = {
                    'name': obj.name or '',
                    'tag': getattr(obj, 'tag', '') or '',
                    'logo_url': logo_url,
                }
            return cache
        except Exception:
            return {}

    @classmethod
    def _build_igl_ign_map(cls, registrations, tournament) -> Dict[int, str]:
        """
        Batch-load GameProfile IGNs for IGL/captain users in team registrations.
        Returns: {user_id: ign_string}
        """
        igl_user_ids = set()
        for reg in registrations:
            if not reg.team_id:
                continue
            snap = reg.lineup_snapshot or []
            captain = next(
                (e for e in snap if e.get('role') == 'OWNER' or e.get('is_igl') or e.get('is_tournament_captain')),
                snap[0] if snap else None,
            )
            if captain and captain.get('user_id'):
                igl_user_ids.add(captain['user_id'])

        if not igl_user_ids:
            return {}

        game_dn = ""
        game_id = None
        try:
            game_id = tournament.game_id
            game_dn = getattr(tournament.game, 'display_name', '') or ''
        except Exception:
            pass
        if not game_dn and not game_id:
            return {}

        try:
            from apps.user_profile.models import GameProfile
            ign_map = {}
            gp_qs = GameProfile.objects.filter(
                user_id__in=list(igl_user_ids),
            ).exclude(ign='')
            if game_id:
                gp_qs = gp_qs.filter(game_id=game_id)
            else:
                gp_qs = gp_qs.filter(game_display_name__iexact=game_dn)

            for row in gp_qs.values('user_id', 'ign'):
                ign_map[row['user_id']] = row['ign']
            return ign_map
        except Exception:
            return {}

    @classmethod
    def _user_avatar_url(cls, user) -> str:
        """Return uploaded user avatar URL when available."""
        if not user:
            return ''
        try:
            profile = getattr(user, 'profile', None)
            if profile and getattr(profile, 'avatar', None):
                return profile.avatar.url
        except Exception:
            return ''
        return ''

    @classmethod
    def _payment_status_label(
        cls,
        reg: Registration,
        payment_map: Optional[Dict[int, Payment]] = None,
    ) -> str:
        """Get human-readable payment status for a registration."""
        try:
            pv = reg.payment_verification
            if pv:
                return pv.get_status_display()
        except Exception:
            pass

        payment = None
        if payment_map is not None:
            payment = payment_map.get(reg.id)
        if payment is None:
            try:
                payment = reg.payment
            except Payment.DoesNotExist:
                payment = None

        if not payment:
            return 'None'

        status_value = ((getattr(payment, 'status', '') or '')).strip().lower()
        if status_value in {Payment.VERIFIED, Payment.WAIVED}:
            return 'Verified'
        if status_value in {Payment.PENDING, Payment.SUBMITTED}:
            return 'Pending'
        if status_value == Payment.REJECTED:
            return 'Rejected'

        try:
            return payment.get_status_display() if hasattr(payment, 'get_status_display') else 'None'
        except Exception:
            return 'None'

    @classmethod
    def _sync_payment_verification(cls, reg: Registration, new_status: str, actor=None) -> None:
        """Keep PaymentVerification.status in sync after a Payment action."""
        try:
            pv = reg.payment_verification
        except Exception:
            return
        update_fields = ["status"]
        pv.status = new_status
        if new_status == "verified" and actor:
            pv.verified_by = actor
            pv.verified_at = timezone.now()
            update_fields += ["verified_by", "verified_at"]
        elif new_status == "rejected" and actor:
            pv.rejected_by = actor
            pv.rejected_at = timezone.now()
            update_fields += ["rejected_by", "rejected_at"]
        pv.save(update_fields=update_fields)

    @classmethod
    def _get_payment_info(cls, reg: Registration) -> Optional[Dict[str, Any]]:
        """Full payment detail for the drawer.

        Tries PaymentVerification first, falls back to Payment model.
        """
        try:
            pv = reg.payment_verification
        except Exception:
            pv = None

        if pv:
            proof_url = None
            if pv.proof_image:
                try:
                    proof_url = pv.proof_image.url
                except (ValueError, AttributeError):
                    pass
            return {
                'status': pv.status,
                'status_display': pv.get_status_display(),
                'method': pv.method,
                'amount_bdt': str(pv.amount_bdt) if pv.amount_bdt else None,
                'transaction_id': pv.transaction_id or '',
                'payer_account_number': pv.payer_account_number or '',
                'reference_number': pv.reference_number or '',
                'proof_image': proof_url,
                'verified_by': pv.verified_by.username if pv.verified_by_id else None,
                'verified_at': pv.verified_at.isoformat() if pv.verified_at else None,
                'reject_reason': pv.reject_reason or '',
                'created_at': pv.created_at.isoformat() if pv.created_at else None,
            }

        # Fallback: use Payment model directly
        try:
            payment = reg.payment
        except Payment.DoesNotExist:
            payment = None
        if not payment:
            return None

        proof_url = None
        try:
            if payment.payment_proof and hasattr(payment.payment_proof, 'url'):
                proof_url = payment.payment_proof.url
        except (ValueError, AttributeError):
            pass

        return {
            'status': payment.status,
            'status_display': payment.get_status_display() if hasattr(payment, 'get_status_display') else payment.status,
            'method': payment.payment_method or '',
            'amount_bdt': str(payment.amount_bdt) if getattr(payment, 'amount_bdt', None) else str(payment.amount or ''),
            'transaction_id': payment.transaction_id or '',
            'payer_account_number': getattr(payment, 'payer_account_number', '') or '',
            'reference_number': getattr(payment, 'reference_number', '') or '',
            'proof_image': proof_url,
            'verified_by': payment.verified_by.username if payment.verified_by else None,
            'verified_at': payment.verified_at.isoformat() if payment.verified_at else None,
            'reject_reason': getattr(payment, 'reject_reason', '') or '',
            'submitted_at': payment.submitted_at.isoformat() if payment.submitted_at else None,
        }
