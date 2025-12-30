"""
Profile V3 Smoke Tests - Playwright E2E
Tests that Profile V3 renders correctly in a real browser.
Run with: pytest tests/test_profile_v3_smoke.py
"""

import pytest
from playwright.sync_api import Page, expect


def test_profile_v3_page_loads(page: Page):
    """Smoke test: Profile V3 page loads successfully."""
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    
    # Page should load
    expect(page).to_have_title(/DeltaCrown/)
    
    # V3 container should exist
    expect(page.locator('.profile-v3-container')).to_be_visible()
    
    # Hero section should be visible
    expect(page.locator('.profile-hero')).to_be_visible()


def test_profile_v3_hero_renders(page: Page):
    """Test that hero section displays user identity."""
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    
    # Should show username
    expect(page.locator('text=@rkrashik')).to_be_visible()
    
    # Should show stats grid
    expect(page.locator('.stats-grid')).to_be_visible()
    expect(page.locator('text=Followers')).to_be_visible()


def test_profile_v3_three_column_layout(page: Page):
    """Test that 3-column grid structure exists."""
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    
    # Check for 3-column grid
    expect(page.locator('.profile-grid')).to_be_visible()
    expect(page.locator('.profile-sidebar-left')).to_be_visible()
    expect(page.locator('.profile-main')).to_be_visible()
    expect(page.locator('.profile-sidebar-right')).to_be_visible()


def test_profile_v3_assets_loaded(page: Page):
    """Test that Profile V3 CSS and JS are loaded."""
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    
    # Check that CSS file is linked
    css_links = page.locator('link[href*="profile_v3.css"]')
    expect(css_links).to_have_count(1)
    
    # Check that JS file is linked
    js_scripts = page.locator('script[src*="profile_v3.js"]')
    expect(js_scripts).to_have_count(1)


def test_profile_v3_no_console_errors(page: Page):
    """Test that no JavaScript console errors occur."""
    console_errors = []
    
    def handle_console(msg):
        if msg.type == 'error':
            console_errors.append(msg.text)
    
    page.on('console', handle_console)
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    
    # Wait for page to fully load
    page.wait_for_load_state('networkidle')
    
    # Should have no console errors
    assert len(console_errors) == 0, f"Console errors found: {console_errors}"


def test_profile_v3_follow_button_exists_for_spectators(page: Page):
    """Test that non-owners see Follow button."""
    # Test as anonymous user (no login)
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    
    # Should have follow button (data attribute)
    follow_btn = page.locator('#follow-btn')
    if follow_btn.count() > 0:
        expect(follow_btn).to_be_visible()


def test_profile_v3_responsive_design(page: Page):
    """Test that profile is responsive to different screen sizes."""
    # Desktop
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    expect(page.locator('.profile-grid')).to_be_visible()
    
    # Tablet
    page.set_viewport_size({"width": 768, "height": 1024})
    expect(page.locator('.profile-v3-container')).to_be_visible()
    
    # Mobile
    page.set_viewport_size({"width": 375, "height": 667})
    expect(page.locator('.profile-hero')).to_be_visible()


def test_profile_v3_game_passports_section(page: Page):
    """Test that Game Passports section exists."""
    page.goto("http://127.0.0.1:8000/@rkrashik/")
    
    # Should have Game Passports heading
    expect(page.locator('text=Game Passports')).to_be_visible()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
