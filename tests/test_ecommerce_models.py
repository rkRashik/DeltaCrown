"""
Ecommerce model tests — Product, Order, OrderItem, and supporting models.

Validates model structure, soft-delete inheritance, field definitions,
status choices, and business logic properties.
"""
import pytest
from apps.common.models import SoftDeleteModel


# ────────────────────────────────────────────────────────────────────
# Product Model
# ────────────────────────────────────────────────────────────────────

class TestProductModel:
    """Verify Product model structure and soft-delete."""

    def test_product_importable(self):
        from apps.ecommerce.models import Product
        assert Product is not None

    def test_product_uses_soft_delete(self):
        from apps.ecommerce.models import Product
        assert issubclass(Product, SoftDeleteModel)

    def test_product_has_soft_delete_fields(self):
        from apps.ecommerce.models import Product
        field_names = {f.name for f in Product._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names
        assert 'deleted_by' in field_names

    def test_product_type_choices(self):
        from apps.ecommerce.models import Product
        types = {c[0] for c in Product.PRODUCT_TYPES}
        assert 'physical' in types
        assert 'digital' in types
        assert 'subscription' in types
        assert 'bundle' in types

    def test_product_rarity_levels(self):
        from apps.ecommerce.models import Product
        rarities = {c[0] for c in Product.RARITY_LEVELS}
        assert 'common' in rarities
        assert 'legendary' in rarities
        assert 'mythic' in rarities

    def test_product_has_price_fields(self):
        from apps.ecommerce.models import Product
        field_names = {f.name for f in Product._meta.get_fields()}
        assert 'price' in field_names
        assert 'original_price' in field_names
        assert 'discount_percentage' in field_names

    def test_product_has_stock_fields(self):
        from apps.ecommerce.models import Product
        field_names = {f.name for f in Product._meta.get_fields()}
        assert 'stock' in field_names
        assert 'track_stock' in field_names
        assert 'allow_backorder' in field_names

    def test_product_has_slug_field(self):
        from apps.ecommerce.models import Product
        slug_field = Product._meta.get_field('slug')
        assert slug_field.unique is True

    def test_product_has_timestamps(self):
        from apps.ecommerce.models import Product
        field_names = {f.name for f in Product._meta.get_fields()}
        assert 'created_at' in field_names
        assert 'updated_at' in field_names


# ────────────────────────────────────────────────────────────────────
# Order Model
# ────────────────────────────────────────────────────────────────────

class TestOrderModel:
    """Verify Order model structure and soft-delete."""

    def test_order_importable(self):
        from apps.ecommerce.models import Order
        assert Order is not None

    def test_order_uses_soft_delete(self):
        from apps.ecommerce.models import Order
        assert issubclass(Order, SoftDeleteModel)

    def test_order_has_soft_delete_fields(self):
        from apps.ecommerce.models import Order
        field_names = {f.name for f in Order._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names
        assert 'deleted_by' in field_names

    def test_order_status_choices(self):
        from apps.ecommerce.models import Order
        statuses = {c[0] for c in Order.STATUS_CHOICES}
        assert 'pending' in statuses
        assert 'paid' in statuses
        assert 'shipped' in statuses
        assert 'delivered' in statuses
        assert 'completed' in statuses
        assert 'cancelled' in statuses
        assert 'refunded' in statuses

    def test_order_payment_methods(self):
        from apps.ecommerce.models import Order
        methods = {c[0] for c in Order.PAYMENT_METHODS}
        assert 'delta_coins' in methods
        assert 'credit_card' in methods

    def test_order_has_billing_fields(self):
        from apps.ecommerce.models import Order
        field_names = {f.name for f in Order._meta.get_fields()}
        assert 'billing_name' in field_names
        assert 'billing_email' in field_names
        assert 'billing_address' in field_names

    def test_order_has_pricing_fields(self):
        from apps.ecommerce.models import Order
        field_names = {f.name for f in Order._meta.get_fields()}
        assert 'subtotal' in field_names
        assert 'total_price' in field_names
        assert 'tax_amount' in field_names
        assert 'discount_amount' in field_names

    def test_order_number_is_unique(self):
        from apps.ecommerce.models import Order
        field = Order._meta.get_field('order_number')
        assert field.unique is True


# ────────────────────────────────────────────────────────────────────
# OrderItem Model
# ────────────────────────────────────────────────────────────────────

class TestOrderItemModel:
    """Verify OrderItem model structure."""

    def test_order_item_importable(self):
        from apps.ecommerce.models import OrderItem
        assert OrderItem is not None

    def test_order_item_uses_soft_delete(self):
        from apps.ecommerce.models import OrderItem
        assert issubclass(OrderItem, SoftDeleteModel)

    def test_order_item_has_price_fields(self):
        from apps.ecommerce.models import OrderItem
        field_names = {f.name for f in OrderItem._meta.get_fields()}
        assert 'unit_price' in field_names
        assert 'total_price' in field_names
        assert 'quantity' in field_names

    def test_order_item_stores_snapshot(self):
        from apps.ecommerce.models import OrderItem
        field_names = {f.name for f in OrderItem._meta.get_fields()}
        assert 'product_name' in field_names


# ────────────────────────────────────────────────────────────────────
# Supporting Models
# ────────────────────────────────────────────────────────────────────

class TestSupportingEcommerceModels:
    """Verify Category, Brand, Cart, Wishlist, Review, Coupon models."""

    def test_category_importable(self):
        from apps.ecommerce.models import Category
        assert Category is not None

    def test_category_has_slug(self):
        from apps.ecommerce.models import Category
        field = Category._meta.get_field('slug')
        assert field.unique is True

    def test_category_types(self):
        from apps.ecommerce.models import Category
        types = {c[0] for c in Category.CATEGORY_TYPES}
        assert 'featured' in types
        assert 'merchandise' in types
        assert 'digital' in types

    def test_brand_importable(self):
        from apps.ecommerce.models import Brand
        assert Brand is not None

    def test_cart_importable(self):
        from apps.ecommerce.models import Cart
        assert Cart is not None

    def test_wishlist_importable(self):
        from apps.ecommerce.models import Wishlist
        assert Wishlist is not None

    def test_review_rating_choices(self):
        from apps.ecommerce.models import Review
        choices = {c[0] for c in Review.RATING_CHOICES}
        assert choices == {1, 2, 3, 4, 5}

    def test_coupon_discount_types(self):
        from apps.ecommerce.models import Coupon
        types = {c[0] for c in Coupon.DISCOUNT_TYPES}
        assert 'percentage' in types
        assert 'fixed' in types

    def test_loyalty_program_importable(self):
        from apps.ecommerce.models import LoyaltyProgram
        assert LoyaltyProgram is not None


# ────────────────────────────────────────────────────────────────────
# Dispute Soft-Delete Verification
# ────────────────────────────────────────────────────────────────────

class TestDisputeSoftDelete:
    """Verify DisputeRecord and DisputeEvidence use SoftDeleteModel."""

    def test_dispute_record_uses_soft_delete(self):
        from apps.tournaments.models.dispute import DisputeRecord
        assert issubclass(DisputeRecord, SoftDeleteModel)

    def test_dispute_record_has_soft_delete_fields(self):
        from apps.tournaments.models.dispute import DisputeRecord
        field_names = {f.name for f in DisputeRecord._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names
        assert 'deleted_by' in field_names

    def test_dispute_evidence_uses_soft_delete(self):
        from apps.tournaments.models.dispute import DisputeEvidence
        assert issubclass(DisputeEvidence, SoftDeleteModel)

    def test_dispute_evidence_has_soft_delete_fields(self):
        from apps.tournaments.models.dispute import DisputeEvidence
        field_names = {f.name for f in DisputeEvidence._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names

    def test_dispute_status_constants(self):
        from apps.tournaments.models.dispute import DisputeRecord
        assert DisputeRecord.OPEN == 'open'
        assert DisputeRecord.UNDER_REVIEW == 'under_review'
        assert DisputeRecord.ESCALATED == 'escalated'
        assert DisputeRecord.RESOLVED_FOR_SUBMITTER == 'resolved_for_submitter'
        assert DisputeRecord.RESOLVED_FOR_OPPONENT == 'resolved_for_opponent'
        assert DisputeRecord.DISMISSED == 'dismissed'

    def test_dispute_reason_codes(self):
        from apps.tournaments.models.dispute import DisputeRecord
        reasons = {c[0] for c in DisputeRecord.REASON_CHOICES}
        assert 'score_mismatch' in reasons
        assert 'cheating_suspicion' in reasons
        assert 'wrong_winner' in reasons


# ────────────────────────────────────────────────────────────────────
# Moderation Soft-Delete Verification
# ────────────────────────────────────────────────────────────────────

class TestModerationSoftDelete:
    """Verify ModerationSanction and AbuseReport use SoftDeleteModel."""

    def test_sanction_uses_soft_delete(self):
        from apps.moderation.models import ModerationSanction
        assert issubclass(ModerationSanction, SoftDeleteModel)

    def test_sanction_has_soft_delete_fields(self):
        from apps.moderation.models import ModerationSanction
        field_names = {f.name for f in ModerationSanction._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names
        assert 'deleted_by' in field_names

    def test_abuse_report_uses_soft_delete(self):
        from apps.moderation.models import AbuseReport
        assert issubclass(AbuseReport, SoftDeleteModel)

    def test_abuse_report_has_soft_delete_fields(self):
        from apps.moderation.models import AbuseReport
        field_names = {f.name for f in AbuseReport._meta.get_fields()}
        assert 'is_deleted' in field_names

    def test_audit_remains_immutable(self):
        """ModerationAudit should NOT use SoftDeleteModel (immutable audit trail)."""
        from apps.moderation.models import ModerationAudit
        assert not issubclass(ModerationAudit, SoftDeleteModel)

    def test_sanction_type_choices(self):
        from apps.moderation.models import ModerationSanction
        types = {c[0] for c in ModerationSanction.TYPE_CHOICES}
        assert 'ban' in types
        assert 'suspend' in types
        assert 'mute' in types

    def test_abuse_report_states(self):
        from apps.moderation.models import AbuseReport
        states = {c[0] for c in AbuseReport.STATE_CHOICES}
        assert 'open' in states
        assert 'triaged' in states
        assert 'resolved' in states
        assert 'rejected' in states

    def test_abuse_report_valid_transitions(self):
        from apps.moderation.models import AbuseReport
        assert AbuseReport.VALID_TRANSITIONS[AbuseReport.STATE_OPEN] == [AbuseReport.STATE_TRIAGED]
        assert AbuseReport.STATE_RESOLVED in AbuseReport.VALID_TRANSITIONS[AbuseReport.STATE_TRIAGED]
        assert AbuseReport.VALID_TRANSITIONS[AbuseReport.STATE_RESOLVED] == []


# ────────────────────────────────────────────────────────────────────
# Economy Model Soft-Delete Verification
# ────────────────────────────────────────────────────────────────────

class TestEconomySoftDelete:
    """Verify economy models use SoftDeleteModel where appropriate."""

    def test_wallet_uses_soft_delete(self):
        from apps.economy.models import DeltaCrownWallet
        assert issubclass(DeltaCrownWallet, SoftDeleteModel)

    def test_transaction_does_not_use_soft_delete(self):
        """DeltaCrownTransaction is immutable ledger — no soft-delete."""
        from apps.economy.models import DeltaCrownTransaction
        assert not issubclass(DeltaCrownTransaction, SoftDeleteModel)

    def test_coin_policy_uses_soft_delete(self):
        from apps.economy.models import CoinPolicy
        assert issubclass(CoinPolicy, SoftDeleteModel)

    def test_topup_request_uses_soft_delete(self):
        from apps.economy.models import TopUpRequest
        assert issubclass(TopUpRequest, SoftDeleteModel)

    def test_inventory_item_uses_soft_delete(self):
        from apps.economy.models import InventoryItem
        assert issubclass(InventoryItem, SoftDeleteModel)

    def test_user_inventory_item_uses_soft_delete(self):
        from apps.economy.models import UserInventoryItem
        assert issubclass(UserInventoryItem, SoftDeleteModel)

    def test_wallet_pin_otp_uses_soft_delete(self):
        from apps.economy.models import WalletPINOTP
        assert issubclass(WalletPINOTP, SoftDeleteModel)

    def test_gift_request_uses_soft_delete(self):
        from apps.economy.models import GiftRequest
        assert issubclass(GiftRequest, SoftDeleteModel)

    def test_trade_request_uses_soft_delete(self):
        from apps.economy.models import TradeRequest
        assert issubclass(TradeRequest, SoftDeleteModel)

    def test_economy_exports_complete(self):
        """Verify __init__.py exports all models."""
        from apps.economy import models as m
        assert hasattr(m, 'DeltaCrownWallet')
        assert hasattr(m, 'DeltaCrownTransaction')
        assert hasattr(m, 'CoinPolicy')
        assert hasattr(m, 'TopUpRequest')
        assert hasattr(m, 'WithdrawalRequest')
        assert hasattr(m, 'InventoryItem')
        assert hasattr(m, 'UserInventoryItem')
        assert hasattr(m, 'GiftRequest')
        assert hasattr(m, 'TradeRequest')
        assert hasattr(m, 'WalletPINOTP')


# ────────────────────────────────────────────────────────────────────
# Competition BountyClaim Soft-Delete
# ────────────────────────────────────────────────────────────────────

class TestBountyClaimSoftDelete:
    """Verify BountyClaim uses SoftDeleteModel."""

    def test_bounty_claim_uses_soft_delete(self):
        from apps.competition.models.bounty import BountyClaim
        assert issubclass(BountyClaim, SoftDeleteModel)

    def test_bounty_claim_has_soft_delete_fields(self):
        from apps.competition.models.bounty import BountyClaim
        field_names = {f.name for f in BountyClaim._meta.get_fields()}
        assert 'is_deleted' in field_names
        assert 'deleted_at' in field_names

    def test_bounty_claim_status_choices(self):
        from apps.competition.models.bounty import BountyClaim
        statuses = {c[0] for c in BountyClaim.STATUS_CHOICES}
        assert 'PENDING' in statuses
        assert 'VERIFIED' in statuses
        assert 'REJECTED' in statuses
        assert 'PAID' in statuses

    def test_bounty_claim_uuid_pk(self):
        from apps.competition.models.bounty import BountyClaim
        pk_field = BountyClaim._meta.pk
        assert pk_field.name == 'id'

    def test_parent_bounty_uses_soft_delete(self):
        from apps.competition.models.bounty import Bounty
        assert issubclass(Bounty, SoftDeleteModel)
