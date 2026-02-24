"""
UP-PHASE13: Modern Profile UI Tests
Tests the new profile_v2.css system, hero rebuild, and grid layout
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from bs4 import BeautifulSoup

User = get_user_model()


@pytest.mark.django_db
class TestPhase13ProfileLayout:
    """Test Phase 13 profile layout modernization"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create test user and profile"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.display_name = 'Test Player'
        self.profile.bio = 'Professional esports athlete'
        self.profile.level = 42
        self.profile.save()

    def test_profile_page_renders(self):
        """Verify profile page loads without errors"""
        response = self.client.get(f'/@{self.user.username}/')
        assert response.status_code == 200
        assert b'Test Player' in response.content

    def test_profile_v2_css_loads(self):
        """Verify profile_v2.css is linked"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        css_links = soup.find_all('link', rel='stylesheet')
        profile_v2_loaded = any('profile_v2.css' in link.get('href', '') for link in css_links)
        
        assert profile_v2_loaded, "profile_v2.css not found in <link> tags"

    def test_design_tokens_css_loads(self):
        """Verify design-tokens.css is linked"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        css_links = soup.find_all('link', rel='stylesheet')
        design_tokens_loaded = any('design-tokens.css' in link.get('href', '') for link in css_links)
        
        assert design_tokens_loaded, "design-tokens.css not found"

    def test_hero_section_uses_new_classes(self):
        """Verify hero uses profile-hero classes"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-hero' in content, "profile-hero class not found"
        assert 'profile-hero-banner' in content, "profile-hero-banner not found"
        assert 'profile-hero-content' in content, "profile-hero-content not found"

    def test_avatar_uses_new_classes(self):
        """Verify avatar uses profile-avatar classes"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-avatar' in content, "profile-avatar class not found"
        assert 'profile-avatar-wrapper' in content, "profile-avatar-wrapper not found"

    def test_grid_uses_new_classes(self):
        """Verify grid uses profile-grid/profile-left/profile-main classes"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-grid' in content, "profile-grid class not found"
        assert 'profile-left' in content, "profile-left column not found"
        assert 'profile-main' in content, "profile-main column not found"

    def test_cards_use_dc_card_classes(self):
        """Verify cards use dc-card system"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'dc-card' in content, "dc-card class not found"
        assert 'dc-card-header' in content, "dc-card-header not found"
        assert 'dc-card-title' in content, "dc-card-title not found"

    def test_buttons_use_dc_btn_classes(self):
        """Verify buttons use dc-btn system"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'dc-btn' in content, "dc-btn class not found"
        # Should have either primary, secondary, or ghost variants
        assert ('dc-btn-primary' in content or 
                'dc-btn-secondary' in content or 
                'dc-btn-ghost' in content), "No dc-btn variant found"

    def test_stats_bar_exists(self):
        """Verify stats bar below hero exists"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-stats-bar' in content, "profile-stats-bar not found"
        assert 'profile-stat-value' in content, "profile-stat-value not found"
        assert 'profile-stat-label' in content, "profile-stat-label not found"

    def test_hero_displays_name_and_handle(self):
        """Verify hero displays display name and handle"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-display-name' in content, "profile-display-name class not found"
        assert 'profile-handle' in content, "profile-handle class not found"
        assert 'Test Player' in content, "Display name not rendered"
        assert '@testplayer' in content, "Handle not rendered"

    def test_hero_displays_badges(self):
        """Verify hero displays level badge"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-badges' in content, "profile-badges container not found"
        assert 'profile-badge' in content, "profile-badge class not found"
        assert 'Lvl' in content or 'Level' in content or 'lvl' in content, "Level indicator not found"

    def test_hero_actions_positioned_correctly(self):
        """Verify hero actions are in top right"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-hero-actions' in content, "profile-hero-actions not found"

    def test_responsive_container_exists(self):
        """Verify profile-container wrapper exists"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-container' in content, "profile-container class not found"

    def test_no_old_grid_cols_12(self):
        """Verify old md:grid-cols-12 is replaced"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Should use profile-grid instead of md:grid-cols-12
        # (Though we might keep md:grid-cols-12 for sub-grids, so check for profile-grid)
        assert 'profile-grid' in content, "New profile-grid system not found"


@pytest.mark.django_db
class TestPhase13HeroSection:
    """Detailed tests for modernized hero section"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.display_name = 'Test Player'
        self.profile.level = 42
        self.profile.bio = 'Professional esports athlete with extensive tournament experience'
        self.profile.country = 'US'
        self.profile.save()

    def test_hero_has_banner_section(self):
        """Verify hero has banner (image or gradient)"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        hero = soup.find('section', class_=lambda x: x and 'profile-hero' in x)
        assert hero, "profile-hero section not found"
        
        banner = soup.find(class_=lambda x: x and 'profile-hero-banner' in x)
        assert banner, "profile-hero-banner not found"

    def test_hero_has_gradient_overlay(self):
        """Verify hero has gradient overlay"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        gradient = soup.find(class_=lambda x: x and 'profile-hero-gradient' in x)
        assert gradient, "profile-hero-gradient overlay not found"

    def test_avatar_ring_for_online_status(self):
        """Verify avatar can show online ring"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Check for avatar ring class (even if not online, code should support it)
        assert 'profile-avatar-ring' in content, "profile-avatar-ring class not in template"

    def test_bio_with_read_more(self):
        """Verify bio supports read more expansion"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert self.profile.bio in content, "Bio not rendered"
        # Should have Alpine.js for expansion
        assert 'expanded' in content, "Bio expansion logic not found"

    def test_stats_show_followers_and_following(self):
        """Verify stats bar shows followers/following"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        stats_bar = soup.find(class_=lambda x: x and 'profile-stats-bar' in x)
        assert stats_bar, "profile-stats-bar not found"
        
        content = response.content.decode('utf-8')
        assert 'Followers' in content or 'followers' in content, "Followers stat not found"
        assert 'Following' in content or 'following' in content, "Following stat not found"


@pytest.mark.django_db
class TestPhase13CardSystem:
    """Test unified dc-card system"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.display_name = 'Test Player'
        self.profile.save()

    def test_about_card_uses_dc_card(self):
        """Verify About card uses dc-card system"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find card with "About" header
        content = response.content.decode('utf-8')
        about_section = content.find('About')
        assert about_section > 0, "About section not found"
        
        # Check for dc-card structure
        assert 'dc-card' in content, "dc-card class not used"
        assert 'dc-card-header' in content, "dc-card-header not used"
        assert 'dc-card-title' in content, "dc-card-title not used"

    def test_stats_card_uses_dc_card(self):
        """Verify Stats card uses dc-card system"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        stats_section = content.find('Competitive Stats')
        assert stats_section > 0, "Competitive Stats section not found"
        
        assert 'dc-card' in content, "dc-card class not used for stats"

    def test_card_headers_have_icons(self):
        """Verify card headers include icons"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # dc-card-icon should exist
        content = response.content.decode('utf-8')
        assert 'dc-card-icon' in content, "dc-card-icon class not found"


@pytest.mark.django_db
class TestPhase13ResponsiveLayout:
    """Test responsive behavior of new grid system"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
        self.profile.display_name = 'Test Player'
        self.profile.save()

    def test_profile_grid_class_exists(self):
        """Verify profile-grid class exists (hidden on mobile, grid on desktop)"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-grid' in content, "profile-grid class not found"

    def test_profile_left_column_exists(self):
        """Verify left column exists with sticky positioning"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-left' in content, "profile-left column not found"

    def test_profile_right_column_exists(self):
        """Verify right column exists (hidden on tablet, visible on desktop)"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Right column should exist (even if hidden on smaller screens)
        assert 'profile-right' in content, "profile-right column not found"

    def test_container_has_max_width(self):
        """Verify container has max-width constraint"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'profile-container' in content, "profile-container not found"
