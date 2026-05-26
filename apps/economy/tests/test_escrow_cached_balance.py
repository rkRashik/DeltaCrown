from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.economy.escrow_service import lock_funds, payout_winner, refund_funds
from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.economy.services import get_master_treasury
from apps.user_profile.models import UserProfile


User = get_user_model()


class EscrowCachedBalanceAfterTests(TestCase):
    def _wallet(self, username, balance):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="pass123",
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        if balance:
            DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=balance,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note="Test opening balance",
                cached_balance_after=balance,
                idempotency_key=f"test_opening_{username}",
            )
        wallet.refresh_from_db()
        return user, wallet

    def test_lock_funds_sets_cached_balance_after_to_post_lock_balance(self):
        actor, wallet = self._wallet("locker", 500)

        result = lock_funds(wallet, 100, reference_id="lock-balance", actor=actor)

        txn = result.transactions[0]
        wallet.refresh_from_db()
        self.assertEqual(txn.cached_balance_after, 400)
        self.assertEqual(wallet.cached_balance, 400)

    def test_refund_funds_sets_cached_balance_after_to_post_refund_balance(self):
        actor, wallet = self._wallet("refunded", 400)

        result = refund_funds(wallet, 100, reference_id="refund-balance", actor=actor)

        txn = result.transactions[0]
        wallet.refresh_from_db()
        self.assertEqual(txn.cached_balance_after, 500)
        self.assertEqual(wallet.cached_balance, 500)

    def test_payout_winner_sets_winner_cached_balance_after(self):
        actor, winner_wallet = self._wallet("winner", 300)
        treasury = get_master_treasury()
        treasury.cached_balance = 0
        treasury.save(update_fields=["cached_balance", "updated_at"])

        result = payout_winner(
            winner_wallet,
            200,
            platform_fee_pct=5,
            reference_id="payout-winner-balance",
            actor=actor,
        )

        winner_txn = next(
            txn for txn in result.transactions
            if txn.reason == DeltaCrownTransaction.Reason.WAGER_WIN
        )
        winner_wallet.refresh_from_db()
        self.assertEqual(winner_txn.cached_balance_after, 490)
        self.assertEqual(winner_wallet.cached_balance, 490)

    def test_payout_winner_sets_treasury_cached_balance_after(self):
        actor, winner_wallet = self._wallet("winnerfee", 300)
        treasury = get_master_treasury()
        treasury.cached_balance = 0
        treasury.save(update_fields=["cached_balance", "updated_at"])

        result = payout_winner(
            winner_wallet,
            200,
            platform_fee_pct=5,
            reference_id="payout-fee-balance",
            actor=actor,
        )

        fee_txn = next(
            txn for txn in result.transactions
            if txn.reason == DeltaCrownTransaction.Reason.PLATFORM_FEE
        )
        treasury.refresh_from_db()
        self.assertEqual(fee_txn.cached_balance_after, 10)
        self.assertEqual(treasury.cached_balance, 10)
