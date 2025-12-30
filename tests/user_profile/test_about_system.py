"""
UP-PHASE15: Tests for ProfileAboutItem (Facebook-style About system)

Tests:
- Model creation and privacy
- API CRUD operations
- IDOR protection
- Privacy filtering
"""
import pytest
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, ProfileAboutItem

User = get_user_model()


@pytest.mark.django_db
class TestProfileAboutModel:
    """Test ProfileAboutItem model"""

    def test_create_about_item(self):
        """Test creating About item"""
        user = User.objects.create_user(username='testuser', password='test123')
        profile = UserProfile.objects.get(user=user)
        
        item = ProfileAboutItem.objects.create(
            user_profile=profile,
            item_type=ProfileAboutItem.TYPE_BIO,
            display_text='Professional Esports Player',
            icon_emoji='🎮',
            visibility=ProfileAboutItem.VISIBILITY_PUBLIC,
            order_index=0
        )
        
        assert item.id is not None
        assert item.display_text == 'Professional Esports Player'
        assert item.visibility == 'public'
        assert item.is_active is True

    def test_about_item_privacy_public(self):
        """Test public items visible to all"""
        user = User.objects.create_user(username='testuser', password='test123')
        profile = UserProfile.objects.get(user=user)
        
        item = ProfileAboutItem.objects.create(
            user_profile=profile,
            item_type=ProfileAboutItem.TYPE_BIO,
            display_text='Test',
            visibility=ProfileAboutItem.VISIBILITY_PUBLIC,
            order_index=0
        )
        
        # Owner can see
        assert item.can_be_viewed_by(user, is_follower=False)
        
        # Non-follower can see (public)
        other_user = User.objects.create_user(username='other', password='test123')
        assert item.can_be_viewed_by(other_user, is_follower=False)
        
        # Anonymous can see (public)
        assert item.can_be_viewed_by(None, is_follower=False)

    def test_about_item_privacy_followers_only(self):
        """Test followers-only items"""
        user = User.objects.create_user(username='testuser', password='test123')
        profile = UserProfile.objects.get(user=user)
        
        item = ProfileAboutItem.objects.create(
            user_profile=profile,
            item_type=ProfileAboutItem.TYPE_BIO,
            display_text='Followers only',
            visibility=ProfileAboutItem.VISIBILITY_FOLLOWERS,
            order_index=0
        )
        
        # Owner can see
        assert item.can_be_viewed_by(user, is_follower=False)
        
        other_user = User.objects.create_user(username='other', password='test123')
        
        # Non-follower cannot see
        assert not item.can_be_viewed_by(other_user, is_follower=False)
        
        # Follower can see
        assert item.can_be_viewed_by(other_user, is_follower=True)
        
        # Anonymous cannot see
        assert not item.can_be_viewed_by(None, is_follower=False)

    def test_about_item_privacy_private(self):
        """Test private items (owner only)"""
        user = User.objects.create_user(username='testuser', password='test123')
        profile = UserProfile.objects.get(user=user)
        
        item = ProfileAboutItem.objects.create(
            user_profile=profile,
            item_type=ProfileAboutItem.TYPE_BIO,
            display_text='Private note',
            visibility=ProfileAboutItem.VISIBILITY_PRIVATE,
            order_index=0
        )
        
        # Owner can see
        assert item.can_be_viewed_by(user, is_follower=False)
        
        other_user = User.objects.create_user(username='other', password='test123')
        
        # Other user cannot see (even if follower)
        assert not item.can_be_viewed_by(other_user, is_follower=False)
        assert not item.can_be_viewed_by(other_user, is_follower=True)
        
        # Anonymous cannot see
        assert not item.can_be_viewed_by(None, is_follower=False)


@pytest.mark.django_db
class TestProfileAboutAPI:
    """Test About API endpoints"""

    def test_create_about_item_api(self, client):
        """Test creating About item via API"""
        user = User.objects.create_user(username='testuser', password='test123')
        client.force_login(user)
        
        response = client.post('/api/profile/about/create/', {
            'item_type': 'bio',
            'display_text': 'Test bio',
            'icon_emoji': '👤',
            'visibility': 'public'
        }, content_type='application/json')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'item' in data
        assert data['item']['display_text'] == 'Test bio'

    def test_get_about_items_api(self, client):
        """Test retrieving About items via API"""
        user = User.objects.create_user(username='testuser', password='test123')
        profile = UserProfile.objects.get(user=user)
        
        # Create test items
        ProfileAboutItem.objects.create(
            user_profile=profile,
            item_type='bio',
            display_text='First item',
            visibility='public',
            order_index=0
        )
        ProfileAboutItem.objects.create(
            user_profile=profile,
            item_type='bio',
            display_text='Second item',
            visibility='public',
            order_index=1
        )
        
        client.force_login(user)
        response = client.get('/api/profile/about/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert len(data['items']) == 2
        assert data['items'][0]['display_text'] == 'First item'

    def test_update_about_item_api_requires_ownership(self, client):
        """Test IDOR protection on update"""
        user1 = User.objects.create_user(username='user1', password='test123')
        user2 = User.objects.create_user(username='user2', password='test123')
        
        profile1 = UserProfile.objects.get(user=user1)
        item = ProfileAboutItem.objects.create(
            user_profile=profile1,
            item_type='bio',
            display_text='User1 item',
            visibility='public',
            order_index=0
        )
        
        # user2 tries to update user1's item
        client.force_login(user2)
        response = client.post(f'/api/profile/about/{item.id}/update/', {
            'display_text': 'Hacked!'
        }, content_type='application/json')
        
        assert response.status_code == 404  # Item not found (ownership check)
        
        # Verify item unchanged
        item.refresh_from_db()
        assert item.display_text == 'User1 item'

    def test_delete_about_item_api_requires_ownership(self, client):
        """Test IDOR protection on delete"""
        user1 = User.objects.create_user(username='user1', password='test123')
        user2 = User.objects.create_user(username='user2', password='test123')
        
        profile1 = UserProfile.objects.get(user=user1)
        item = ProfileAboutItem.objects.create(
            user_profile=profile1,
            item_type='bio',
            display_text='User1 item',
            visibility='public',
            order_index=0
        )
        
        # user2 tries to delete user1's item
        client.force_login(user2)
        response = client.post(f'/api/profile/about/{item.id}/delete/')
        
        assert response.status_code == 404  # Item not found (ownership check)
        
        # Verify item still active
        item.refresh_from_db()
        assert item.is_active is True


@pytest.mark.django_db
class TestProfileAboutIntegration:
    """Test About section integration with profile view"""

    def test_profile_includes_about_items(self, client):
        """Test About items appear on profile page"""
        user = User.objects.create_user(username='testuser', password='test123')
        profile = UserProfile.objects.get(user=user)
        
        ProfileAboutItem.objects.create(
            user_profile=profile,
            item_type='bio',
            display_text='Professional Gamer',
            icon_emoji='🎮',
            visibility='public',
            order_index=0
        )
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Check About section present
        assert 'about-section' in content.lower() or 'About' in content
        assert 'Professional Gamer' in content

    def test_profile_filters_private_items(self, client):
        """Test private About items not visible to other users"""
        user1 = User.objects.create_user(username='user1', password='test123')
        user2 = User.objects.create_user(username='user2', password='test123')
        profile1 = UserProfile.objects.get(user=user1)
        
        # Public item
        ProfileAboutItem.objects.create(
            user_profile=profile1,
            item_type='bio',
            display_text='Public info',
            visibility='public',
            order_index=0
        )
        
        # Private item
        ProfileAboutItem.objects.create(
            user_profile=profile1,
            item_type='bio',
            display_text='Private secret',
            visibility='private',
            order_index=1
        )
        
        # user2 views user1's profile
        client.force_login(user2)
        response = client.get(f'/@{user1.username}/')
        content = response.content.decode('utf-8')
        
        # Public item visible
        assert 'Public info' in content
        
        # Private item NOT visible
        assert 'Private secret' not in content
