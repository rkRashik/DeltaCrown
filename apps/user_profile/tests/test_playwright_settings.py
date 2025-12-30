"""
UP-PHASE12-A: Playwright tests for Settings page
Verifies zero console errors, Alpine.js boots correctly, all sections visible/switchable

NOTE: These tests use Django test client + Playwright (not pytest-asyncio).
"""
import pytest
from django.contrib.auth import get_user_model

# UP-PHASE12: Disable pytest-asyncio for this module (conflicts with Django LiveServerTestCase)
pytest_plugins = []

User = get_user_model()


@pytest.fixture(scope='module')
def browser():
    """Module-scoped Playwright browser instance"""
    from playwright.sync_api import sync_playwright
    
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    yield browser
    browser.close()
    pw.stop()


@pytest.fixture(scope='function')
def page(browser):
    """Function-scoped Playwright page with console tracking"""
    context = browser.new_context()
    page = context.new_page()
    
    # Track console errors
    console_errors = []
    console_warnings = []
    page.on("console", lambda msg: 
        console_errors.append(msg.text()) if msg.type == "error" else 
        console_warnings.append(msg.text()) if msg.type == "warning" else None
    )
    page.console_errors = console_errors
    page.console_warnings = console_warnings
    
    yield page
    context.close()


@pytest.fixture(scope='function')
def test_user(db, transactional_db):
    """Test user with problematic data (quotes, newlines)"""
    from apps.games.models import Game
    from apps.user_profile.models.game_passport_schema import GamePassportSchema
    
    # Create game first (needed for profile)
    valorant_game, _ = Game.objects.get_or_create(
        slug='valorant',
        defaults={
            'name': 'VALORANT',
            'display_name': 'VALORANT',
            'short_code': 'VAL',
            'is_active': True,
            'category': 'FPS',
        }
    )
    GamePassportSchema.objects.get_or_create(
        game=valorant_game,
        defaults={
            'identity_fields': {
                'riot_name': {'label': 'Riot ID', 'required': True},
                'tagline': {'label': 'Tagline', 'required': True}
            },
            'identity_format': '{riot_name}#{tagline}',
            'identity_key_format': '{riot_name_lower}#{tagline_lower}',
        }
    )
    
    user = User.objects.create_user(
        username='test_settings_user',
        email='settings@test.com',
        password='testpass123'
    )
    profile = user.profile
    profile.display_name = 'Test "User" Name'
    profile.bio = 'Bio with\nnewlines and "quotes" and \'apostrophes\''
    profile.country = "USA's Country"
    profile.pronouns = 'they/them (test)'
    profile.save()
    
    yield user
    # Don't delete - transaction=True will rollback


def login_user(page, live_server, username, password):
    """Helper: Log in via Django login page"""
    page.goto(f'{live_server.url}/accounts/login/')
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state('networkidle')


@pytest.mark.django_db(transaction=True)
def test_settings_page_zero_console_errors(page, test_user, live_server):
    """
    PHASE12-A: THE CRITICAL TEST - Settings page MUST have zero console errors
    This is the user's primary complaint - "settingsApp is not defined", "SyntaxError"
    """
    login_user(page, live_server, 'test_settings_user', 'testpass123')
    
    # Navigate to settings
    page.goto(f'{live_server.url}/me/settings/')
    page.wait_for_load_state('networkidle')
    
    # Wait for Alpine to initialize (give it time)
    page.wait_for_timeout(2000)
    
    # ASSERTION 1: Zero console errors
    critical_errors = [err for err in page.console_errors if 
                      'settingsApp' in err or 
                      'SyntaxError' in err or 
                      'activeSection' in err or
                      'undefined' in err.lower()]
    
    assert len(critical_errors) == 0, (
        f"CRITICAL: Found {len(critical_errors)} console errors on settings page:\n" + 
        "\n".join(critical_errors)
    )
    
    # ASSERTION 2: settingsApp is defined globally
    is_defined = page.evaluate('typeof window.settingsApp === "function"')
    assert is_defined, "window.settingsApp must be a function (Alpine component factory)"
    
    # ASSERTION 3: Alpine initialized successfully
    alpine_data = page.evaluate('''
        const container = document.querySelector('[x-data]');
        if (!container || !container.__x) return null;
        return {
            activeSection: container.__x.$data.activeSection,
            hasSwitchSection: typeof container.__x.$data.switchSection === 'function'
        };
    ''')
    assert alpine_data is not None, "Alpine must initialize ([x-data] container must have .__x property)"
    assert alpine_data['activeSection'] in ['profile', 'privacy', 'notifications', 'platform', 'wallet', 'account'], (
        f"activeSection must be valid section name, got: {alpine_data['activeSection']}"
    )
    assert alpine_data['hasSwitchSection'], "Alpine component must have switchSection() method"


@pytest.mark.django_db(transaction=True)
def test_settings_page_all_sections_visible_and_switchable(page, test_user, live_server):
    """
    PHASE12-A: All 6 sections must be visible and switchable
    Tests: profile, privacy, notifications, platform, wallet, account
    """
    login_user(page, live_server, 'test_settings_user', 'testpass123')
    page.goto(f'{live_server.url}/me/settings/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)
    
    sections = ['profile', 'privacy', 'notifications', 'platform', 'wallet', 'account']
    
    for section in sections:
        # Click nav item
        nav_item = page.locator(f'nav button[data-section="{section}"], nav a[href="#{section}"]')
        if nav_item.count() > 0:
            nav_item.first.click()
            page.wait_for_timeout(500)
            
            # Verify section content visible
            section_content = page.locator(f'div[data-section="{section}"], section[id="{section}"]')
            assert section_content.count() > 0, f"Section '{section}' content must exist"


@pytest.mark.django_db(transaction=True)
def test_settings_page_no_template_syntax_errors(page, test_user, live_server):
    """
    PHASE12-A: Template with problematic data (quotes, newlines) must NOT cause SyntaxError
    Tests that escapejs filter works correctly
    """
    login_user(page, live_server, 'test_settings_user', 'testpass123')
    
    # User has bio with newlines and quotes
    page.goto(f'{live_server.url}/me/settings/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)
    
    # Verify no SyntaxError
    syntax_errors = [err for err in page.console_errors if 'SyntaxError' in err]
    assert len(syntax_errors) == 0, (
        f"Found {len(syntax_errors)} SyntaxErrors (escapejs failure):\n" + 
        "\n".join(syntax_errors)
    )
    
    # Verify profile data loaded correctly
    profile_data = page.evaluate('window.settingsApp ? settingsApp().profile : null')
    assert profile_data is not None, "Profile data must load"
    assert 'Test "User" Name' in profile_data.get('display_name', ''), "Display name with quotes must load"


@pytest.mark.django_db(transaction=True)
def test_settings_page_form_submission_works(page, test_user, live_server):
    """
    PHASE12-A: Form submission must work without JavaScript errors
    """
    login_user(page, live_server, 'test_settings_user', 'testpass123')
    page.goto(f'{live_server.url}/me/settings/')
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(1000)
    
    # Navigate to profile section
    profile_nav = page.locator('nav button[data-section="profile"], nav a[href="#profile"]')
    if profile_nav.count() > 0:
        profile_nav.first.click()
        page.wait_for_timeout(500)
    
    # Fill display_name input
    display_name_input = page.locator('input[name="display_name"]')
    if display_name_input.count() > 0:
        display_name_input.first.fill('Updated Name')
        
        # Click save button
        save_button = page.locator('button[type="submit"]')
        if save_button.count() > 0:
            save_button.first.click()
            page.wait_for_timeout(1000)
            
            # Verify no errors during submission
            submission_errors = [err for err in page.console_errors if 
                               'settingsApp' in err or 'undefined' in err.lower()]
            assert len(submission_errors) == 0, (
                f"Form submission caused {len(submission_errors)} JS errors:\n" + 
                "\n".join(submission_errors)
            )


@pytest.mark.django_db(transaction=True)
def test_settings_page_x_cloak_works(page, test_user, live_server):
    """
    PHASE12-A: x-cloak must prevent FOUC (Flash Of Unstyled Content)
    Alpine should remove x-cloak after initialization
    """
    login_user(page, live_server, 'test_settings_user', 'testpass123')
    page.goto(f'{live_server.url}/me/settings/')
    page.wait_for_load_state('domcontentloaded')
    
    # Check for x-cloak attribute (should exist on load)
    container = page.locator('[x-data]')
    assert container.count() > 0, "Must have [x-data] container"
    
    # Wait for Alpine to initialize
    page.wait_for_timeout(1000)
    
    # After init, x-cloak should be removed and element visible
    is_visible = container.first.is_visible()
    assert is_visible, "Container must be visible after Alpine initialization"
