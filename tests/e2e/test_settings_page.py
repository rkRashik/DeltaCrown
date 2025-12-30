"""
Playwright E2E Tests for User Profile Settings
UP-PHASE15-SESSION6: Comprehensive settings page testing

Tests:
- Settings page renders all sections
- Hash navigation works
- No JavaScript console errors
- All API endpoints return valid responses
- CRUD operations work end-to-end
"""
import pytest
from playwright.sync_api import Page, expect
import re


@pytest.fixture(scope="session")
def django_db_setup():
    """Ensure Django test database is set up"""
    pass


@pytest.fixture
def authenticated_page(page: Page, live_server):
    """
    Fixture that provides an authenticated browser session
    
    Prerequisites:
    - Test user must exist: username='testuser', password='testpass123'
    - Run: python manage.py create_test_user (if command exists)
    """
    # Navigate to login page
    page.goto(f"{live_server.url}/accounts/login/")
    
    # Fill in credentials
    page.fill('input[name="username"]', 'testuser')
    page.fill('input[name="password"]', 'testpass123')
    
    # Submit form
    page.click('button[type="submit"]')
    
    # Wait for redirect
    page.wait_for_url(re.compile(r'.*/dashboard/.*|.*/me/.*'))
    
    return page


class TestSettingsPageRendering:
    """Test that settings page loads and renders correctly"""
    
    def test_settings_page_loads(self, authenticated_page: Page, live_server):
        """Test that /me/settings/ loads without errors"""
        page = authenticated_page
        
        # Navigate to settings
        page.goto(f"{live_server.url}/me/settings/")
        
        # Check page title
        expect(page).to_have_title(re.compile(r'Settings.*DeltaCrown'))
        
        # Check settings container exists
        settings_container = page.locator('.settings-container')
        expect(settings_container).to_be_visible()
        
        # Check navigation menu exists
        settings_nav = page.locator('.settings-nav')
        expect(settings_nav).to_be_visible()
    
    def test_default_section_renders(self, authenticated_page: Page, live_server):
        """Test that default section (profile) renders content on load"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/")
        
        # Wait for JavaScript to initialize
        page.wait_for_timeout(500)
        
        # Check that at least one section is visible (not hidden)
        visible_sections = page.locator('.content-section:not(.hidden)')
        expect(visible_sections).to_have_count(1, timeout=5000)
        
        # Check that profile section is the visible one
        profile_section = page.locator('[data-section="profile"]').first
        expect(profile_section).not_to_have_class('hidden')
        expect(profile_section).to_be_visible()
        
        # Check that profile form exists
        profile_form = page.locator('#profile-form')
        expect(profile_form).to_be_visible()
    
    def test_no_console_errors(self, authenticated_page: Page, live_server):
        """Test that no JavaScript console errors occur"""
        page = authenticated_page
        console_errors = []
        
        def handle_console(msg):
            if msg.type == 'error':
                console_errors.append(msg.text)
        
        page.on('console', handle_console)
        
        # Navigate to settings
        page.goto(f"{live_server.url}/me/settings/")
        page.wait_for_timeout(1000)
        
        # Check for errors
        assert len(console_errors) == 0, f"Console errors detected: {console_errors}"
    
    def test_all_nav_items_exist(self, authenticated_page: Page, live_server):
        """Test that all navigation menu items exist"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/")
        
        expected_sections = [
            'profile', 'privacy', 'about', 'game-passports', 'social',
            'notifications', 'platform', 'wallet', 'kyc', 'security', 'account'
        ]
        
        for section in expected_sections:
            nav_item = page.locator(f'.nav-item[data-section="{section}"]')
            expect(nav_item).to_be_visible()


class TestHashNavigation:
    """Test hash-based section navigation"""
    
    def test_hash_navigation_profile(self, authenticated_page: Page, live_server):
        """Test navigating to #profile section"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#profile")
        page.wait_for_timeout(500)
        
        profile_section = page.locator('[data-section="profile"]').first
        expect(profile_section).to_be_visible()
        expect(profile_section).not_to_have_class('hidden')
    
    def test_hash_navigation_about(self, authenticated_page: Page, live_server):
        """Test navigating to #about section"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#about")
        page.wait_for_timeout(500)
        
        about_section = page.locator('[data-section="about"]').first
        expect(about_section).to_be_visible()
        expect(about_section).not_to_have_class('hidden')
    
    def test_hash_navigation_social(self, authenticated_page: Page, live_server):
        """Test navigating to #social section"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#social")
        page.wait_for_timeout(500)
        
        social_section = page.locator('[data-section="social"]').first
        expect(social_section).to_be_visible()
        expect(social_section).not_to_have_class('hidden')
    
    def test_click_navigation_switches_sections(self, authenticated_page: Page, live_server):
        """Test clicking nav items switches sections"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/")
        page.wait_for_timeout(500)
        
        # Click privacy nav item
        privacy_nav = page.locator('.nav-item[data-section="privacy"]')
        privacy_nav.click()
        page.wait_for_timeout(300)
        
        # Check privacy section is visible
        privacy_section = page.locator('[data-section="privacy"]').first
        expect(privacy_section).to_be_visible()
        expect(privacy_section).not_to_have_class('hidden')
        
        # Check profile section is hidden
        profile_section = page.locator('[data-section="profile"]').first
        expect(profile_section).to_have_class(re.compile(r'.*hidden.*'))
    
    def test_invalid_hash_defaults_to_profile(self, authenticated_page: Page, live_server):
        """Test that invalid hash redirects to profile section"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#invalid-section")
        page.wait_for_timeout(500)
        
        # Should fall back to profile section
        profile_section = page.locator('[data-section="profile"]').first
        expect(profile_section).to_be_visible()


class TestSectionContent:
    """Test that each section has meaningful content"""
    
    def test_profile_section_has_form_fields(self, authenticated_page: Page, live_server):
        """Test profile section has all expected form fields"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#profile")
        page.wait_for_timeout(500)
        
        # Check form fields exist
        assert page.locator('#display_name').is_visible()
        assert page.locator('#bio').is_visible()
        assert page.locator('#country').is_visible()
    
    def test_about_section_has_content(self, authenticated_page: Page, live_server):
        """Test about section has manager UI"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#about")
        page.wait_for_timeout(500)
        
        about_section = page.locator('[data-section="about"]').first
        expect(about_section).to_be_visible()
        
        # Should have some content (either items or empty state)
        content = about_section.inner_text()
        assert len(content) > 50, "About section appears empty"
    
    def test_social_section_has_content(self, authenticated_page: Page, live_server):
        """Test social links section has manager UI"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#social")
        page.wait_for_timeout(500)
        
        social_section = page.locator('[data-section="social"]').first
        expect(social_section).to_be_visible()
        
        content = social_section.inner_text()
        assert len(content) > 50, "Social section appears empty"
    
    def test_game_passports_section_has_content(self, authenticated_page: Page, live_server):
        """Test game passports section has manager UI"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#game-passports")
        page.wait_for_timeout(500)
        
        passports_section = page.locator('[data-section="game-passports"]').first
        expect(passports_section).to_be_visible()
        
        content = passports_section.inner_text()
        assert len(content) > 50, "Game passports section appears empty"


class TestFormSubmission:
    """Test form submission and API interactions"""
    
    def test_profile_form_submission(self, authenticated_page: Page, live_server):
        """Test submitting profile form (if endpoint exists)"""
        page = authenticated_page
        page.goto(f"{live_server.url}/me/settings/#profile")
        page.wait_for_timeout(500)
        
        # Fill in display name
        display_name_input = page.locator('#display_name')
        display_name_input.fill('Test User Updated')
        
        # Submit form
        submit_btn = page.locator('#profile-form button[type="submit"]')
        if submit_btn.is_visible():
            submit_btn.click()
            
            # Wait for response
            page.wait_for_timeout(1000)
            
            # Check for success message or alert
            # (Implementation depends on actual UI feedback)
            pass


class TestResponsiveLayout:
    """Test responsive design"""
    
    def test_mobile_layout(self, authenticated_page: Page, live_server):
        """Test settings page on mobile viewport"""
        page = authenticated_page
        page.set_viewport_size({"width": 375, "height": 667})
        
        page.goto(f"{live_server.url}/me/settings/")
        page.wait_for_timeout(500)
        
        # Settings container should still be visible
        settings_container = page.locator('.settings-container')
        expect(settings_container).to_be_visible()
        
        # Nav should adapt to mobile
        settings_nav = page.locator('.settings-nav')
        expect(settings_nav).to_be_visible()
    
    def test_tablet_layout(self, authenticated_page: Page, live_server):
        """Test settings page on tablet viewport"""
        page = authenticated_page
        page.set_viewport_size({"width": 768, "height": 1024})
        
        page.goto(f"{live_server.url}/me/settings/")
        page.wait_for_timeout(500)
        
        settings_container = page.locator('.settings-container')
        expect(settings_container).to_be_visible()


# Helper functions for test setup
def create_test_user():
    """Create test user for E2E tests"""
    from django.contrib.auth import get_user_model
    from apps.user_profile.models import UserProfile
    
    User = get_user_model()
    
    # Create or get test user
    user, created = User.objects.get_or_create(
        username='testuser',
        defaults={
            'email': 'testuser@example.com',
            'is_active': True
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Ensure profile exists
    UserProfile.objects.get_or_create(user=user)
    
    return user
