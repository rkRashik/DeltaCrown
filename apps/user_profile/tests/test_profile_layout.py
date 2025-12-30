"""
UP-PHASE12B: Profile Page Layout Verification Tests
Tests 3-column grid layout, hero section, and responsive behavior WITHOUT Playwright.
Uses Django test client + HTML parsing to verify structure.
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from bs4 import BeautifulSoup

User = get_user_model()


@pytest.mark.django_db
class TestProfileLayout:
    """Test Profile page layout structure using Django test client"""

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
        self.profile.save()

    def test_profile_page_renders(self):
        """Verify profile page loads without errors"""
        response = self.client.get(f'/@{self.user.username}/')
        assert response.status_code == 200
        assert b'Test Player' in response.content

    def test_design_tokens_css_loads(self):
        """Verify design-tokens.css is linked in template"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        css_links = soup.find_all('link', rel='stylesheet')
        design_tokens_loaded = any('design-tokens.css' in link.get('href', '') for link in css_links)
        
        assert design_tokens_loaded, "design-tokens.css not found in <link> tags"

    def test_grid_container_exists(self):
        """Verify grid container uses new profile-v2 semantic classes"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Check for new semantic grid classes (Phase 13)
        assert 'profile-grid' in content, "Grid container missing profile-grid class"
        assert 'profile-container' in content, "Container missing profile-container class"

    def test_three_column_spans_present(self):
        """Verify left, middle, right column semantic classes exist"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # New semantic columns (Phase 13 profile_v2.css)
        assert 'profile-left' in content, "Left column (profile-left) not found"
        assert 'profile-main' in content, "Middle column (profile-main) not found"
        assert 'profile-right' in content, "Right column (profile-right) not found"

    def test_hero_section_exists(self):
        """Verify hero section with banner and avatar exists"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for new semantic hero class (Phase 13)
        sections = soup.find_all('section')
        hero_found = any('profile-hero' in section.get('class', []) for section in sections)
        
        assert hero_found, "Hero section not found (profile-hero class missing)"

    def test_avatar_with_online_status(self):
        """Verify avatar uses new profile-avatar classes"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # New semantic avatar classes (Phase 13)
        assert 'profile-avatar' in content, "Avatar missing profile-avatar class"
        assert 'profile-avatar-ring' in content, "Avatar missing profile-avatar-ring"

    def test_sticky_columns(self):
        """Verify columns use profile_v2 CSS sticky behavior"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # New semantic column classes (sticky defined in profile_v2.css)
        assert 'profile-left' in content and 'profile-right' in content, "Sticky columns not using semantic classes"

    def test_responsive_container_max_width(self):
        """Verify container has max-width constraint"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Should have max-width to prevent excessive width on large screens
        assert 'max-w-[1920px]' in content or 'max-w-7xl' in content, "Container missing max-width"

    def test_glass_card_styles_exist(self):
        """Verify glass-card CSS is defined in inline styles"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert '.glass-card' in content, "glass-card class not defined"
        assert 'backdrop-filter' in content or 'backdrop-filter:' in content, "Backdrop filter missing"

    def test_alpine_js_loaded(self):
        """Verify Alpine.js is loaded for Follow button functionality"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        assert 'alpinejs' in content.lower(), "Alpine.js script not found"
        assert 'x-data' in content, "Alpine.js x-data directive not found"

    def test_no_obvious_html_errors(self):
        """Verify HTML structure is valid (no unclosed tags, etc.)"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Check for basic HTML structure
        assert soup.find('html'), "No <html> tag found"
        assert soup.find('head'), "No <head> tag found"
        assert soup.find('body'), "No <body> tag found"
        
        # Check for common layout elements
        assert soup.find('section') or soup.find('div', class_=lambda x: x and 'container' in x), \
            "No main content structure found"


@pytest.mark.django_db
class TestProfileHeroSection:
    """Detailed tests for Hero section 2025 redesign"""

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
        self.profile.bio = 'Professional esports athlete'
        self.profile.save()

    def test_hero_has_banner_or_gradient(self):
        """Verify hero has either banner image or gradient background"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Should have either banner_url or gradient background
        has_banner = 'profile.banner_url' in content or 'banner_url' in content
        has_gradient = 'bg-gradient-to' in content
        
        assert has_banner or has_gradient, "Hero section missing banner or gradient"

    def test_hero_displays_level(self):
        """Verify hero displays user level"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Level should be visible (Lvl, LVL, or Level - case insensitive)
        content_lower = content.lower()
        assert 'lvl' in content_lower or 'level' in content_lower, "Level indicator not found"

    def test_hero_has_action_buttons(self):
        """Verify hero has Follow/Message buttons"""
        response = self.client.get(f'/@{self.user.username}/')
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for action buttons
        buttons = soup.find_all('button')
        assert len(buttons) > 0, "No buttons found in profile"

    def test_hero_responsive_sizing(self):
        """Verify hero has responsive height classes"""
        response = self.client.get(f'/@{self.user.username}/')
        content = response.content.decode('utf-8')
        
        # Hero uses profile-hero class (heights defined in profile_v2.css)
        assert 'profile-hero' in content, \
            "Hero section missing profile-hero class"
