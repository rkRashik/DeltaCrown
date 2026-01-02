# apps/economy/tests/test_phase3a_inventory.py
"""
Phase 3A: Inventory System Tests
Comprehensive test coverage for inventory, gifting, trading with visibility enforcement.
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError

from apps.economy.models import (
    InventoryItem,
    UserInventoryItem,
    GiftRequest,
    TradeRequest
)
from apps.economy.inventory_services import (
    can_view_inventory,
    process_gift_accept,
    process_trade_accept
)
from apps.user_profile.models import UserProfile, PrivacySettings, Follow

User = get_user_model()


class InventoryModelTest(TestCase):
    """Test inventory item models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        
        self.item = InventoryItem.objects.create(
            slug='awp-dragon-lore',
            name='AWP | Dragon Lore',
            description='Legendary AWP skin',
            item_type=InventoryItem.ItemType.COSMETIC,
            rarity=InventoryItem.Rarity.LEGENDARY,
            tradable=True,
            giftable=True
        )
    
    def test_inventory_item_creation(self):
        """Test creating inventory items"""
        self.assertEqual(self.item.slug, 'awp-dragon-lore')
        self.assertEqual(self.item.name, 'AWP | Dragon Lore')
        self.assertTrue(self.item.tradable)
        self.assertTrue(self.item.giftable)
    
    def test_user_inventory_item_creation(self):
        """Test user acquiring inventory items"""
        user_item = UserInventoryItem.objects.create(
            profile=self.profile,
            item=self.item,
            quantity=2,
            acquired_from=UserInventoryItem.AcquiredFrom.PURCHASE
        )
        
        self.assertEqual(user_item.quantity, 2)
        self.assertFalse(user_item.locked)
        self.assertTrue(user_item.can_trade())
        self.assertTrue(user_item.can_gift())
    
    def test_locked_item_cannot_trade_or_gift(self):
        """Test locked items cannot be traded/gifted"""
        user_item = UserInventoryItem.objects.create(
            profile=self.profile,
            item=self.item,
            quantity=1,
            locked=True,
            acquired_from=UserInventoryItem.AcquiredFrom.REWARD
        )
        
        self.assertFalse(user_item.can_trade())
        self.assertFalse(user_item.can_gift())


class InventoryVisibilityTest(TestCase):
    """Test inventory visibility enforcement"""
    
    def setUp(self):
        # Owner
        self.owner_user = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='pass123'
        )
        self.owner_profile, _ = UserProfile.objects.get_or_create(user=self.owner_user)
        
        # Viewer (friend)
        self.friend_user = User.objects.create_user(
            username='friend',
            email='friend@example.com',
            password='pass123'
        )
        self.friend_profile, _ = UserProfile.objects.get_or_create(user=self.friend_user)
        
        # Stranger
        self.stranger_user = User.objects.create_user(
            username='stranger',
            email='stranger@example.com',
            password='pass123'
        )
        self.stranger_profile, _ = UserProfile.objects.get_or_create(user=self.stranger_user)
        
        # Setup privacy settings
        self.privacy, _ = PrivacySettings.objects.get_or_create(
            user_profile=self.owner_profile
        )
    
    def test_public_inventory_visible_to_anyone(self):
        """Test PUBLIC inventory is visible to everyone"""
        self.privacy.inventory_visibility = 'PUBLIC'
        self.privacy.save()
        
        # Owner can view
        self.assertTrue(can_view_inventory(self.owner_profile, self.owner_profile))
        # Friend can view
        self.assertTrue(can_view_inventory(self.friend_profile, self.owner_profile))
        # Stranger can view
        self.assertTrue(can_view_inventory(self.stranger_profile, self.owner_profile))
        # Anonymous can view
        self.assertTrue(can_view_inventory(None, self.owner_profile))
    
    def test_private_inventory_only_owner(self):
        """Test PRIVATE inventory only visible to owner"""
        self.privacy.inventory_visibility = 'PRIVATE'
        self.privacy.save()
        
        # Owner can view
        self.assertTrue(can_view_inventory(self.owner_profile, self.owner_profile))
        # Friend CANNOT view
        self.assertFalse(can_view_inventory(self.friend_profile, self.owner_profile))
        # Stranger CANNOT view
        self.assertFalse(can_view_inventory(self.stranger_profile, self.owner_profile))
        # Anonymous CANNOT view
        self.assertFalse(can_view_inventory(None, self.owner_profile))
    
    def test_friends_inventory_respects_follow(self):
        """Test FRIENDS inventory visible to followers"""
        self.privacy.inventory_visibility = 'FRIENDS'
        self.privacy.save()
        
        # Before following: friend CANNOT view
        self.assertFalse(can_view_inventory(self.friend_profile, self.owner_profile))
        
        # Friend follows owner
        Follow.objects.create(follower=self.friend_user, following=self.owner_user)
        
        # After following: friend CAN view
        self.assertTrue(can_view_inventory(self.friend_profile, self.owner_profile))
        
        # Stranger still CANNOT view
        self.assertFalse(can_view_inventory(self.stranger_profile, self.owner_profile))


class GiftingTest(TestCase):
    """Test gifting functionality"""
    
    def setUp(self):
        # Sender
        self.sender_user = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='pass123'
        )
        self.sender_profile, _ = UserProfile.objects.get_or_create(user=self.sender_user)
        
        # Receiver
        self.receiver_user = User.objects.create_user(
            username='receiver',
            email='receiver@example.com',
            password='pass123'
        )
        self.receiver_profile, _ = UserProfile.objects.get_or_create(user=self.receiver_user)
        
        # Giftable item
        self.item = InventoryItem.objects.create(
            slug='birthday-badge',
            name='Birthday Badge',
            item_type=InventoryItem.ItemType.BADGE,
            rarity=InventoryItem.Rarity.RARE,
            tradable=False,
            giftable=True
        )
        
        # Sender owns item
        self.sender_inventory = UserInventoryItem.objects.create(
            profile=self.sender_profile,
            item=self.item,
            quantity=5,
            acquired_from=UserInventoryItem.AcquiredFrom.REWARD
        )
    
    def test_gift_creation_succeeds(self):
        """Test creating a valid gift request"""
        gift = GiftRequest(
            sender_profile=self.sender_profile,
            receiver_profile=self.receiver_profile,
            item=self.item,
            quantity=2,
            message='Happy birthday!'
        )
        gift.full_clean()  # Should not raise
        gift.save()
        
        self.assertEqual(gift.status, GiftRequest.Status.PENDING)
        self.assertEqual(gift.quantity, 2)
    
    def test_gift_to_self_fails(self):
        """Test cannot gift to yourself"""
        gift = GiftRequest(
            sender_profile=self.sender_profile,
            receiver_profile=self.sender_profile,  # Same as sender
            item=self.item,
            quantity=1
        )
        
        with self.assertRaises(ValidationError):
            gift.full_clean()
    
    def test_gift_non_giftable_item_fails(self):
        """Test cannot gift non-giftable items"""
        non_giftable = InventoryItem.objects.create(
            slug='non-giftable-item',
            name='Non-Giftable Item',
            item_type=InventoryItem.ItemType.TOKEN,
            rarity=InventoryItem.Rarity.COMMON,
            tradable=False,
            giftable=False
        )
        
        UserInventoryItem.objects.create(
            profile=self.sender_profile,
            item=non_giftable,
            quantity=1,
            acquired_from=UserInventoryItem.AcquiredFrom.PURCHASE
        )
        
        gift = GiftRequest(
            sender_profile=self.sender_profile,
            receiver_profile=self.receiver_profile,
            item=non_giftable,
            quantity=1
        )
        
        with self.assertRaises(ValidationError) as ctx:
            gift.full_clean()
        
        self.assertIn('not giftable', str(ctx.exception))
    
    def test_gift_insufficient_quantity_fails(self):
        """Test cannot gift more than owned"""
        gift = GiftRequest(
            sender_profile=self.sender_profile,
            receiver_profile=self.receiver_profile,
            item=self.item,
            quantity=10  # Sender only has 5
        )
        
        with self.assertRaises(ValidationError) as ctx:
            gift.full_clean()
        
        self.assertIn('Insufficient quantity', str(ctx.exception))
    
    def test_gift_locked_item_fails(self):
        """Test cannot gift locked items"""
        self.sender_inventory.locked = True
        self.sender_inventory.save()
        
        gift = GiftRequest(
            sender_profile=self.sender_profile,
            receiver_profile=self.receiver_profile,
            item=self.item,
            quantity=1
        )
        
        with self.assertRaises(ValidationError) as ctx:
            gift.full_clean()
        
        self.assertIn('locked', str(ctx.exception).lower())
    
    def test_gift_accept_transfers_items(self):
        """Test accepting gift transfers items atomically"""
        gift = GiftRequest.objects.create(
            sender_profile=self.sender_profile,
            receiver_profile=self.receiver_profile,
            item=self.item,
            quantity=2
        )
        
        # Accept gift
        process_gift_accept(gift)
        
        # Verify sender quantity decreased
        self.sender_inventory.refresh_from_db()
        self.assertEqual(self.sender_inventory.quantity, 3)  # 5 - 2 = 3
        
        # Verify receiver got item
        receiver_inventory = UserInventoryItem.objects.get(
            profile=self.receiver_profile,
            item=self.item
        )
        self.assertEqual(receiver_inventory.quantity, 2)
        self.assertEqual(receiver_inventory.acquired_from, UserInventoryItem.AcquiredFrom.GIFT)
        
        # Verify gift status updated
        gift.refresh_from_db()
        self.assertEqual(gift.status, GiftRequest.Status.ACCEPTED)
        self.assertIsNotNone(gift.resolved_at)


class TradingTest(TestCase):
    """Test trading functionality"""
    
    def setUp(self):
        # Initiator
        self.initiator_user = User.objects.create_user(
            username='initiator',
            email='init@example.com',
            password='pass123'
        )
        self.initiator_profile, _ = UserProfile.objects.get_or_create(user=self.initiator_user)
        
        # Target
        self.target_user = User.objects.create_user(
            username='target',
            email='target@example.com',
            password='pass123'
        )
        self.target_profile, _ = UserProfile.objects.get_or_create(user=self.target_user)
        
        # Tradable items
        self.item_a = InventoryItem.objects.create(
            slug='item-a',
            name='Item A',
            item_type=InventoryItem.ItemType.COSMETIC,
            rarity=InventoryItem.Rarity.RARE,
            tradable=True,
            giftable=False
        )
        
        self.item_b = InventoryItem.objects.create(
            slug='item-b',
            name='Item B',
            item_type=InventoryItem.ItemType.COSMETIC,
            rarity=InventoryItem.Rarity.EPIC,
            tradable=True,
            giftable=False
        )
        
        # Initiator owns item A
        self.initiator_inventory = UserInventoryItem.objects.create(
            profile=self.initiator_profile,
            item=self.item_a,
            quantity=3,
            acquired_from=UserInventoryItem.AcquiredFrom.PURCHASE
        )
        
        # Target owns item B
        self.target_inventory = UserInventoryItem.objects.create(
            profile=self.target_profile,
            item=self.item_b,
            quantity=2,
            acquired_from=UserInventoryItem.AcquiredFrom.REWARD
        )
    
    def test_trade_creation_succeeds(self):
        """Test creating a valid trade request"""
        trade = TradeRequest(
            initiator_profile=self.initiator_profile,
            target_profile=self.target_profile,
            offered_item=self.item_a,
            offered_quantity=1,
            requested_item=self.item_b,
            requested_quantity=1
        )
        trade.full_clean()  # Should not raise
        trade.save()
        
        self.assertEqual(trade.status, TradeRequest.Status.PENDING)
    
    def test_trade_with_self_fails(self):
        """Test cannot trade with yourself"""
        trade = TradeRequest(
            initiator_profile=self.initiator_profile,
            target_profile=self.initiator_profile,  # Same as initiator
            offered_item=self.item_a,
            offered_quantity=1
        )
        
        with self.assertRaises(ValidationError):
            trade.full_clean()
    
    def test_trade_non_tradable_item_fails(self):
        """Test cannot trade non-tradable items"""
        non_tradable = InventoryItem.objects.create(
            slug='non-tradable',
            name='Non-Tradable',
            item_type=InventoryItem.ItemType.BADGE,
            rarity=InventoryItem.Rarity.COMMON,
            tradable=False,
            giftable=False
        )
        
        UserInventoryItem.objects.create(
            profile=self.initiator_profile,
            item=non_tradable,
            quantity=1,
            acquired_from=UserInventoryItem.AcquiredFrom.ADMIN
        )
        
        trade = TradeRequest(
            initiator_profile=self.initiator_profile,
            target_profile=self.target_profile,
            offered_item=non_tradable,
            offered_quantity=1
        )
        
        with self.assertRaises(ValidationError) as ctx:
            trade.full_clean()
        
        self.assertIn('not tradable', str(ctx.exception))
    
    def test_trade_accept_swaps_items(self):
        """Test accepting trade swaps items atomically"""
        trade = TradeRequest.objects.create(
            initiator_profile=self.initiator_profile,
            target_profile=self.target_profile,
            offered_item=self.item_a,
            offered_quantity=1,
            requested_item=self.item_b,
            requested_quantity=1
        )
        
        # Accept trade
        process_trade_accept(trade)
        
        # Verify initiator lost item A
        self.initiator_inventory.refresh_from_db()
        self.assertEqual(self.initiator_inventory.quantity, 2)  # 3 - 1 = 2
        
        # Verify initiator gained item B
        initiator_item_b = UserInventoryItem.objects.get(
            profile=self.initiator_profile,
            item=self.item_b
        )
        self.assertEqual(initiator_item_b.quantity, 1)
        
        # Verify target lost item B
        self.target_inventory.refresh_from_db()
        self.assertEqual(self.target_inventory.quantity, 1)  # 2 - 1 = 1
        
        # Verify target gained item A
        target_item_a = UserInventoryItem.objects.get(
            profile=self.target_profile,
            item=self.item_a
        )
        self.assertEqual(target_item_a.quantity, 1)
        
        # Verify trade status updated
        trade.refresh_from_db()
        self.assertEqual(trade.status, TradeRequest.Status.ACCEPTED)
        self.assertIsNotNone(trade.resolved_at)


class InventoryAPITest(TestCase):
    """Test inventory API endpoints"""
    
    def setUp(self):
        self.client = Client()
        
        # Create user
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='pass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        
        # Create items
        self.item = InventoryItem.objects.create(
            slug='test-item',
            name='Test Item',
            item_type=InventoryItem.ItemType.COSMETIC,
            rarity=InventoryItem.Rarity.COMMON,
            tradable=True,
            giftable=True
        )
        
        UserInventoryItem.objects.create(
            profile=self.profile,
            item=self.item,
            quantity=5,
            acquired_from=UserInventoryItem.AcquiredFrom.PURCHASE
        )
    
    def test_my_inventory_requires_auth(self):
        """Test /me/inventory/ requires authentication"""
        response = self.client.get(reverse('economy:my_inventory'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_my_inventory_returns_items(self):
        """Test /me/inventory/ returns user's items"""
        self.client.force_login(self.user)
        response = self.client.get(reverse('economy:my_inventory'))
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertTrue(data['success'])
        self.assertEqual(data['data']['total_unique_items'], 1)
        self.assertEqual(data['data']['total_items'], 5)
        self.assertEqual(data['data']['items'][0]['item_slug'], 'test-item')
    
    def test_user_inventory_respects_privacy(self):
        """Test /profiles/<username>/inventory/ respects privacy"""
        # Set inventory to PRIVATE
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=self.profile)
        privacy.inventory_visibility = 'PRIVATE'
        privacy.save()
        
        # Create another user
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='pass123'
        )
        
        # Try to view as other user
        self.client.force_login(other_user)
        response = self.client.get(
            reverse('economy:user_inventory', kwargs={'username': 'apiuser'})
        )
        
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('private', data['error'].lower())
