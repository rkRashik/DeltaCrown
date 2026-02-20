"""
P4-T02: Payment Deadline Auto-Expiry — Celery periodic task.

Runs every 15 minutes.  Finds registrations whose payment has status
``submitted`` and whose tournament's ``payment_deadline_hours`` has elapsed
since the payment was created.  Marks those payments as **expired**, cancels
the registration, and auto-promotes the next waitlisted participant.

Beat schedule entry registered in deltacrown/celery.py.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(
    name='apps.tournaments.tasks.expire_overdue_payments',
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    ignore_result=True,
)
def expire_overdue_payments(self):
    """
    Find ``Payment`` rows with status *submitted* whose deadline has passed
    and expire them.

    For each expired payment:
    1. Set payment.status = 'expired'
    2. Set registration.status = 'cancelled'
    3. Auto-promote next waitlisted registration (if any)

    Runs every 15 minutes via Celery Beat.
    """
    from apps.tournaments.models import Payment, Registration
    from apps.tournaments.models.tournament import Tournament

    now = timezone.now()
    expired_count = 0
    promoted_count = 0

    # Find tournaments with a payment deadline configured
    tournaments_with_deadline = Tournament.objects.filter(
        has_entry_fee=True,
        payment_deadline_hours__gt=0,
    ).values_list('id', 'payment_deadline_hours')

    for tournament_id, deadline_hours in tournaments_with_deadline:
        cutoff = now - timedelta(hours=deadline_hours)

        overdue_payments = Payment.objects.filter(
            registration__tournament_id=tournament_id,
            status=Payment.SUBMITTED,
            submitted_at__lt=cutoff,
        ).select_related('registration', 'registration__tournament')

        for payment in overdue_payments:
            try:
                with transaction.atomic():
                    # 1. Expire the payment
                    payment.status = Payment.EXPIRED
                    payment.notes = payment.notes if isinstance(payment.notes, dict) else {}
                    payment.notes['expired_by'] = 'system_auto_expiry'
                    payment.notes['expired_at'] = now.isoformat()
                    payment.notes['deadline_hours'] = deadline_hours
                    payment.last_action_reason = (
                        f'Auto-expired: payment not verified within {deadline_hours}h'
                    )
                    payment.save(update_fields=[
                        'status', 'notes', 'last_action_reason', 'updated_at',
                    ])

                    # Dual-write
                    from apps.tournaments.services.payment_service import (
                        _sync_to_payment_verification,
                    )
                    _sync_to_payment_verification(payment)

                    # 2. Cancel the registration
                    reg = payment.registration
                    reg.status = Registration.CANCELLED
                    reg.save(update_fields=['status', 'updated_at'])

                    expired_count += 1

                    # 3. Auto-promote next waitlisted participant
                    promoted = _promote_next_waitlisted(reg.tournament)
                    if promoted:
                        promoted_count += 1

                    logger.info(
                        "[expire_overdue] Expired payment %s for reg %s "
                        "(tournament %s)",
                        payment.id, reg.id, tournament_id,
                    )
            except Exception:
                logger.exception(
                    "[expire_overdue] Failed to expire payment %s", payment.id,
                )

    if expired_count:
        logger.info(
            "[expire_overdue] Expired %d payment(s), promoted %d waitlisted.",
            expired_count, promoted_count,
        )

    return {'expired': expired_count, 'promoted': promoted_count}


def _promote_next_waitlisted(tournament) -> bool:
    """Promote the next waitlisted registration to ``pending`` (or ``confirmed``
    for free tournaments).  Returns True if a promotion happened."""
    from apps.tournaments.models import Registration

    next_in_line = (
        Registration.objects
        .filter(
            tournament=tournament,
            status=Registration.WAITLISTED,
            is_deleted=False,
        )
        .order_by('waitlist_position', 'created_at')
        .select_for_update()
        .first()
    )

    if not next_in_line:
        return False

    if tournament.has_entry_fee:
        # Move to pending — they still need to pay
        next_in_line.status = Registration.PENDING
    else:
        next_in_line.status = Registration.CONFIRMED

    next_in_line.waitlist_position = None
    next_in_line.save(update_fields=['status', 'waitlist_position', 'updated_at'])

    logger.info(
        "[waitlist_promote] Promoted reg %s to %s (tournament %s)",
        next_in_line.id, next_in_line.status, tournament.id,
    )
    return True
