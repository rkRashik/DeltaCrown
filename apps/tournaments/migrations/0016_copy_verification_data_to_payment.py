"""
P4-T03 Step 2: Data migration — copy PaymentVerification fields to Payment.

For each PaymentVerification row, copies payer_account_number, amount_bdt,
note, proof_image, notes, idempotency_key, rejected_by, rejected_at,
refunded_by, refunded_at, reject_reason, last_action_reason into the
matching Payment row (matched by registration_id).

Reverse: clears the copied fields back to defaults.
"""

from django.db import migrations


def copy_verification_to_payment(apps, schema_editor):
    """Copy data from PaymentVerification → Payment (joined by registration_id)."""
    PaymentVerification = apps.get_model('tournaments', 'PaymentVerification')
    Payment = apps.get_model('tournaments', 'Payment')

    verifications = PaymentVerification.objects.select_related().all()
    updated = 0

    for pv in verifications.iterator(chunk_size=500):
        try:
            payment = Payment.objects.get(registration_id=pv.registration_id)
        except Payment.DoesNotExist:
            continue

        payment.payer_account_number = pv.payer_account_number or ''
        payment.amount_bdt = pv.amount_bdt
        payment.note = pv.note or ''
        if pv.proof_image:
            payment.proof_image = pv.proof_image
        payment.notes = pv.notes or {}
        # Only copy idempotency_key if Payment doesn't already have one
        if not payment.idempotency_key and pv.idempotency_key:
            payment.idempotency_key = pv.idempotency_key
        payment.rejected_by_id = pv.rejected_by_id
        payment.rejected_at = pv.rejected_at
        payment.refunded_by_id = pv.refunded_by_id
        payment.refunded_at = pv.refunded_at
        payment.reject_reason = pv.reject_reason or ''
        payment.last_action_reason = pv.last_action_reason or ''

        payment.save(update_fields=[
            'payer_account_number', 'amount_bdt', 'note', 'proof_image',
            'notes', 'idempotency_key', 'rejected_by_id', 'rejected_at',
            'refunded_by_id', 'refunded_at', 'reject_reason', 'last_action_reason',
        ])
        updated += 1

    if updated:
        print(f"\n  Copied {updated} PaymentVerification records to Payment.")


def clear_copied_fields(apps, schema_editor):
    """Reverse: clear the copied verification fields from Payment."""
    Payment = apps.get_model('tournaments', 'Payment')
    Payment.objects.all().update(
        payer_account_number='',
        amount_bdt=None,
        note='',
        proof_image='',
        notes={},
        rejected_by=None,
        rejected_at=None,
        refunded_by=None,
        refunded_at=None,
        reject_reason='',
        last_action_reason='',
        # Note: idempotency_key NOT cleared — Payment may have its own
    )


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0015_add_payment_consolidation_fields'),
    ]

    operations = [
        migrations.RunPython(
            copy_verification_to_payment,
            reverse_code=clear_copied_fields,
        ),
    ]
