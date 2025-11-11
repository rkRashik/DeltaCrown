"""
Module 7.2 - DeltaCoin Shop: Catalog Admin Tests

Tests the ShopItem model and admin interface:
- Model field constraints (sku unique, price positive)
- Admin registration and list display
- Active filter functionality

Coverage:
- Item creation happy path
- SKU unique constraint
- Price positive CHECK constraint
- Admin registered correctly
- Active field filtering in admin
"""

import pytest
from decimal import Decimal
from django.contrib import admin
from django.db import IntegrityError
from django.core.exceptions import ValidationError


@pytest.mark.django_db
class TestShopItemCatalog:
    """Test ShopItem model and admin functionality."""

    def test_shop_item_creation(self):
        """Create ShopItem with valid fields."""
        from apps.shop.models import ShopItem

        item = ShopItem.objects.create(
            sku='BOOST_XP_100',
            name='100 XP Boost',
            description='Adds 100 XP to your profile',
            price=Decimal('50.00'),
            active=True
        )

        assert item.sku == 'BOOST_XP_100'
        assert item.name == '100 XP Boost'
        assert item.price == Decimal('50.00')
        assert item.active is True
        assert item.created_at is not None

    def test_sku_unique_constraint(self):
        """SKU must be unique - duplicate raises IntegrityError."""
        from apps.shop.models import ShopItem

        ShopItem.objects.create(
            sku='BADGE_GOLD',
            name='Gold Badge',
            price=Decimal('100.00'),
            active=True
        )

        # Duplicate SKU should fail
        with pytest.raises(IntegrityError):
            ShopItem.objects.create(
                sku='BADGE_GOLD',  # Same SKU
                name='Different Name',
                price=Decimal('200.00'),
                active=True
            )

    def test_price_positive_constraint(self):
        """Price must be positive - zero/negative raises ValidationError."""
        from apps.shop.models import ShopItem

        # Zero price should fail CHECK constraint
        item_zero = ShopItem(
            sku='FREE_ITEM',
            name='Free Item',
            price=Decimal('0.00'),  # Invalid
            active=True
        )
        with pytest.raises((ValidationError, IntegrityError)):
            item_zero.full_clean()

        # Negative price should fail CHECK constraint
        item_negative = ShopItem(
            sku='NEGATIVE_ITEM',
            name='Negative Item',
            price=Decimal('-10.00'),  # Invalid
            active=True
        )
        with pytest.raises((ValidationError, IntegrityError)):
            item_negative.full_clean()

    def test_shop_item_admin_registered(self):
        """ShopItemAdmin is registered in Django admin."""
        from apps.shop.models import ShopItem

        # Check model is registered
        assert ShopItem in admin.site._registry
        admin_class = admin.site._registry[ShopItem]

        # Check admin has expected configuration
        assert 'sku' in admin_class.list_display
        assert 'name' in admin_class.list_display
        assert 'price' in admin_class.list_display
        assert 'active' in admin_class.list_display
        assert 'created_at' in admin_class.list_display

    def test_active_field_filtering(self):
        """Can filter ShopItems by active status."""
        from apps.shop.models import ShopItem

        # Create active and inactive items (in addition to autouse fixture items)
        active_1 = ShopItem.objects.create(sku='ACTIVE_1', name='Active Item', price=Decimal('25.00'), active=True)
        inactive_1 = ShopItem.objects.create(sku='INACTIVE_1', name='Inactive Item', price=Decimal('30.00'), active=False)
        active_2 = ShopItem.objects.create(sku='ACTIVE_2', name='Another Active', price=Decimal('45.00'), active=True)

        # Filter for just our test items
        test_skus = ['ACTIVE_1', 'INACTIVE_1', 'ACTIVE_2']
        active_items = ShopItem.objects.filter(active=True, sku__in=test_skus)
        assert active_items.count() == 2
        assert all(item.active for item in active_items)

        # Filter inactive only from our test items
        inactive_items = ShopItem.objects.filter(active=False, sku__in=test_skus)
        assert inactive_items.count() == 1
        assert not inactive_items.first().active
