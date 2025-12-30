"""
Profile V3 Template Integration Tests
Tests that the new Profile V3 template renders correctly with real backend data.
"""

import pytest
from django.test import Client, TestCase
from django.contrib.auth.models import User
from apps.user_profile.models import UserProfile, GameProfile, ProfileAboutItem, SocialLink


class ProfileV3TemplateTests(TestCase):
    """Test suite for Profile V3 template rendering."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        
        # Create test user
        self.test_user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        
        # Create profile
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.test_user,
            defaults={
                'display_name': 'Test Player',
                'bio': 'This is a test bio for Profile V3',
                'country': 'US',
                'level': 10
            }
        )
    
    def test_profile_page_loads_successfully(self):
        """Test that profile page returns 200 status."""
        response = self.client.get(f'/@{self.test_user.username}/')
        self.assertEqual(response.status_code, 200)
    
    def test_profile_uses_v3_template(self):
        """Test that the view uses public_v3.html template."""
        response = self.client.get(f'/@{self.test_user.username}/')
        self.assertTemplateUsed(response, 'user_profile/profile/public_v3.html')
    
    def test_hero_section_renders(self):
        """Test that hero section contains key identity elements."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        # Check for key hero elements
        self.assertIn('profile-hero', content)
        self.assertIn('Test Player', content)
        self.assertIn('@testplayer', content)
        self.assertIn('Lvl 10', content)
    
    def test_required_css_and_js_loaded(self):
        """Test that Profile V3 assets are linked."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('profile_v3.css', content)
        self.assertIn('profile_v3.js', content)
    
    def test_bio_renders_correctly(self):
        """Test that bio text appears in the template."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('This is a test bio for Profile V3', content)
    
    def test_follower_stats_display(self):
        """Test that follower/following stats render."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('Followers', content)
        self.assertIn('Following', content)
        self.assertIn('follower-count', content)
    
    def test_three_column_grid_structure(self):
        """Test that the 3-column grid structure exists."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('profile-grid', content)
        self.assertIn('profile-sidebar-left', content)
        self.assertIn('profile-main', content)
        self.assertIn('profile-sidebar-right', content)
    
    def test_owner_sees_edit_button(self):
        """Test that profile owner sees Edit Profile button."""
        self.client.login(username='testplayer', password='testpass123')
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('Edit Profile', content)
        self.assertIn('profile_settings_v2', content)
    
    def test_non_owner_sees_follow_button(self):
        """Test that spectators see Follow button instead of Edit."""
        # Create different user
        other_user = User.objects.create_user(
            username='spectator',
            password='testpass123'
        )
        self.client.login(username='spectator', password='testpass123')
        
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('follow-btn', content)
        self.assertIn('Follow', content)
        self.assertNotIn('Edit Profile', content)
    
    def test_game_passports_section_exists(self):
        """Test that Game Passports section container exists."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('Game Passports', content)
    
    def test_empty_state_for_owner_with_no_passports(self):
        """Test that owner sees CTA when no game passports exist."""
        self.client.login(username='testplayer', password='testpass123')
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        # Should show empty state with link to settings
        self.assertIn('Create Game Passport', content)
        self.assertIn('game-passports', content)
    
    def test_about_section_renders_when_items_exist(self):
        """Test that About section renders with ProfileAboutItem data."""
        # Create about item
        ProfileAboutItem.objects.create(
            user=self.test_user,
            type='location',
            display_text='San Francisco, CA',
            icon_emoji='📍',
            visibility='public'
        )
        
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('About', content)
        self.assertIn('San Francisco, CA', content)
        self.assertIn('📍', content)
    
    def test_social_links_render_when_exist(self):
        """Test that social links render from SocialLink model."""
        SocialLink.objects.create(
            user=self.test_user,
            platform='twitter',
            handle='testplayer',
            url='https://twitter.com/testplayer'
        )
        
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('Social Links', content)
        self.assertIn('twitter.com', content)
        self.assertIn('@testplayer', content)
    
    def test_owner_sees_wallet_section(self):
        """Test that only profile owner sees Wallet section."""
        self.profile.deltacoin_balance = 1500
        self.profile.lifetime_earnings = 5000
        self.profile.save()
        
        self.client.login(username='testplayer', password='testpass123')
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('Wallet', content)
        self.assertIn('1500', content)
        self.assertIn('5000', content)
        self.assertIn('View-only', content)
    
    def test_spectator_does_not_see_wallet(self):
        """Test that non-owners don't see Wallet section."""
        other_user = User.objects.create_user(
            username='spectator2',
            password='testpass123'
        )
        self.client.login(username='spectator2', password='testpass123')
        
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        # Wallet section should not appear for spectators
        self.assertNotIn('View-only. Managed by Economy system.', content)
    
    def test_no_console_errors_in_template(self):
        """Test that template has no obvious syntax errors."""
        response = self.client.get(f'/@{self.test_user.username}/')
        
        # Should render without 500 error
        self.assertEqual(response.status_code, 200)
        
        # Should not have Django error markers
        content = response.content.decode('utf-8')
        self.assertNotIn('TemplateSyntaxError', content)
        self.assertNotIn('VariableDoesNotExist', content)
    
    def test_responsive_classes_present(self):
        """Test that responsive design classes exist."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        # Check for responsive utility classes
        self.assertIn('flex', content)
        self.assertIn('gap', content)
        self.assertIn('grid', content)
    
    def test_profile_public_id_displays_if_exists(self):
        """Test that public_id displays when set."""
        self.profile.public_id = 'DC-12345'
        self.profile.save()
        
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('Public ID', content)
        self.assertIn('DC-12345', content)
        self.assertIn('copy-public-id', content)
    
    def test_profile_v3_container_exists(self):
        """Test that the main V3 container wrapper exists."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('profile-v3-container', content)


class ProfileV3DataIntegrationTests(TestCase):
    """Test that Profile V3 correctly uses backend data (no hardcoded values)."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.test_user = User.objects.create_user(
            username='datatest',
            password='testpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.test_user,
            defaults={'display_name': 'Data Test User'}
        )
    
    def test_no_hardcoded_game_names(self):
        """Test that no hardcoded game names appear in template."""
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        # Should NOT contain hardcoded examples like "Valorant" or "League of Legends"
        # unless they come from the database
        # This test passes if template renders without fake game data
        self.assertNotIn('Example Game', content)
        self.assertNotIn('Placeholder', content)
    
    def test_stats_use_real_backend_values(self):
        """Test that stats come from UserProfileStats model."""
        from apps.user_profile.models import UserProfileStats
        
        # Create real stats
        stats, _ = UserProfileStats.objects.get_or_create(
            user_profile=self.profile,
            defaults={
                'total_matches': 42,
                'total_wins': 28,
                'tournaments_played': 5
            }
        )
        
        response = self.client.get(f'/@{self.test_user.username}/')
        content = response.content.decode('utf-8')
        
        self.assertIn('42', content)  # Total matches
        self.assertIn('28', content)  # Total wins
        self.assertIn('5', content)   # Tournaments played
    
    def test_follower_counts_from_follow_model(self):
        """Test that follower/following counts come from Follow model."""
        from apps.user_profile.models import Follow
        
        # Create followers
        follower1 = User.objects.create_user(username='follower1')
        follower2 = User.objects.create_user(username='follower2')
        
        Follow.objects.create(follower=follower1, following=self.test_user)
        Follow.objects.create(follower=follower2, following=self.test_user)
        
        response = self.client.get(f'/@{self.test_user.username}/')
        
        # Should show 2 followers
        self.assertContains(response, 'follower-count')
        self.assertContains(response, '2')


@pytest.mark.django_db
class TestProfileV3Smoke:
    """Pytest-style smoke tests for Profile V3."""
    
    def test_profile_v3_loads_for_any_user(self, client):
        """Smoke test: Any valid user profile should load."""
        user = User.objects.create_user(username='smoketest', password='test')
        UserProfile.objects.get_or_create(user=user, defaults={'display_name': 'Smoke Test'})
        
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        assert b'profile-v3-container' in response.content
    
    def test_profile_v3_anonymous_access(self, client):
        """Smoke test: Anonymous users can view public profiles."""
        user = User.objects.create_user(username='publicuser', password='test')
        UserProfile.objects.get_or_create(user=user, defaults={'display_name': 'Public User'})
        
        # Don't login - test anonymous access
        response = client.get(f'/@{user.username}/')
        assert response.status_code == 200
        assert b'Follow' in response.content  # Should show Follow button, not Edit
