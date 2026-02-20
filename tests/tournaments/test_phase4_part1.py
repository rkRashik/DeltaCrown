"""
Phase 4 Part 1 Tests.

Covers:
- P4-T01: DeltaCoin Payment Integration (balance check, atomic deduction, auto-verify, refund)
- P4-T02: Payment Deadline Auto-Expiry (Celery task, cancel, waitlist promotion)
- P4-T03: Payment Model Consolidation Steps 1-3 (new fields, dual-write, consistency)

Source: Documents/Registration_system/05_IMPLEMENTATION_TRACKER.md
"""

import pytest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction
from apps.games.models.game import Game
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.payment_verification import PaymentVerification
from apps.tournaments.services.payment_service import PaymentService, _sync_to_payment_verification

User = get_user_model()

import uuid as _uuid


# ── Helpers ──────────────────────────────────────────────────────────

def _uid():
    return _uuid.uuid4().hex[:8]


def _make_game(**kwargs):
    uid = _uid()
    defaults = dict(
        name=f'Game-{uid}', slug=f'game-{uid}', short_code=uid[:4].upper(),
        category='FPS', display_name=f'Game {uid}', game_type='TEAM_VS_TEAM',
        is_active=True,
    )
    defaults.update(kwargs)
    return Game.objects.create(**defaults)


def _make_tournament(game, organizer, **kwargs):
    uid = _uid()
    now = timezone.now()
    defaults = dict(
        name=f'Tournament-{uid}',
        slug=f't-{uid}',
        description='Test tournament',
        organizer=organizer,
        game=game,
        max_participants=16,
        min_participants=2,
        registration_start=now - timedelta(days=1),
        registration_end=now + timedelta(days=7),
        tournament_start=now + timedelta(days=14),
        status=Tournament.REGISTRATION_OPEN,
        participation_type=Tournament.SOLO,
        format='single_elimination',
        enable_check_in=True,
        check_in_minutes_before=30,
    )
    defaults.update(kwargs)
    return Tournament.objects.create(**defaults)


def _make_user(username=None, **kwargs):
    uid = _uid()
    uname = username or f'user-{uid}'
    defaults = dict(username=uname, email=f'{uname}@test.dc', password='test1234')
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def _make_registration(tournament, user, **kwargs):
    defaults = dict(
        tournament=tournament,
        user=user,
        status='pending',
        registration_data={'game_id': f'gid-{_uid()}'},
    )
    defaults.update(kwargs)
    return Registration.objects.create(**defaults)


def _make_wallet(user, balance=1000):
    """Create a UserProfile (if needed) and a DeltaCrownWallet with given balance.
    
    Uses economy_services.credit() so the balance is backed by a real
    transaction — required because signals recalculate cached_balance from
    the sum of transactions.
    """
    from apps.user_profile.models_main import UserProfile
    from apps.economy import services as economy_services

    profile, _ = UserProfile.objects.get_or_create(user=user)
    wallet, _ = DeltaCrownWallet.objects.get_or_create(
        profile=profile,
        defaults={'cached_balance': 0},
    )
    if balance > 0:
        economy_services.credit(
            profile=profile,
            amount=balance,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
            idempotency_key=f'test-setup-{user.id}-{_uid()}',
        )
        wallet.refresh_from_db()
    return wallet


def _paid_tournament(game, organizer, fee=500, **kwargs):
    """Create a tournament with an entry fee and deltacoin accepted."""
    return _make_tournament(
        game, organizer,
        has_entry_fee=True,
        entry_fee_amount=Decimal(str(fee)),
        payment_methods=['deltacoin', 'bkash', 'nagad'],
        **kwargs,
    )


# =====================================================================
# P4-T01: DeltaCoin Payment Integration
# =====================================================================


class TestDeltaCoinPayment:
    """P4-T01: DeltaCoin payment wiring — balance check, atomic deduction,
    auto-verify, auto-confirm, refund."""

    @pytest.mark.django_db
    def test_can_use_deltacoin_sufficient(self):
        """AC: Balance check — user can afford."""
        user = _make_user()
        _make_wallet(user, balance=1000)
        result = PaymentService.can_use_deltacoin(user, 500)
        assert result['can_afford'] is True
        assert result['balance'] == 1000
        assert result['required'] == 500
        assert result['shortfall'] == 0

    @pytest.mark.django_db
    def test_can_use_deltacoin_insufficient(self):
        """AC: Balance check — insufficient blocks selection."""
        user = _make_user()
        _make_wallet(user, balance=100)
        result = PaymentService.can_use_deltacoin(user, 500)
        assert result['can_afford'] is False
        assert result['shortfall'] == 400

    @pytest.mark.django_db
    def test_process_deltacoin_payment_success(self):
        """AC: Atomic deduction + Payment(verified) + Registration(confirmed)."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=500)

        user = _make_user()
        _make_wallet(user, balance=1000)
        reg = _make_registration(tournament, user, status='pending')

        result = PaymentService.process_deltacoin_payment(
            registration_id=reg.id,
            user=user,
            idempotency_key=f'test-dc-{reg.id}',
        )

        assert result['status'] == 'verified'
        assert result['amount'] == 500
        assert result['balance_after'] == 500  # 1000 - 500

        # Payment auto-verified
        payment = Payment.objects.get(registration=reg)
        assert payment.status == Payment.VERIFIED
        assert payment.payment_method == Payment.DELTACOIN
        assert payment.verified_by == user
        assert payment.verified_at is not None
        assert payment.idempotency_key == f'test-dc-{reg.id}'

        # Registration auto-confirmed
        reg.refresh_from_db()
        assert reg.status == Registration.CONFIRMED

    @pytest.mark.django_db
    def test_process_deltacoin_insufficient_funds(self):
        """AC: Insufficient balance raises ValidationError."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=500)

        user = _make_user()
        _make_wallet(user, balance=100)
        reg = _make_registration(tournament, user, status='pending')

        with pytest.raises(ValidationError, match='Insufficient DeltaCoin'):
            PaymentService.process_deltacoin_payment(
                registration_id=reg.id,
                user=user,
            )

    @pytest.mark.django_db
    def test_deltacoin_transaction_logged(self):
        """AC: Transaction logged for audit."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=200)

        user = _make_user()
        wallet = _make_wallet(user, balance=500)

        reg = _make_registration(tournament, user, status='pending')
        PaymentService.process_deltacoin_payment(
            registration_id=reg.id,
            user=user,
            idempotency_key=f'test-audit-{reg.id}',
        )

        # DeltaCrownTransaction must exist
        txn = DeltaCrownTransaction.objects.filter(
            wallet=wallet,
            reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
        ).first()
        assert txn is not None
        assert txn.amount == -200  # negative = debit

    @pytest.mark.django_db
    def test_refund_deltacoin_payment(self):
        """AC: Refund on withdrawal returns DeltaCoin to balance."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=300)

        user = _make_user()
        _make_wallet(user, balance=1000)
        reg = _make_registration(tournament, user, status='pending')

        # Pay first
        PaymentService.process_deltacoin_payment(
            registration_id=reg.id,
            user=user,
            idempotency_key=f'test-refund-pay-{reg.id}',
        )
        assert PaymentService.get_wallet_balance(user) == 700

        # Refund
        result = PaymentService.refund_deltacoin_payment(
            registration_id=reg.id,
            refund_reason='User cancellation',
            refunded_by=organizer,
            idempotency_key=f'test-refund-{reg.id}',
        )
        assert result['status'] == 'refunded'
        assert result['amount'] == 300
        assert result['balance_after'] == 1000  # Balance restored

        # Payment status updated
        payment = Payment.objects.get(registration=reg)
        assert payment.status == Payment.REFUNDED
        assert payment.refunded_by == organizer
        assert payment.refunded_at is not None

        # Registration cancelled
        reg.refresh_from_db()
        assert reg.status == Registration.CANCELLED

    @pytest.mark.django_db
    def test_idempotency_prevents_double_charge(self):
        """Idempotent: second call with same key returns existing payment
        (service short-circuits on already-verified payment)."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=500)

        user = _make_user()
        _make_wallet(user, balance=2000)
        reg = _make_registration(tournament, user, status='pending')

        key = f'test-idem-{reg.id}'
        r1 = PaymentService.process_deltacoin_payment(
            registration_id=reg.id, user=user, idempotency_key=key,
        )
        assert r1['status'] == 'verified'

        # Registration is now CONFIRMED — service re-checks and returns
        # existing payment via the "already exists" guard.
        reg.refresh_from_db()
        assert reg.status == Registration.CONFIRMED

        # Reset registration to pending to allow re-entry
        reg.status = Registration.PENDING
        reg.save(update_fields=['status'])

        # Second call with same key — economy debit returns existing txn
        r2 = PaymentService.process_deltacoin_payment(
            registration_id=reg.id, user=user, idempotency_key=key,
        )
        assert r2['payment_id'] == r1['payment_id']
        assert r2['message'] == 'Payment already processed'

        # Balance should only be debited once (2000 - 500 = 1500)
        assert PaymentService.get_wallet_balance(user) == 1500


# =====================================================================
# P4-T02: Payment Deadline Auto-Expiry
# =====================================================================


class TestPaymentExpiry:
    """P4-T02: Celery task expires overdue payments, cancels registrations,
    and auto-promotes waitlisted participants."""

    @pytest.mark.django_db
    def test_expire_overdue_payments(self):
        """AC: Submitted payments past deadline are expired."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(
            game, organizer, fee=100,
            payment_deadline_hours=24,
        )

        user = _make_user()
        reg = _make_registration(tournament, user, status='payment_submitted')

        # Create payment submitted 48 hours ago
        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN123',
            status=Payment.SUBMITTED,
        )
        # Backdate submitted_at to 48 hours ago
        Payment.objects.filter(pk=payment.pk).update(
            submitted_at=timezone.now() - timedelta(hours=48)
        )

        from apps.tournaments.tasks.payment_expiry import expire_overdue_payments
        result = expire_overdue_payments()

        assert result['expired'] == 1

        payment.refresh_from_db()
        assert payment.status == Payment.EXPIRED
        assert 'system_auto_expiry' in (payment.notes or {}).get('expired_by', '')

        reg.refresh_from_db()
        assert reg.status == Registration.CANCELLED

    @pytest.mark.django_db
    def test_non_overdue_payments_untouched(self):
        """Payments within deadline are not expired."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(
            game, organizer, fee=100,
            payment_deadline_hours=48,
        )

        user = _make_user()
        reg = _make_registration(tournament, user, status='payment_submitted')

        # Payment submitted just now (within 48h deadline)
        Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_RECENT',
            status=Payment.SUBMITTED,
        )

        from apps.tournaments.tasks.payment_expiry import expire_overdue_payments
        result = expire_overdue_payments()

        assert result['expired'] == 0

    @pytest.mark.django_db
    def test_waitlist_promotion_on_expiry(self):
        """AC: After expiry, next waitlisted participant is promoted."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(
            game, organizer, fee=100,
            payment_deadline_hours=24,
            max_participants=2,
        )

        # Two confirmed registrations + one waitlisted
        u1 = _make_user()
        u2 = _make_user()
        u3 = _make_user()

        _make_registration(tournament, u1, status='confirmed')

        # u2 has overdue payment
        reg2 = _make_registration(tournament, u2, status='payment_submitted')
        payment2 = Payment.objects.create(
            registration=reg2,
            payment_method='nagad',
            amount=Decimal('100.00'),
            transaction_id='TXN_OVERDUE',
            status=Payment.SUBMITTED,
        )
        Payment.objects.filter(pk=payment2.pk).update(
            submitted_at=timezone.now() - timedelta(hours=48)
        )

        # u3 is waitlisted
        reg3 = _make_registration(tournament, u3, status='waitlisted', waitlist_position=1)

        from apps.tournaments.tasks.payment_expiry import expire_overdue_payments
        result = expire_overdue_payments()

        assert result['expired'] == 1
        assert result['promoted'] == 1

        reg3.refresh_from_db()
        # Promoted: should be pending (paid tournament) or confirmed (free)
        assert reg3.status == Registration.PENDING
        assert reg3.waitlist_position is None

    @pytest.mark.django_db
    def test_no_deadline_tournaments_skipped(self):
        """Tournaments with payment_deadline_hours=0 are skipped."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(
            game, organizer, fee=100,
            payment_deadline_hours=0,  # No deadline
        )

        user = _make_user()
        reg = _make_registration(tournament, user, status='payment_submitted')
        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_NO_DEADLINE',
            status=Payment.SUBMITTED,
        )
        Payment.objects.filter(pk=payment.pk).update(
            submitted_at=timezone.now() - timedelta(hours=9999)
        )

        from apps.tournaments.tasks.payment_expiry import expire_overdue_payments
        result = expire_overdue_payments()

        assert result['expired'] == 0

    @pytest.mark.django_db
    def test_expired_status_in_constraint(self):
        """'expired' status is valid per payment_status_valid constraint."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=100)

        user = _make_user()
        reg = _make_registration(tournament, user, status='pending')

        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_EXPIRE',
            status=Payment.EXPIRED,
            verified_by=None,
            verified_at=None,
        )
        # Should not raise — 'expired' is now valid
        payment.refresh_from_db()
        assert payment.status == 'expired'


# =====================================================================
# P4-T03: Payment Model Consolidation Steps 1-3
# =====================================================================


class TestPaymentConsolidation:
    """P4-T03: New nullable fields on Payment, dual-write to PV, consistency."""

    @pytest.mark.django_db
    def test_new_fields_exist_on_payment(self):
        """Step 1: All new fields are accessible and nullable."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=100)

        user = _make_user()
        reg = _make_registration(tournament, user, status='pending')

        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_FIELDS',
            status=Payment.SUBMITTED,
            # New fields — all nullable/blank
            payer_account_number='01712345678',
            amount_bdt=100,
            note='Test note',
            reject_reason='',
            last_action_reason='',
        )
        payment.refresh_from_db()
        assert payment.payer_account_number == '01712345678'
        assert payment.amount_bdt == 100
        assert payment.note == 'Test note'
        assert payment.notes == {}
        assert payment.idempotency_key is None
        assert payment.rejected_by is None
        assert payment.rejected_at is None
        assert payment.refunded_by is None
        assert payment.refunded_at is None

    @pytest.mark.django_db
    def test_notes_json_field(self):
        """Step 1: notes JSONField stores dict correctly."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=100)

        user = _make_user()
        reg = _make_registration(tournament, user, status='pending')

        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_JSON',
            status=Payment.SUBMITTED,
            notes={'auto_verified': True, 'source': 'test'},
        )
        payment.refresh_from_db()
        assert payment.notes['auto_verified'] is True
        assert payment.notes['source'] == 'test'

    @pytest.mark.django_db
    def test_dual_write_on_deltacoin_payment(self):
        """Step 3: DeltaCoin payment creates both Payment + PaymentVerification."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=200)

        user = _make_user()
        _make_wallet(user, balance=500)
        reg = _make_registration(tournament, user, status='pending')

        PaymentService.process_deltacoin_payment(
            registration_id=reg.id,
            user=user,
            idempotency_key=f'test-dual-{reg.id}',
        )

        # Payment row exists
        payment = Payment.objects.get(registration=reg)
        assert payment.status == Payment.VERIFIED

        # PaymentVerification row also exists (dual-write)
        pv = PaymentVerification.objects.get(registration=reg)
        assert pv.status == PaymentVerification.Status.VERIFIED
        assert pv.verified_by == user

    @pytest.mark.django_db
    def test_dual_write_on_verify(self):
        """Step 3: verify_payment syncs to PaymentVerification."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=100)

        user = _make_user()
        reg = _make_registration(tournament, user, status='payment_submitted')

        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_VERIFY',
            status=Payment.SUBMITTED,
        )

        PaymentService.verify_payment(payment, verified_by=organizer)

        # Check PV was created and synced
        pv = PaymentVerification.objects.get(registration=reg)
        assert pv.status == PaymentVerification.Status.VERIFIED
        assert pv.verified_by == organizer

    @pytest.mark.django_db
    def test_dual_write_on_reject(self):
        """Step 3: reject_payment syncs rejection to PaymentVerification."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=100)

        user = _make_user()
        reg = _make_registration(tournament, user, status='payment_submitted')

        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_REJECT',
            status=Payment.SUBMITTED,
        )

        PaymentService.reject_payment(payment, rejected_by=organizer)

        pv = PaymentVerification.objects.get(registration=reg)
        assert pv.status == PaymentVerification.Status.REJECTED
        assert pv.rejected_by == organizer
        assert pv.rejected_at is not None

    @pytest.mark.django_db
    def test_dual_write_on_refund(self):
        """Step 3: refund DeltaCoin syncs refund to PaymentVerification."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=300)

        user = _make_user()
        _make_wallet(user, balance=1000)
        reg = _make_registration(tournament, user, status='pending')

        PaymentService.process_deltacoin_payment(
            registration_id=reg.id,
            user=user,
            idempotency_key=f'test-dual-refund-pay-{reg.id}',
        )

        PaymentService.refund_deltacoin_payment(
            registration_id=reg.id,
            refund_reason='Dual-write refund test',
            refunded_by=organizer,
            idempotency_key=f'test-dual-refund-{reg.id}',
        )

        pv = PaymentVerification.objects.get(registration=reg)
        assert pv.status == PaymentVerification.Status.REFUNDED
        assert pv.refunded_by == organizer
        assert pv.refunded_at is not None

    @pytest.mark.django_db
    def test_sync_function_creates_pv_if_missing(self):
        """_sync_to_payment_verification creates PV row if none exists."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=100)

        user = _make_user()
        reg = _make_registration(tournament, user, status='pending')

        payment = Payment.objects.create(
            registration=reg,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_SYNC',
            status=Payment.SUBMITTED,
            payer_account_number='01799999999',
        )

        # No PV exists yet
        assert not PaymentVerification.objects.filter(registration=reg).exists()

        _sync_to_payment_verification(payment)

        # PV should now exist with mirrored data
        pv = PaymentVerification.objects.get(registration=reg)
        assert pv.payer_account_number == '01799999999'
        assert pv.transaction_id == 'TXN_SYNC'

    @pytest.mark.django_db
    def test_consistency_command_clean(self):
        """Consistency command reports zero discrepancies when synced."""
        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=200)

        user = _make_user()
        _make_wallet(user, balance=500)
        reg = _make_registration(tournament, user, status='pending')

        PaymentService.process_deltacoin_payment(
            registration_id=reg.id,
            user=user,
            idempotency_key=f'test-consistency-{reg.id}',
        )

        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('verify_payment_consistency', stdout=out)
        output = out.getvalue()
        assert 'consistent' in output.lower() or 'Discrepancies:         0' in output

    @pytest.mark.django_db
    def test_payment_deadline_hours_field(self):
        """Tournament has payment_deadline_hours field (default 48)."""
        organizer = _make_user()
        game = _make_game()
        tournament = _make_tournament(game, organizer)
        assert tournament.payment_deadline_hours == 48

        tournament2 = _make_tournament(game, organizer, payment_deadline_hours=72)
        assert tournament2.payment_deadline_hours == 72

    @pytest.mark.django_db
    def test_submit_payment_dual_writes(self):
        """RegistrationService.submit_payment creates PV via dual-write."""
        from apps.tournaments.services.registration_service import RegistrationService

        organizer = _make_user()
        game = _make_game()
        tournament = _paid_tournament(game, organizer, fee=100)

        user = _make_user()
        reg = _make_registration(tournament, user, status='pending')

        payment = RegistrationService.submit_payment(
            registration_id=reg.id,
            payment_method='bkash',
            amount=Decimal('100.00'),
            transaction_id='TXN_REG_SVC',
        )

        # PV should exist from dual-write
        pv = PaymentVerification.objects.get(registration=reg)
        assert pv.transaction_id == 'TXN_REG_SVC'
        assert pv.method == 'bkash'
