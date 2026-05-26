from unittest.mock import patch

from django.test import TestCase

from apps.competition.models import Bounty, BountyClaim
from apps.competition.services.challenge_service import BountyService
from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
from apps.organizations.tests.factories import GameFactory, TeamFactory, UserFactory
from apps.user_profile.models import UserProfile


class BountyVerifyClaimLifecycleTests(TestCase):
    def setUp(self):
        self.game = GameFactory()
        self.verifier = UserFactory(username="bounty_verifier", is_staff=True)

    def _wallet_for(self, user, balance=0):
        profile, _ = UserProfile.objects.get_or_create(user=user)
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        if balance:
            DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=balance,
                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                note="Test opening balance",
                cached_balance_after=balance,
                idempotency_key=f"bounty_opening_{user.username}",
            )
        wallet.refresh_from_db()
        return wallet

    def _make_claim(self, *, reward_amount_dc=100):
        issuer = UserFactory(username="bounty_issuer")
        claimant = UserFactory(username="bounty_claimant")
        issuer_team = TeamFactory.create_independent(
            created_by=issuer,
            game_id=self.game.id,
        )
        claiming_team = TeamFactory.create_independent(
            created_by=claimant,
            game_id=self.game.id,
        )
        issuer_wallet = self._wallet_for(issuer, 1000)
        self._wallet_for(claimant, 0)
        issuer_lock_txn = DeltaCrownTransaction.objects.create(
            wallet=issuer_wallet,
            amount=1,
            reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
            note="Test issuer lock marker",
            cached_balance_after=issuer_wallet.cached_balance,
            idempotency_key=f"bounty_issuer_lock_{issuer.username}",
        )
        bounty = Bounty.objects.create(
            issuer_team=issuer_team,
            game=self.game,
            created_by=issuer,
            title="Verify claim bounty",
            is_hitlist=True,
            reward_amount_dc=reward_amount_dc,
            issuer_lock_txn=issuer_lock_txn,
            funded_by=issuer,
            escrow_locked=True,
            max_claims=1,
        )
        claim = BountyClaim.objects.create(
            bounty=bounty,
            claiming_team=claiming_team,
            claimed_by=claimant,
            status="PENDING",
        )
        return bounty, claim, claimant

    def test_approved_claim_status_is_persisted_before_payout_call(self):
        _bounty, claim, _claimant = self._make_claim()

        with patch.object(
            BountyService,
            "_hitlist_payout_to_challenger",
            side_effect=RuntimeError("payout failed"),
        ):
            with self.assertRaises(RuntimeError):
                BountyService.verify_claim(
                    claim_id=claim.id,
                    verified_by=self.verifier,
                    approved=True,
                    notes="approved",
                )

        claim.refresh_from_db()
        self.assertEqual(claim.status, "VERIFIED")
        self.assertEqual(claim.verified_by, self.verifier)
        self.assertIsNotNone(claim.verified_at)
        self.assertIsNone(claim.outcome_txn)

    def test_approved_claim_records_outcome_transaction_on_successful_payout(self):
        bounty, claim, claimant = self._make_claim()

        result = BountyService.verify_claim(
            claim_id=claim.id,
            verified_by=self.verifier,
            approved=True,
            notes="approved",
        )

        result.refresh_from_db()
        bounty.refresh_from_db()
        self.assertEqual(result.status, "VERIFIED")
        self.assertIsNotNone(result.outcome_txn)
        self.assertEqual(result.outcome_txn.reason, DeltaCrownTransaction.Reason.WAGER_WIN)
        self.assertEqual(result.outcome_txn.wallet.profile.user, claimant)
        self.assertLessEqual(
            len(result.outcome_txn.idempotency_key),
            DeltaCrownTransaction._meta.get_field("idempotency_key").max_length,
        )
        self.assertTrue(result.outcome_txn.idempotency_key.startswith("escrow_winner_HL-"))
        self.assertEqual(bounty.status, "CLAIMED")
        self.assertEqual(bounty.claim_count, 1)

    def test_verify_claim_retry_does_not_double_payout(self):
        _bounty, claim, claimant = self._make_claim()

        first = BountyService.verify_claim(
            claim_id=claim.id,
            verified_by=self.verifier,
            approved=True,
            notes="approved",
        )
        claimant_wallet = DeltaCrownWallet.objects.get(profile__user=claimant)
        first_balance = claimant_wallet.cached_balance
        first_txn_id = first.outcome_txn_id
        first_txn_count = DeltaCrownTransaction.objects.filter(
            wallet=claimant_wallet,
            reason=DeltaCrownTransaction.Reason.WAGER_WIN,
        ).count()

        with patch.object(
            BountyService,
            "_hitlist_payout_to_challenger",
        ) as payout_mock:
            second = BountyService.verify_claim(
                claim_id=claim.id,
                verified_by=self.verifier,
                approved=True,
                notes="approved retry",
            )
            self.assertEqual(payout_mock.call_count, 0)

        claimant_wallet.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(claimant_wallet.cached_balance, first_balance)
        self.assertEqual(second.outcome_txn_id, first_txn_id)
        self.assertEqual(
            DeltaCrownTransaction.objects.filter(
                wallet=claimant_wallet,
                reason=DeltaCrownTransaction.Reason.WAGER_WIN,
            ).count(),
            first_txn_count,
        )

    def test_rejected_claim_behavior_remains_unchanged(self):
        _bounty, claim, _claimant = self._make_claim()

        result = BountyService.verify_claim(
            claim_id=claim.id,
            verified_by=self.verifier,
            approved=False,
            notes="rejected",
        )

        result.refresh_from_db()
        self.assertEqual(result.status, "REJECTED")
        self.assertEqual(result.closure_reason, "REJECTED")
        self.assertEqual(result.admin_notes, "rejected")
        self.assertIsNone(result.outcome_txn)
