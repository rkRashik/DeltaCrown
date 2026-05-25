from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.tournaments.models import (
    Game,
    Payment,
    PrizeTransaction,
    Registration,
    Tournament,
    TournamentResult,
)
from apps.tournaments.services.payout_service import PayoutService
from apps.user_profile.models import UserProfile


User = get_user_model()


class PayoutServiceTests(TestCase):
    def setUp(self):
        self.organizer = self._user("payout-organizer")
        self.winner_user = self._user("payout-winner")
        self.runner_up_user = self._user("payout-runner")
        self.bdt_user = self._user("payout-bdt")
        self.game = Game.objects.create(name="Payout Game", slug="payout-game")

    def _user(self, username):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="pass123",
        )
        UserProfile.objects.get_or_create(user=user)
        return user

    def _tournament(self, *, status=Tournament.COMPLETED, entry_fee_amount=Decimal("100.00")):
        return Tournament.objects.create(
            name=f"Payout Tournament {status}",
            slug=f"payout-tournament-{status}-{Tournament.objects.count()}",
            game=self.game,
            organizer=self.organizer,
            status=status,
            participation_type=Tournament.SOLO,
            max_participants=16,
            min_participants=2,
            registration_start=timezone.now(),
            registration_end=timezone.now(),
            tournament_start=timezone.now(),
            prize_pool=Decimal("500.00"),
            prize_distribution={"1st": "250.00"},
            has_entry_fee=True,
            entry_fee_amount=entry_fee_amount,
            payment_methods=[Tournament.DELTACOIN],
        )

    def _registration(self, tournament, user, *, status=Registration.CONFIRMED):
        return Registration.objects.create(
            tournament=tournament,
            user=user,
            status=status,
            registration_data={"game_id": user.username},
        )

    def _wallet(self, user, balance=0):
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=user.profile)
        wallet.cached_balance = balance
        wallet.save(update_fields=["cached_balance", "updated_at"])
        return wallet

    def _original_dc_payment(self, tournament, registration, *, debit_amount=100, wallet_balance=400):
        wallet = self._wallet(registration.user, wallet_balance + debit_amount)
        DeltaCrownTransaction.objects.create(
            wallet=wallet,
            amount=-debit_amount,
            reason=DeltaCrownTransaction.Reason.ENTRY_FEE_DEBIT,
            tournament_id=tournament.id,
            registration_id=registration.id,
            note="Original tournament entry fee",
            created_by=registration.user,
            idempotency_key=f"tournament_entry_{tournament.id}_reg_{registration.id}",
            cached_balance_after=wallet_balance,
        )
        wallet.cached_balance = wallet_balance
        wallet.save(update_fields=["cached_balance", "updated_at"])
        Payment.objects.create(
            registration=registration,
            payment_method=Payment.DELTACOIN,
            amount=Decimal("100.00"),
            transaction_id="DC-original",
            status=Payment.VERIFIED,
            verified_by=self.organizer,
            verified_at=timezone.now(),
        )
        return wallet

    def test_process_payouts_credits_winner_wallet(self):
        tournament = self._tournament()
        winner = self._registration(tournament, self.winner_user)
        TournamentResult.objects.create(
            tournament=tournament,
            winner=winner,
            rules_applied={"determination": "test"},
        )
        wallet = self._wallet(self.winner_user, 0)

        tx_ids = PayoutService.process_payouts(tournament.id, processed_by=self.organizer)

        wallet.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 250)
        self.assertEqual(len(tx_ids), 1)
        self.assertEqual(DeltaCrownTransaction.objects.get(id=tx_ids[0]).amount, 250)

    def test_process_payouts_sets_cached_balance_after(self):
        tournament = self._tournament()
        winner = self._registration(tournament, self.winner_user)
        TournamentResult.objects.create(
            tournament=tournament,
            winner=winner,
            rules_applied={"determination": "test"},
        )
        self._wallet(self.winner_user, 0)

        tx_ids = PayoutService.process_payouts(tournament.id, processed_by=self.organizer)

        transaction = DeltaCrownTransaction.objects.get(id=tx_ids[0])
        self.assertEqual(transaction.cached_balance_after, 250)

    def test_process_payouts_creates_completed_prize_transaction(self):
        tournament = self._tournament()
        winner = self._registration(tournament, self.winner_user)
        TournamentResult.objects.create(
            tournament=tournament,
            winner=winner,
            rules_applied={"determination": "test"},
        )
        self._wallet(self.winner_user, 0)

        tx_ids = PayoutService.process_payouts(tournament.id, processed_by=self.organizer)

        prize_tx = PrizeTransaction.objects.get(tournament=tournament, participant=winner)
        self.assertEqual(prize_tx.status, PrizeTransaction.Status.COMPLETED)
        self.assertEqual(prize_tx.coin_transaction_id, tx_ids[0])
        self.assertEqual(prize_tx.placement, PrizeTransaction.Placement.FIRST)

    def test_process_payouts_is_idempotent(self):
        tournament = self._tournament()
        winner = self._registration(tournament, self.winner_user)
        TournamentResult.objects.create(
            tournament=tournament,
            winner=winner,
            rules_applied={"determination": "test"},
        )
        wallet = self._wallet(self.winner_user, 0)

        first = PayoutService.process_payouts(tournament.id, processed_by=self.organizer)
        second = PayoutService.process_payouts(tournament.id, processed_by=self.organizer)

        wallet.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 250)
        self.assertEqual(first, second)
        self.assertEqual(
            DeltaCrownTransaction.objects.filter(
                idempotency_key=f"prize_payout_t{tournament.id}_r{winner.id}_p1st"
            ).count(),
            1,
        )
        self.assertEqual(
            PrizeTransaction.objects.filter(
                tournament=tournament,
                participant=winner,
                placement=PrizeTransaction.Placement.FIRST,
                status=PrizeTransaction.Status.COMPLETED,
            ).count(),
            1,
        )

    def test_process_payouts_requires_completed_status(self):
        tournament = self._tournament(status=Tournament.LIVE)

        with self.assertRaises(ValidationError):
            PayoutService.process_payouts(tournament.id, processed_by=self.organizer)

    def test_process_refunds_credits_dc_payer_wallet(self):
        tournament = self._tournament(status=Tournament.CANCELLED)
        registration = self._registration(tournament, self.winner_user)
        wallet = self._original_dc_payment(tournament, registration, debit_amount=100, wallet_balance=400)

        tx_ids = PayoutService.process_refunds(tournament.id, processed_by=self.organizer)

        wallet.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 500)
        refund_tx = DeltaCrownTransaction.objects.get(id=tx_ids[0])
        self.assertEqual(refund_tx.amount, 100)
        self.assertEqual(refund_tx.reason, DeltaCrownTransaction.Reason.REFUND)

    def test_process_refunds_skips_bdt_payer(self):
        tournament = self._tournament(status=Tournament.CANCELLED)
        registration = self._registration(tournament, self.bdt_user)
        wallet = self._wallet(self.bdt_user, 0)
        Payment.objects.create(
            registration=registration,
            payment_method=Payment.BKASH,
            amount=Decimal("100.00"),
            transaction_id="BKASH-1",
            status=Payment.VERIFIED,
            verified_by=self.organizer,
            verified_at=timezone.now(),
        )

        tx_ids = PayoutService.process_refunds(tournament.id, processed_by=self.organizer)

        wallet.refresh_from_db()
        self.assertEqual(tx_ids, [])
        self.assertEqual(wallet.cached_balance, 0)
        self.assertFalse(
            DeltaCrownTransaction.objects.filter(
                reason=DeltaCrownTransaction.Reason.REFUND,
                registration_id=registration.id,
            ).exists()
        )

    def test_process_refunds_uses_original_dc_transaction_amount(self):
        tournament = self._tournament(status=Tournament.CANCELLED, entry_fee_amount=Decimal("999.00"))
        registration = self._registration(tournament, self.winner_user)
        wallet = self._original_dc_payment(tournament, registration, debit_amount=75, wallet_balance=425)

        PayoutService.process_refunds(tournament.id, processed_by=self.organizer)

        wallet.refresh_from_db()
        refund_tx = DeltaCrownTransaction.objects.get(
            idempotency_key=f"prize_refund_t{tournament.id}_r{registration.id}"
        )
        self.assertEqual(refund_tx.amount, 75)
        self.assertEqual(wallet.cached_balance, 500)

    def test_process_refunds_is_idempotent(self):
        tournament = self._tournament(status=Tournament.CANCELLED)
        registration = self._registration(tournament, self.winner_user)
        wallet = self._original_dc_payment(tournament, registration, debit_amount=100, wallet_balance=400)

        first = PayoutService.process_refunds(tournament.id, processed_by=self.organizer)
        second = PayoutService.process_refunds(tournament.id, processed_by=self.organizer)

        wallet.refresh_from_db()
        self.assertEqual(wallet.cached_balance, 500)
        self.assertEqual(first, second)
        self.assertEqual(
            DeltaCrownTransaction.objects.filter(
                idempotency_key=f"prize_refund_t{tournament.id}_r{registration.id}"
            ).count(),
            1,
        )
