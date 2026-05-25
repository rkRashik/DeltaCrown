from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.economy.exceptions import InsufficientFunds
from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.tournaments.models import Game, Payment, Registration, Tournament
from apps.tournaments.services.registration_service import RegistrationService
from apps.user_profile.models import UserProfile


User = get_user_model()


class RegistrationDeltaCoinPaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dc-player",
            email="dc-player@example.com",
            password="pass123",
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.organizer = User.objects.create_user(
            username="dc-organizer",
            email="dc-organizer@example.com",
            password="pass123",
        )
        self.game = Game.objects.create(name="DeltaCoin Game", slug="deltacoin-game")
        self.tournament = Tournament.objects.create(
            name="DeltaCoin Cup",
            slug="deltacoin-cup",
            game=self.game,
            organizer=self.organizer,
            status=Tournament.REGISTRATION_OPEN,
            participation_type=Tournament.SOLO,
            max_participants=16,
            min_participants=2,
            registration_start=timezone.now(),
            registration_end=timezone.now(),
            tournament_start=timezone.now(),
            has_entry_fee=True,
            entry_fee_amount=Decimal("100.00"),
            payment_methods=[Tournament.DELTACOIN],
        )
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.user,
            status=Registration.PENDING,
            registration_data={"game_id": "dc-player"},
        )

    def _wallet(self, balance):
        return DeltaCrownWallet.objects.create(
            profile=self.profile,
            cached_balance=balance,
        )

    def test_pay_with_deltacoin_debits_wallet_and_confirms_registration(self):
        wallet = self._wallet(500)

        payment, transaction = RegistrationService.pay_with_deltacoin(
            self.registration.id,
            self.user,
        )

        wallet.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 400)
        self.assertEqual(self.registration.status, Registration.CONFIRMED)
        self.assertEqual(payment.status, Payment.VERIFIED)
        self.assertEqual(transaction.amount, -100)
        self.assertEqual(DeltaCrownTransaction.objects.count(), 1)

    def test_pay_with_deltacoin_transaction_has_cached_balance_after(self):
        self._wallet(500)

        _, transaction = RegistrationService.pay_with_deltacoin(
            self.registration.id,
            self.user,
        )

        self.assertEqual(transaction.cached_balance_after, 400)

    def test_pay_with_deltacoin_is_idempotent_on_duplicate_call(self):
        wallet = self._wallet(500)

        first_payment, first_tx = RegistrationService.pay_with_deltacoin(
            self.registration.id,
            self.user,
        )
        second_payment, second_tx = RegistrationService.pay_with_deltacoin(
            self.registration.id,
            self.user,
        )

        wallet.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 400)
        self.assertEqual(DeltaCrownTransaction.objects.count(), 1)
        self.assertEqual(first_tx.id, second_tx.id)
        self.assertEqual(first_payment.id, second_payment.id)

    def test_pay_with_deltacoin_raises_insufficient_funds(self):
        wallet = self._wallet(50)

        with self.assertRaises(InsufficientFunds):
            RegistrationService.pay_with_deltacoin(
                self.registration.id,
                self.user,
            )

        wallet.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 50)
        self.assertEqual(self.registration.status, Registration.PENDING)
        self.assertEqual(DeltaCrownTransaction.objects.count(), 0)
        self.assertFalse(hasattr(self.registration, "payment"))
