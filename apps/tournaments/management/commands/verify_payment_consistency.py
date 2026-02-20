"""
P4-T03 Step 3: Payment consistency monitoring command.

Compares Payment and PaymentVerification rows (joined by registration_id)
and reports any discrepancies. Run periodically until confidence is high
enough to drop the PaymentVerification table (Step 4).

Usage:
    python manage.py verify_payment_consistency
    python manage.py verify_payment_consistency --fix   # auto-fix Payment → PV
"""
import sys

from django.core.management.base import BaseCommand, CommandError

from apps.tournaments.models import Payment
from apps.tournaments.models.payment_verification import PaymentVerification


# Fields to compare (Payment field → PV field)
FIELD_MAP = {
    'transaction_id': 'transaction_id',
    'reference_number': 'reference_number',
    'payer_account_number': 'payer_account_number',
    'amount_bdt': 'amount_bdt',
    'note': 'note',
    'reject_reason': 'reject_reason',
    'last_action_reason': 'last_action_reason',
}

STATUS_MAP = {
    'pending': 'pending',
    'submitted': 'pending',
    'verified': 'verified',
    'rejected': 'rejected',
    'refunded': 'refunded',
    'expired': 'rejected',
}

FK_FIELDS = {
    'verified_by_id': 'verified_by_id',
    'rejected_by_id': 'rejected_by_id',
    'refunded_by_id': 'refunded_by_id',
}

DT_FIELDS = {
    'verified_at': 'verified_at',
    'rejected_at': 'rejected_at',
    'refunded_at': 'refunded_at',
}


class Command(BaseCommand):
    help = 'Compare Payment and PaymentVerification rows for discrepancies.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Auto-fix by copying Payment values to PaymentVerification.',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        payments = Payment.objects.all().select_related('registration')
        total = payments.count()
        discrepancies = 0
        missing_pv = 0
        missing_payment = 0
        fixed = 0

        self.stdout.write(f"Checking {total} Payment records...")

        for payment in payments.iterator(chunk_size=500):
            try:
                pv = PaymentVerification.objects.get(
                    registration_id=payment.registration_id
                )
            except PaymentVerification.DoesNotExist:
                missing_pv += 1
                continue

            diffs = []

            # Check status mapping
            expected_pv_status = STATUS_MAP.get(payment.status)
            if expected_pv_status and pv.status != expected_pv_status:
                diffs.append(f"status: Payment={payment.status} → PV={pv.status} (expected {expected_pv_status})")

            # Check text/int fields
            for p_field, pv_field in FIELD_MAP.items():
                p_val = getattr(payment, p_field, None) or ''
                pv_val = getattr(pv, pv_field, None) or ''
                if str(p_val) != str(pv_val):
                    diffs.append(f"{p_field}: Payment={p_val!r} vs PV={pv_val!r}")

            # Check FK fields
            for p_field, pv_field in FK_FIELDS.items():
                p_val = getattr(payment, p_field, None)
                pv_val = getattr(pv, pv_field, None)
                if p_val != pv_val:
                    diffs.append(f"{p_field}: Payment={p_val} vs PV={pv_val}")

            if diffs:
                discrepancies += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"  REG {payment.registration_id}: {len(diffs)} diff(s)"
                    )
                )
                for d in diffs:
                    self.stdout.write(f"    - {d}")

                if fix:
                    from apps.tournaments.services.payment_service import _sync_to_payment_verification
                    _sync_to_payment_verification(payment)
                    fixed += 1

        # Check for orphan PVs (have PV but no Payment)
        pv_only = PaymentVerification.objects.exclude(
            registration_id__in=Payment.objects.values_list('registration_id', flat=True)
        ).count()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"Total Payment rows:    {total}"))
        self.stdout.write(f"Missing PV:            {missing_pv}")
        self.stdout.write(f"Orphan PV (no Payment):{pv_only}")
        self.stdout.write(f"Discrepancies:         {discrepancies}")
        if fix:
            self.stdout.write(f"Auto-fixed:            {fixed}")

        if discrepancies == 0 and missing_pv == 0 and pv_only == 0:
            self.stdout.write(self.style.SUCCESS("✓ All records consistent!"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Discrepancies found."))
            if not fix:
                self.stdout.write("  Run with --fix to auto-repair.")
