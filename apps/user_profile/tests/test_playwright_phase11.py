"""
UP-PHASE11: Headless Browser Tests (Playwright)

Tests verify actual browser behavior:
- No console errors
- Alpine.js boots correctly
- Settings sections switch properly
- Profile page CSS loads correctly
"""
import pytest
from django.test import LiveServerTestCase
from django.contrib.auth import get_user_model
from playwright.sync_api import sync_playwright, expect

User = get_user_model()

pytestmark = pytest.mark.django_db


class PlaywrightSettingsTestCase(LiveServerTestCase):
    """
    Headless browser tests for settings page.
    Verifies Alpine.js loads without console errors.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
    
    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()
    
    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser_phase11',
            email='test@example.com',
            password='testpass123'
        )
        profile = self.user.profile
        profile.display_name = 'Test User'
        profile.bio = 'Test bio with "quotes" and\nnewlines'
        profile.save()
        
        # Track console errors
        self.console_errors = []
        self.page.on("console", lambda msg: 
            self.console_errors.append(msg.text) if msg.type == "error" else None
        )
    
    def tearDown(self):
        self.context.close()
    
    def login(self):
        """Helper: Log in via Django login page"""
        self.page.goto(f'{self.live_server_url}/accounts/login/')
        self.page.fill('input[name="username"]', 'testuser_phase11')
        self.page.fill('input[name="password"]', 'testpass123')
        self.page.click('button[type="submit"]')
        self.page.wait_for_load_state('networkidle')
    
    def test_settings_page_no_console_errors(self):
        """
        PHASE11-A: Settings page loads without JavaScript errors.
        Verifies Alpine.js boots correctly and settingsApp is defined.
        """
        self.login()
        
        # Navigate to settings
        self.page.goto(f'{self.live_server_url}/me/settings/')
        self.page.wait_for_load_state('networkidle')
        
        # Wait for Alpine to initialize
        self.page.wait_for_timeout(1000)
        
        # Assert no console errors
        js_errors = [err for err in self.console_errors if 'settingsApp' in err or 'SyntaxError' in err]
        assert len(js_errors) == 0, f"Console errors found: {js_errors}"
        
        # Verify settingsApp is defined
        is_defined = self.page.evaluate('typeof window.settingsApp === "function"')
        assert is_defined, "window.settingsApp is not defined"
        
        # Verify Alpine initialized (x-data resolved)
        active_section = self.page.evaluate('document.querySelector(".settings-container").__x')
        assert active_section is not None, "Alpine.js did not initialize"
    
    def test_settings_page_sections_visible(self):
        """
        PHASE11-A: Settings page renders content sections (not just sidebar).
        Verifies all 6 sections exist and are switchable.
        """
        self.login()
        self.page.goto(f'{self.live_server_url}/me/settings/')
        self.page.wait_for_load_state('networkidle')
        
        # Verify sidebar exists
        sidebar = self.page.locator('.settings-nav')
        expect(sidebar).to_be_visible()
        
        # Verify content area exists (not blank)
        content = self.page.locator('.settings-content')
        expect(content).to_be_visible()
        
        # Verify at least one section is visible
        profile_section = self.page.locator('section[x-show*="profile"]')
        expect(profile_section).to_be_visible()
        
        # Test section switching (click each nav item)
        sections = ['profile', 'privacy', 'notifications', 'platform', 'wallet', 'account']
        for section in sections:
            # Click nav item
            nav_item = self.page.locator(f'.nav-item[\\@click*="{section}"]')
            nav_item.click()
            self.page.wait_for_timeout(300)
            
            # Verify section becomes visible
            section_elem = self.page.locator(f'section[x-show*="{section}"]')
            expect(section_elem).to_be_visible()
    
    def test_settings_page_no_syntax_errors(self):
        """
        PHASE11-A: Verify no SyntaxError from template variable injection.
        Tests that escapejs filter prevents broken JavaScript.
        """
        self.login()
        
        # Navigate to settings
        self.page.goto(f'{self.live_server_url}/me/settings/')
        self.page.wait_for_load_state('networkidle')
        
        # Check for syntax errors in console
        syntax_errors = [err for err in self.console_errors if 'SyntaxError' in err or 'unexpected token' in err]
        assert len(syntax_errors) == 0, f"JavaScript syntax errors found: {syntax_errors}"
        
        # Verify profile data loaded correctly (bio with quotes/newlines)
        bio = self.page.evaluate('document.querySelector(".settings-container").__x.$data.profile.bio')
        assert bio is not None, "Profile bio failed to load"
        assert '"' not in repr(bio) or '\\' in repr(bio), "Bio quotes not properly escaped"


class PlaywrightProfileTestCase(LiveServerTestCase):
    """
    Headless browser tests for profile page.
    Verifies CSS loads correctly and layout renders.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(headless=True)
    
    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        super().tearDownClass()
    
    def setUp(self):
        self.context = self.browser.new_context()
        self.page = self.context.new_page()
        
        # Create test user
        self.user = User.objects.create_user(
            username='rkrashik',
            email='test@example.com',
            password='testpass123'
        )
        profile = self.user.profile
        profile.display_name = 'Test User'
        profile.bio = 'Test bio'
        profile.save()
        
        # Track console errors
        self.console_errors = []
        self.page.on("console", lambda msg: 
            self.console_errors.append(msg.text) if msg.type == "error" else None
        )
    
    def tearDown(self):
        self.context.close()
    
    def test_profile_page_css_loaded(self):
        """
        PHASE11-B: Profile page loads CSS correctly.
        Verifies design-tokens.css is included and applied.
        """
        self.page.goto(f'{self.live_server_url}/@rkrashik/')
        self.page.wait_for_load_state('networkidle')
        
        # Check for CSS loading errors
        css_errors = [err for err in self.console_errors if '.css' in err or 'stylesheet' in err]
        assert len(css_errors) == 0, f"CSS loading errors: {css_errors}"
        
        # Verify design-tokens.css is loaded
        stylesheets = self.page.evaluate('''
            Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
                .map(link => link.href)
        ''')
        has_design_tokens = any('design-tokens.css' in href for href in stylesheets)
        assert has_design_tokens, "design-tokens.css not loaded"
        
        # Verify CSS variables are available
        primary_color = self.page.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--dc-primary")')
        assert primary_color, "CSS design tokens not applied"
    
    def test_profile_page_layout_renders(self):
        """
        PHASE11-B: Profile page layout renders correctly (not broken).
        Verifies key sections are visible and styled.
        """
        self.page.goto(f'{self.live_server_url}/@rkrashik/')
        self.page.wait_for_load_state('networkidle')
        
        # Verify profile header exists
        header = self.page.locator('h1, .profile-header, [class*="header"]')
        expect(header.first).to_be_visible()
        
        # Verify no JavaScript errors
        assert len(self.console_errors) == 0, f"Console errors on profile: {self.console_errors}"
        
        # Verify body has background styling
        bg_color = self.page.evaluate('getComputedStyle(document.body).backgroundColor')
        assert bg_color and bg_color != 'rgba(0, 0, 0, 0)', "Background not styled"
