"""Behavioural tests for the notification popover, mobile sheet and inbox JS (Batch E).

The real nav partials (templates/partials/notifications/*.html) and the real static/js/notifications_client.js and
static/siteui/js/primary_navigation.js run in Chromium against a small harness page. Every /notifications/ API call
is routed and counted, so the tests prove what the browser sends and how keyboard focus behaves.
Skipped when Playwright's Chromium is not installed.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string

pw = pytest.importorskip("playwright.sync_api")

BASE = Path(settings.BASE_DIR)
CLIENT_JS = (BASE / "static/js/notifications_client.js").read_text(encoding="utf-8")
NAV_JS = (BASE / "static/siteui/js/primary_navigation.js").read_text(encoding="utf-8")
CSS = (BASE / "static/css/notifications.css").read_text(encoding="utf-8")
ORIGIN = "http://notif.test"


def _item(i, cat="TOURNAMENT", read=False, link="", actions=None):
    return {
        "id": i, "type": cat, "notification_type": cat, "read": read, "timestamp": "2099-01-01T00:00:00+00:00",
        "title": f"Title {i}", "titleHtml": f"Title {i}", "htmlText": f"Body {i}", "actionLink": link,
        "actions": actions or [], "priority": "NORMAL",
    }


def _page(unread=0):
    return f"""<!doctype html><html><head><meta name="csrf-token" content="{'x' * 40}"><style>{CSS}</style></head><body>
    <div class="relative">
      <button id="dc-notif-btn" aria-label="Notifications" aria-haspopup="dialog" aria-controls="dc-notif-menu" aria-expanded="false">Bell</button>
      <span id="dc-notif-badge" class="notif-badge" data-count="{unread}" style="display:none"></span>
      {render_to_string("partials/notifications/nav_dropdown.html", {"nav_unread_count": unread})}
    </div>
    <button id="dc-mobile-notif-btn" aria-label="Notifications" aria-haspopup="dialog" aria-expanded="false">Bell</button>
    <span id="dc-mobile-notif-badge" class="notif-badge" data-count="{unread}" style="display:none"></span>
    <a id="after" href="#x">after</a>
    {render_to_string("partials/notifications/mobile_sheet.html", {})}
    <script>{NAV_JS}</script><script>{CLIENT_JS}</script></body></html>"""


@pytest.fixture(scope="module", autouse=True)
def _allow_orm_while_the_browser_loop_runs():
    previous = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    yield
    if previous is None:
        os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
    else:
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = previous


@pytest.fixture(scope="module")
def browser():
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    sync = pw.sync_playwright().start()
    try:
        b = sync.chromium.launch(headless=True)
    except Exception as exc:  # pragma: no cover
        sync.stop()
        pytest.skip(f"Chromium unavailable: {exc}")
    yield b
    b.close()
    sync.stop()


class Harness:
    def __init__(self, browser, items, unread=None, width=1280, fail_first=False):
        self.items = items
        self.unread = sum(1 for i in items if not i["read"]) if unread is None else unread
        self.calls = []
        self.fail_first = fail_first
        self.ctx = browser.new_context(viewport={"width": width, "height": 800})
        self.page = self.ctx.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.route("**/*", self._route)
        self.page.goto(ORIGIN + "/")
        self.page.wait_for_timeout(300)

    def _route(self, route):
        req = route.request
        url = req.url.replace(ORIGIN, "")
        if url == "/":
            return route.fulfill(status=200, content_type="text/html", body=_page(self.unread))
        self.calls.append((req.method, url.split("?")[0]))
        if url.startswith("/notifications/api/preview/"):
            if self.fail_first:
                self.fail_first = False
                return route.fulfill(status=500, body="boom")
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"items": self.items, "unread_count": self.unread}))
        if url.startswith("/notifications/api/mark-read/"):
            return route.fulfill(status=200, content_type="application/json", body=json.dumps({"ok": True}))
        if url.startswith("/notifications/stream"):
            return route.abort()
        return route.fulfill(status=204, body="")

    def posts(self):
        return [c for c in self.calls if c[0] == "POST"]

    def close(self):
        self.ctx.close()


@pytest.fixture
def make(browser):
    made = []

    def _make(items, **kw):
        h = Harness(browser, items, **kw)
        made.append(h)
        return h

    yield _make
    for h in made:
        h.close()


def test_tabs_are_real_tabs_with_selected_state_and_arrow_keys(make):
    h = make([_item(1, "TOURNAMENT"), _item(2, "TEAM"), _item(3, "TEAM")])
    p = h.page
    p.click("#dc-notif-btn")
    tabs = p.locator("#dc-notif-tabs [role=tab]")
    assert tabs.count() == 6
    assert p.get_attribute("#dc-notif-tab-ALL", "aria-selected") == "true"
    p.click("#dc-notif-tab-TEAM")
    assert p.get_attribute("#dc-notif-tab-TEAM", "aria-selected") == "true"
    assert p.get_attribute("#dc-notif-tab-ALL", "aria-selected") == "false"
    assert p.get_attribute("#dc-notif-content", "aria-labelledby") == "dc-notif-tab-TEAM"
    assert p.locator("#dc-notif-content .notif-row").count() == 2
    p.focus("#dc-notif-tab-TEAM")
    p.keyboard.press("ArrowRight")
    assert p.evaluate("document.activeElement.id") == "dc-notif-tab-ECONOMY"
    assert p.get_attribute("#dc-notif-tab-ECONOMY", "aria-selected") == "true"
    assert "Nothing in this filter" in p.inner_text("#dc-notif-content")
    assert not h.errors


def test_popover_escape_closes_and_returns_focus(make):
    h = make([_item(1)])
    p = h.page
    assert p.evaluate("document.querySelector('#dc-notif-menu').inert") is True
    p.click("#dc-notif-btn")
    assert p.get_attribute("#dc-notif-btn", "aria-expanded") == "true"
    assert p.evaluate("document.querySelector('#dc-notif-menu').inert") is False
    assert p.evaluate("document.querySelector('#dc-notif-menu').contains(document.activeElement)")
    p.keyboard.press("Escape")
    assert p.get_attribute("#dc-notif-btn", "aria-expanded") == "false"
    assert p.evaluate("document.querySelector('#dc-notif-menu').inert") is True
    assert p.evaluate("document.activeElement.id") == "dc-notif-btn"
    p.click("#dc-notif-btn")
    p.mouse.click(5, 700)  # outside click closes too
    assert p.get_attribute("#dc-notif-btn", "aria-expanded") == "false"
    assert not h.errors


def test_mobile_sheet_focus_trap_escape_and_scroll_lock(make):
    h = make([_item(1), _item(2)], width=390)
    p = h.page
    assert p.evaluate("document.querySelector('#dc-mobile-notif-sheet').inert") is True
    p.click("#dc-mobile-notif-btn")
    assert p.get_attribute("#dc-mobile-notif-btn", "aria-expanded") == "true"
    assert p.evaluate("document.activeElement.id") == "dc-mobile-notif-close"
    assert p.evaluate("document.body.style.overflow") == "hidden"
    # Shift+Tab from the first control wraps inside the dialog instead of escaping to the page behind it
    p.keyboard.press("Shift+Tab")
    assert p.evaluate("document.querySelector('#dc-mobile-notif-sheet').contains(document.activeElement)")
    for _ in range(40):
        p.keyboard.press("Tab")
        assert p.evaluate("document.querySelector('#dc-mobile-notif-sheet').contains(document.activeElement)")
    p.keyboard.press("Escape")
    assert p.evaluate("document.querySelector('#dc-mobile-notif-sheet').inert") is True
    assert p.evaluate("document.body.style.overflow") == ""
    assert p.evaluate("document.activeElement.id") == "dc-mobile-notif-btn"
    assert not h.errors


def test_zero_one_many_states_and_mark_all_read(make):
    zero = make([])
    zero.page.click("#dc-notif-btn")
    assert "No notifications yet" in zero.page.inner_text("#dc-notif-content")
    assert zero.page.is_disabled("#dc-mark-read-btn")

    one = make([_item(1)])
    one.page.click("#dc-notif-btn")
    assert one.page.locator("#dc-notif-content .notif-row").count() == 1
    assert one.page.inner_text("#dc-notif-badge") == "1"

    many = make([_item(i, ["TOURNAMENT", "TEAM", "SOCIAL"][i % 3], read=(i % 4 == 0)) for i in range(1, 25)])
    many.page.click("#dc-notif-btn")
    assert many.page.locator("#dc-notif-content .notif-row").count() == 10  # popover is capped, inbox has the rest
    unread = many.unread
    assert many.page.inner_text("#dc-notif-badge") == str(unread)
    many.page.click("#dc-mark-read-btn")
    many.page.wait_for_timeout(300)
    assert many.posts() == [("POST", "/notifications/api/mark-read/")]
    assert many.page.is_hidden("#dc-notif-badge")
    assert many.page.is_disabled("#dc-mark-read-btn")
    assert "All notifications marked as read" in many.page.inner_text("#dc-notif-live")


def test_load_failure_shows_retry_and_recovers(make):
    h = make([_item(1)], fail_first=True)
    p = h.page
    p.click("#dc-notif-btn")
    assert "Could not load notifications" in p.inner_text("#dc-notif-content")
    p.click("#dc-notif-content [data-notif-retry]")
    p.wait_for_timeout(300)
    assert p.locator("#dc-notif-content .notif-row").count() == 1
    previews = [c for c in h.calls if c[1].startswith("/notifications/api/preview/")]
    assert len(previews) == 2  # the first load and exactly one retry


def test_opening_the_popover_does_not_refetch_and_rows_have_keyboard_actions(make):
    h = make([_item(1), _item(2, link="/tournaments/x/")])
    p = h.page
    before = len([c for c in h.calls if "preview" in c[1]])
    p.click("#dc-notif-btn")
    p.keyboard.press("Escape")
    p.click("#dc-notif-btn")
    assert len([c for c in h.calls if "preview" in c[1]]) == before == 1
    # row without a link gets a real button; row with a link gets a real anchor
    assert p.locator("#dc-notif-content button[data-mark-read='1']").count() == 1
    assert p.locator("#dc-notif-content a.notif-btn[href='/tournaments/x/']").count() == 1
    p.click("#dc-notif-content button[data-mark-read='1']")
    p.wait_for_timeout(300)
    assert h.posts() == [("POST", "/notifications/api/mark-read/")]
    assert p.locator("#dc-notif-content button[data-mark-read='1']").count() == 0
