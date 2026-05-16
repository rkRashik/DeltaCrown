"""Missions service layer.

Responsibilities:
  * enroll(user, template) — atomic: lock entry fee + create ACTIVE row.
  * record_progress(enrollment, **counters) — verification-engine hook.
  * complete(enrollment) — payout reward + refund entry fee.
  * fail(enrollment) / expire(enrollment) / cancel(enrollment) — close entry fee.
  * void(enrollment, reason) — admin remediation, refund entry fee.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import transaction
from django.utils import timezone

from apps.common.validators import validate_payment_proof_upload
from apps.economy import escrow_service
from apps.economy.models import DeltaCrownWallet
from apps.economy.services import get_master_treasury

from .models import ContractEnrollment, ContractProofSubmission, ContractTemplate


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

#: Anti-whale ceiling: maximum DC a single Mission may charge for entry.
CONTRACT_ENTRY_FEE_CAP_DC: int = 1_000

#: Reward is paid from the platform treasury — fee is 0 here (no skim).
CONTRACT_PLATFORM_FEE_PCT: int = 0


def _wallet_for_user(user) -> DeltaCrownWallet:
    """Return the player's DeltaCrownWallet or raise ValidationError."""
    if user is None:
        raise ValidationError("Cannot resolve wallet: user is None.")
    profile = getattr(user, "profile", None) or getattr(user, "user_profile", None)
    if profile is None:
        raise ValidationError(
            f"User '{getattr(user, 'username', user)}' has no profile."
        )
    try:
        return DeltaCrownWallet.objects.get(profile=profile)
    except DeltaCrownWallet.DoesNotExist as exc:
        raise ValidationError(
            f"User '{user.username}' has no DeltaCoin wallet."
        ) from exc


# ─────────────────────────────────────────────────────────────────────────────
# Service
# ─────────────────────────────────────────────────────────────────────────────

class ContractService:
    """Lifecycle service for Missions."""

    # ── Enrollment ───────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def enroll(*, user, template: ContractTemplate) -> ContractEnrollment:
        """Enroll ``user`` in ``template``: lock entry fee, start clock."""
        if not template.is_currently_available:
            raise ValidationError("Mission template is not currently available.")
        if template.entry_fee_dc > CONTRACT_ENTRY_FEE_CAP_DC:
            raise ValidationError(
                f"Mission entry fee {template.entry_fee_dc} DC exceeds "
                f"the anti-whale cap of {CONTRACT_ENTRY_FEE_CAP_DC} DC."
            )

        # Block overlapping enrollments at the unique-constraint level too.
        if ContractEnrollment.objects.filter(
            user=user, template=template, status='ACTIVE'
        ).exists():
            raise ValidationError("You already have an active enrollment for this Mission.")

        deadline = timezone.now() + timedelta(hours=template.duration_hours)
        enrollment = ContractEnrollment.objects.create(
            user=user,
            template=template,
            deadline_at=deadline,
            status='ACTIVE',
            progress={},
        )

        # Lock the entry fee (skip if the template is free).
        if template.entry_fee_dc:
            wallet = _wallet_for_user(user)
            result = escrow_service.lock_funds(
                wallet,
                template.entry_fee_dc,
                reference_id=enrollment.contract_ref_id('entry'),
                actor=user,
                note=f"Mission {enrollment.reference_code} entry fee",
            )
            enrollment.escrow_lock_txn = result.transactions[0]
            enrollment.save(update_fields=['escrow_lock_txn'])

        logger.info(
            "Mission enrolled: %s by %s (template=%s, fee=%s DC)",
            enrollment.reference_code, user.username,
            template.title, template.entry_fee_dc,
        )
        return enrollment

    # ── Progress ─────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def record_progress(*, enrollment_id, progress: dict) -> ContractEnrollment:
        """Replace the enrollment's progress dict.  Caller computes verification."""
        enrollment = ContractEnrollment.objects.select_for_update().get(pk=enrollment_id)
        if enrollment.status != 'ACTIVE':
            raise ValidationError("Cannot record progress on a non-active enrollment.")
        enrollment.progress = progress or {}
        enrollment.save(update_fields=['progress'])
        return enrollment

    # ── Resolution ───────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def complete(*, enrollment_id, actor=None) -> ContractEnrollment:
        """Goal met: refund entry fee + pay reward."""
        enrollment = ContractEnrollment.objects.select_for_update().select_related('template').get(
            pk=enrollment_id
        )
        if enrollment.status != 'ACTIVE':
            raise ValidationError("Only active enrollments can complete.")
        wallet = _wallet_for_user(enrollment.user)
        template = enrollment.template

        # Refund the entry fee.
        if enrollment.escrow_lock_txn_id and template.entry_fee_dc:
            escrow_service.refund_funds(
                wallet,
                template.entry_fee_dc,
                reference_id=enrollment.contract_ref_id('entry'),
                actor=actor,
                note=f"Mission {enrollment.reference_code} entry-fee refund (success)",
            )

        # Pay the reward (no platform fee — comes from treasury).
        if template.reward_dc:
            payout = escrow_service.payout_winner(
                wallet,
                template.reward_dc,
                platform_fee_pct=CONTRACT_PLATFORM_FEE_PCT,
                reference_id=enrollment.contract_ref_id('reward'),
                actor=actor,
                note=f"Mission {enrollment.reference_code} reward",
            )
            enrollment.reward_payout_txn = payout.transactions[0]

        enrollment.status = 'COMPLETED'
        enrollment.closure_reason = 'COMPLETED'
        enrollment.resolved_at = timezone.now()
        enrollment.save(update_fields=[
            'status', 'closure_reason', 'resolved_at', 'reward_payout_txn',
        ])

        logger.info(
            "Mission completed: %s (reward=%s DC)",
            enrollment.reference_code, template.reward_dc,
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def fail(*, enrollment_id, reason='FAILED', note='', actor=None) -> ContractEnrollment:
        """Goal not met: forfeit entry fee to platform treasury."""
        enrollment = ContractEnrollment.objects.select_for_update().select_related('template').get(
            pk=enrollment_id
        )
        if enrollment.status != 'ACTIVE':
            raise ValidationError("Only active enrollments can fail.")
        if reason not in ('FAILED', 'EXPIRED', 'CANCELLED'):
            raise ValidationError(f"Invalid fail reason: {reason}")

        template = enrollment.template
        if enrollment.escrow_lock_txn_id and template.entry_fee_dc:
            treasury = get_master_treasury()
            escrow_service.payout_winner(
                treasury,
                template.entry_fee_dc,
                platform_fee_pct=0,
                reference_id=enrollment.contract_ref_id('forfeit'),
                actor=actor,
                note=f"Mission {enrollment.reference_code} entry forfeited ({reason})",
            )

        # Map reason → terminal status
        terminal_map = {'FAILED': 'FAILED', 'EXPIRED': 'EXPIRED', 'CANCELLED': 'CANCELLED'}
        enrollment.status = terminal_map[reason]
        enrollment.closure_reason = reason
        enrollment.closure_note = note or ''
        enrollment.resolved_at = timezone.now()
        enrollment.save(update_fields=[
            'status', 'closure_reason', 'closure_note', 'resolved_at',
        ])

        logger.info(
            "Mission %s: %s (reason=%s)",
            enrollment.status.lower(), enrollment.reference_code, reason,
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def void(*, enrollment_id, actor=None, note='') -> ContractEnrollment:
        """Admin remediation: refund the entry fee."""
        enrollment = ContractEnrollment.objects.select_for_update().select_related('template').get(
            pk=enrollment_id
        )
        if enrollment.status != 'ACTIVE':
            raise ValidationError("Only active enrollments can be voided.")

        template = enrollment.template
        if enrollment.escrow_lock_txn_id and template.entry_fee_dc:
            wallet = _wallet_for_user(enrollment.user)
            escrow_service.refund_funds(
                wallet,
                template.entry_fee_dc,
                reference_id=enrollment.contract_ref_id('entry'),
                actor=actor,
                note=f"Mission {enrollment.reference_code} voided by admin",
            )

        enrollment.status = 'VOIDED'
        enrollment.closure_reason = 'VOIDED'
        enrollment.closure_note = note or ''
        enrollment.resolved_at = timezone.now()
        enrollment.save(update_fields=[
            'status', 'closure_reason', 'closure_note', 'resolved_at',
        ])
        logger.info("Mission voided: %s", enrollment.reference_code)
        return enrollment

    # ── Admin/operator wrappers ─────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def admin_complete(*, enrollment_id, actor=None, note='') -> ContractEnrollment:
        """Complete a Mission through the normal reward/refund service path."""
        enrollment = ContractService.complete(enrollment_id=enrollment_id, actor=actor)
        if note:
            enrollment.closure_note = note
            enrollment.save(update_fields=['closure_note'])
        ContractService._log_mission_admin_action(
            'mission.admin_completed',
            enrollment,
            actor=actor,
            note=note,
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def admin_fail(*, enrollment_id, actor=None, note='') -> ContractEnrollment:
        """Fail a Mission through the normal entry-fee forfeit path."""
        enrollment = ContractService.fail(
            enrollment_id=enrollment_id,
            reason='FAILED',
            note=note,
            actor=actor,
        )
        ContractService._log_mission_admin_action(
            'mission.admin_failed',
            enrollment,
            actor=actor,
            note=note,
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def admin_void_refund(*, enrollment_id, actor=None, note='') -> ContractEnrollment:
        """Void/refund a Mission through the normal remediation path."""
        enrollment = ContractService.void(
            enrollment_id=enrollment_id,
            actor=actor,
            note=note,
        )
        ContractService._log_mission_admin_action(
            'mission.admin_void_refund',
            enrollment,
            actor=actor,
            note=note,
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def admin_expire(*, enrollment_id, actor=None, note='') -> ContractEnrollment:
        """Expire a selected overdue Mission."""
        enrollment = ContractEnrollment.objects.select_for_update().get(pk=enrollment_id)
        if enrollment.status != 'ACTIVE':
            raise ValidationError("Only active Missions can be expired.")
        if enrollment.deadline_at >= timezone.now():
            raise ValidationError("Only overdue Missions can be expired.")

        enrollment = ContractService.fail(
            enrollment_id=enrollment_id,
            reason='EXPIRED',
            note=note or 'Deadline passed without completion.',
            actor=actor,
        )
        ContractService._log_mission_admin_action(
            'mission.admin_expired',
            enrollment,
            actor=actor,
            note=note,
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def admin_record_progress(*, enrollment_id, actor=None, progress_patch=None, note='') -> ContractEnrollment:
        """Record a minimal manual review marker in the Mission progress JSON."""
        enrollment = ContractEnrollment.objects.select_for_update().get(pk=enrollment_id)
        if enrollment.status != 'ACTIVE':
            raise ValidationError("Cannot record progress on a non-active Mission.")
        progress = dict(enrollment.progress or {})
        manual_reviews = list(progress.get('manual_reviews') or [])
        manual_reviews.append({
            'reviewed_at': timezone.now().isoformat(),
            'reviewed_by_id': getattr(actor, 'pk', None),
            'note': note,
        })
        progress['manual_reviews'] = manual_reviews
        if progress_patch:
            progress.update(progress_patch)
        enrollment.progress = progress
        enrollment.save(update_fields=['progress'])
        ContractService._log_mission_admin_action(
            'mission.progress_recorded',
            enrollment,
            actor=actor,
            note=note,
        )
        return enrollment

    @staticmethod
    @transaction.atomic
    def submit_proof(
        *,
        enrollment_id,
        user,
        proof_url: str = '',
        notes: str = '',
        proof_file=None,
    ) -> ContractProofSubmission:
        """Submit Mission proof for manual review without resolving rewards."""
        enrollment = ContractEnrollment.objects.select_for_update().get(pk=enrollment_id)
        if enrollment.user_id != getattr(user, 'id', None):
            raise ValidationError("Not allowed to submit proof for this Mission.")
        if enrollment.status != 'ACTIVE':
            raise ValidationError("Proof can only be submitted for active Missions.")
        proof_url = (proof_url or '').strip()
        if not proof_url and not proof_file:
            raise ValidationError("Proof URL or proof file is required.")
        if proof_url:
            URLValidator()(proof_url)
        if proof_file:
            validate_payment_proof_upload(proof_file)
        pending_exists = ContractProofSubmission.objects.filter(
            enrollment=enrollment,
            status='PENDING_REVIEW',
        ).exists()
        if pending_exists:
            raise ValidationError("A proof submission is already waiting for review.")

        proof_kwargs = {
            'enrollment': enrollment,
            'submitted_by': user,
            'proof_url': proof_url,
            'notes': (notes or '').strip(),
        }
        if proof_file:
            proof_kwargs['proof_file'] = proof_file
        proof = ContractProofSubmission.objects.create(**proof_kwargs)
        ContractService._log_mission_admin_action(
            'mission.proof_submitted',
            enrollment,
            actor=user,
            note='Mission proof submitted.',
            extra={'proof_id': str(proof.pk)},
        )
        return proof

    @staticmethod
    @transaction.atomic
    def review_proof(*, proof_id, actor, decision: str, note: str = '') -> ContractProofSubmission:
        """Accept/reject Mission proof without auto-completing the Mission."""
        proof = (
            ContractProofSubmission.objects.select_for_update()
            .select_related('enrollment')
            .get(pk=proof_id)
        )
        if proof.status != 'PENDING_REVIEW':
            raise ValidationError("Only pending proof can be reviewed.")
        if decision not in {'ACCEPTED', 'REJECTED'}:
            raise ValidationError("Invalid proof review decision.")

        proof.status = decision
        proof.reviewed_by = actor
        proof.reviewed_at = timezone.now()
        proof.review_note = note or ''
        proof.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_at'])
        ContractService._log_mission_admin_action(
            'mission.proof_reviewed',
            proof.enrollment,
            actor=actor,
            note=note,
            extra={'proof_id': str(proof.pk), 'decision': decision},
        )
        return proof

    @staticmethod
    def _log_mission_admin_action(event_name, enrollment, *, actor=None, note='', extra=None):
        """Persist a lightweight Mission operator audit event without blocking the action."""
        try:
            from apps.common.events.models import EventLog

            EventLog.objects.create(
                name=event_name,
                payload={
                    'enrollment_id': str(enrollment.pk),
                    'reference_code': enrollment.reference_code,
                    'template_id': str(enrollment.template_id),
                    'status': enrollment.status,
                    'closure_reason': enrollment.closure_reason,
                    'note': note,
                    **(extra or {}),
                },
                occurred_at=timezone.now(),
                user_id=getattr(actor, 'pk', None),
                correlation_id=enrollment.reference_code,
                metadata={'source': 'contracts.admin'},
                status=EventLog.STATUS_PROCESSED,
            )
        except Exception:
            logger.exception(
                "Failed to write Mission admin audit event %s for %s",
                event_name,
                getattr(enrollment, 'reference_code', enrollment),
            )

    # ── Periodic deadline sweep ──────────────────────────────────────────

    @staticmethod
    def expire_overdue():
        """Sweep ACTIVE enrollments whose deadline has passed → EXPIRED.

        Per-row atomic so a single bad row doesn't block the rest.
        Called by a Celery beat task.
        """
        stale = ContractEnrollment.objects.filter(
            status='ACTIVE',
            deadline_at__lt=timezone.now(),
        ).only('id', 'reference_code')

        count = 0
        for stub in stale.iterator():
            try:
                ContractService.fail(
                    enrollment_id=stub.pk,
                    reason='EXPIRED',
                    note='Deadline passed without completion.',
                )
                count += 1
            except Exception:
                logger.exception(
                    "expire_overdue: failed on %s", stub.reference_code,
                )
        if count:
            logger.info("Expired %d Mission enrollments", count)
        return count
