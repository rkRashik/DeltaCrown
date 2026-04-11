"""
E2E Test Framework — Playwright-based browser tests for DeltaCrown.

This module provides base fixtures and helpers for end-to-end browser testing
of tournament registration, bracket generation, and match room flows.

Prerequisites:
    pip install playwright pytest-playwright
    playwright install chromium

Run:
    pytest tests/e2e/ -v --browser chromium
"""
from __future__ import annotations

import os
import pytest

# Skip all E2E tests if Playwright is not installed
pytest.importorskip("playwright", reason="Playwright not installed — pip install playwright pytest-playwright")


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def base_url():
    """Base URL for the test server."""
    return os.environ.get("E2E_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="session")
def admin_credentials():
    """Admin user credentials for E2E tests."""
    return {
        "username": os.environ.get("E2E_ADMIN_USER", "admin"),
        "password": os.environ.get("E2E_ADMIN_PASS", "admin"),
    }


@pytest.fixture
def authenticated_page(page, base_url, admin_credentials):
    """
    A Playwright page already logged in as admin.

    Usage:
        def test_dashboard(authenticated_page, base_url):
            authenticated_page.goto(f"{base_url}/dashboard/")
            assert authenticated_page.title()
    """
    page.goto(f"{base_url}/accounts/login/")
    page.fill('input[name="username"], input[name="login"]', admin_credentials["username"])
    page.fill('input[name="password"]', admin_credentials["password"])
    page.click('button[type="submit"]')
    page.wait_for_url(f"{base_url}/**")
    return page


# ── Helpers ──────────────────────────────────────────────────────────────

def wait_for_toast(page, text: str, timeout: int = 5000):
    """Wait for a toast notification containing the given text."""
    toast = page.locator(f".toast:has-text('{text}'), [role='alert']:has-text('{text}')")
    toast.wait_for(state="visible", timeout=timeout)
    return toast


def click_and_wait_for_api(page, selector: str, url_pattern: str, timeout: int = 10000):
    """Click an element and wait for an API response matching the URL pattern."""
    with page.expect_response(lambda r: url_pattern in r.url, timeout=timeout) as response_info:
        page.click(selector)
    return response_info.value
