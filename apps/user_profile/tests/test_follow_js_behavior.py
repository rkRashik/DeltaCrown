"""Behavioural tests for static/siteui/js/follow.js, run in Chromium against a small harness page.

The page serves the real follow.js; every /api/profile/... call is routed and counted, so the tests prove what the
browser actually sends (one mutation per click, no calls for visitors) without needing a live Django server.
Skipped when Playwright's Chromium is not installed.
"""
import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from django.conf import settings

pw = pytest.importorskip("playwright.sync_api")

JS = (Path(settings.BASE_DIR) / "static/siteui/js/follow.js").read_text(encoding="utf-8")
ORIGIN = "http://follow.test"


def _page_html(state="none", authenticated=True, private=False, extra_button=True, toast="options"):
    server = json.dumps({
        "viewer_is_authenticated": authenticated, "profile_username": "target",
        "relationship_state": state, "is_private_account": private, "can_follow": True,
    })
    toast_js = {
        "options": "window.__toasts=[];window.showToast=function(o){window.__toasts.push(typeof o==='object'?o.message+'|'+o.type:'BARE:'+o)};",
        "legacy": "window.__toasts=[];window.showToast=function(message,type){window.__toasts.push(String(message)+'|'+type)};",
        "none": "",
        "throws": "window.showToast=function(){throw new Error('boom')};",
    }[toast]
    sidebar = ('<button id="side" class="follow-btn" data-follow-btn data-follow-extra-class="w-full">Follow</button>'
               if extra_button else "")
    return f"""<!doctype html><html><head><meta name="csrf-token" content="{'x' * 40}"></head><body>
    <script id="profile-follow-state" type="application/json">{server}</script>
    <span data-follower-count>5</span>
    <button id="head" data-follow-btn>Follow</button>{sidebar}
    <script>{toast_js}</script><script>{JS}</script></body></html>"""


@pytest.fixture(scope="module", autouse=True)
def _allow_orm_while_the_browser_loop_runs():
    """Playwright's sync API keeps an event loop running in this thread; the package's autouse DB fixtures are
    synchronous and would otherwise be refused by Django's async guard. Scoped to this module only."""
    previous = os.environ.get("DJANGO_ALLOW_ASYNC_UNSAFE")
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    yield
    if previous is None:
        os.environ.pop("DJANGO_ALLOW_ASYNC_UNSAFE", None)
    else:
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = previous


@pytest.fixture(scope="module")
def browser():
    if sys.platform == "win32":  # Playwright spawns the browser as a subprocess, which needs the Proactor loop
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    sync = pw.sync_playwright().start()
    try:
        b = sync.chromium.launch(headless=True)
    except Exception as exc:  # pragma: no cover - environment without a browser
        sync.stop()
        pytest.skip(f"Chromium unavailable: {exc}")
    yield b
    b.close()
    sync.stop()


class Harness:
    def __init__(self, browser, **page_kwargs):
        self.ctx = browser.new_context()
        self.page = self.ctx.new_page()
        self.calls = []
        self.dialogs = []
        self.responses = {}
        self.delay = 0
        self.page_kwargs = page_kwargs
        self.page.on("dialog", lambda d: (self.dialogs.append(d.message), d.accept()))
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self.page.route(f"{ORIGIN}/**", self._route)

    def _route(self, route):
        req = route.request
        path = req.url.replace(ORIGIN, "")
        if path == "/":
            return route.fulfill(status=200, content_type="text/html", body=_page_html(**self.page_kwargs))
        self.calls.append((req.method, path))
        status, body, ctype = self.responses.get(path, (200, {"success": True}, "application/json"))
        if self.delay:
            self.page.wait_for_timeout(self.delay)
        route.fulfill(status=status, content_type=ctype, body=body if isinstance(body, str) else json.dumps(body))

    def open(self):
        self.page.goto(ORIGIN + "/")
        self.page.wait_for_timeout(150)
        return self

    def mutations(self):
        return [c for c in self.calls if c[0] == "POST"]

    def close(self):
        self.ctx.close()


@pytest.fixture
def make(browser):
    made = []

    def factory(**kw):
        h = Harness(browser, **kw)
        made.append(h)
        return h

    yield factory
    for h in made:
        h.close()


def test_visitor_makes_no_status_request(make):
    h = make(authenticated=False).open()
    assert h.calls == []


def test_signed_in_viewer_loads_status_exactly_once(make):
    h = make(state="none")
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
    h.open()
    assert h.calls == [("GET", "/api/profile/target/follow/status/")]


def test_one_click_is_exactly_one_follow_mutation_and_updates_every_button(make):
    h = make(state="none")
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
    h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "followed"}, "application/json")
    h.open()
    h.page.click("#head")
    h.page.wait_for_timeout(300)
    assert h.mutations() == [("POST", "/api/profile/target/follow/")]
    assert "Following" in h.page.inner_text("#head") and "Following" in h.page.inner_text("#side")
    assert "w-full" in h.page.get_attribute("#side", "class")          # layout class survives the restyle
    assert h.page.inner_text("[data-follower-count]") == "6"
    assert h.page.evaluate("window.__toasts") == ["Now following user!|success"]


def test_sidebar_button_works_and_a_busy_button_ignores_double_clicks(make):
    h = make(state="none")
    h.delay = 400
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
    h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "followed"}, "application/json")
    h.open()
    h.page.dispatch_event("#side", "click")
    h.page.dispatch_event("#side", "click")       # arrives while the first request is in flight
    assert h.page.is_disabled("#side")
    h.page.wait_for_timeout(900)
    assert len(h.mutations()) == 1


def test_unfollow_asks_for_confirmation_and_declining_sends_nothing(make):
    h = make(state="following")
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "following"}, "application/json")
    h.open()
    h.page.on("dialog", lambda d: None)
    h.ctx.clear_cookies()
    h.page.evaluate("window.confirm = () => false")
    h.page.click("#head")
    h.page.wait_for_timeout(200)
    assert h.mutations() == []
    h.page.evaluate("window.confirm = () => true")
    h.responses["/api/profile/target/unfollow/"] = (200, {"success": True}, "application/json")
    h.page.click("#head")
    h.page.wait_for_timeout(300)
    assert h.mutations() == [("POST", "/api/profile/target/unfollow/")]
    assert "Follow" in h.page.inner_text("#head") and "Following" not in h.page.inner_text("#head")
    assert h.page.inner_text("[data-follower-count]") == "4"


def test_private_account_request_is_shown_as_pending_and_cannot_be_clicked_again(make):
    """The backend has no cancel-request endpoint, so a pending request must not offer a cancel that would 404."""
    h = make(state="none", private=True)
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none", "is_private_account": True}, "application/json")
    h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "request_sent"}, "application/json")
    h.open()
    h.page.click("#head")
    h.page.wait_for_timeout(300)
    assert "Requested" in h.page.inner_text("#head") and "Requested" in h.page.inner_text("#side")
    assert h.page.is_disabled("#head") and h.page.get_attribute("#head", "title") == "Waiting for approval"
    assert h.page.evaluate("window.__toasts") == ["Follow request sent!|success"]
    h.page.dispatch_event("#head", "click")          # a forced click on the disabled button sends nothing
    h.page.wait_for_timeout(200)
    assert [m[1] for m in h.mutations()] == ["/api/profile/target/follow/"]


def test_a_pending_request_from_the_server_state_is_disabled_on_load(make):
    h = make(state="requested", private=True)
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "requested"}, "application/json")
    h.open()
    assert h.page.is_disabled("#head") and h.page.is_disabled("#side")
    assert h.mutations() == []


def test_server_error_restores_the_button_and_reports_it(make):
    h = make(state="none")
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
    h.responses["/api/profile/target/follow/"] = (500, "<html>Server Error</html>", "text/html")
    h.open()
    h.page.click("#head")
    h.page.wait_for_timeout(300)
    assert not h.page.is_disabled("#head")
    assert h.page.inner_text("#head").strip() == "Follow"
    assert h.page.evaluate("window.__toasts") == ["Failed to follow user|error"]   # no "Unexpected token <"
    assert h.errors == []


def test_toast_works_with_both_toast_apis_and_without_one(make):
    for kind, expected in (("options", ["Now following user!|success"]), ("legacy", ["Now following user!|success"])):
        h = make(state="none", toast=kind)
        h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
        h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "followed"}, "application/json")
        h.open()
        h.page.click("#head")
        h.page.wait_for_timeout(250)
        assert h.page.evaluate("window.__toasts") == expected, kind
    for kind in ("none", "throws"):
        h = make(state="none", toast=kind)
        h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
        h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "followed"}, "application/json")
        h.open()
        h.page.click("#head")
        h.page.wait_for_timeout(250)
        assert "Now following user!" in h.page.inner_text("#follow-toast-region"), kind
        assert h.page.get_attribute("#follow-toast-region", "role") == "status"


def test_initialisation_binds_one_listener_per_button(make):
    h = make(state="none")
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
    h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "followed"}, "application/json")
    h.open()
    # a second DOMContentLoaded (as a restored page could trigger) must not stack handlers
    h.page.evaluate("document.dispatchEvent(new Event('DOMContentLoaded'))")
    h.page.wait_for_timeout(150)
    h.page.click("#head")
    h.page.wait_for_timeout(300)
    assert len(h.mutations()) == 1


# ---- one shared in-flight guard for every follow button on the page -----------------------------------------------

def _rapid(h, first, second):
    """Click `first`, then `second` before the first request has completed (the route holds each response for 500ms)."""
    h.page.dispatch_event(first, "click")
    h.page.dispatch_event(second, "click")


@pytest.mark.parametrize("first,second", [("#head", "#side"), ("#side", "#head")])
def test_header_and_sidebar_clicked_together_make_exactly_one_follow_request(make, first, second):
    h = make(state="none")
    h.delay = 500
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
    h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "followed"}, "application/json")
    h.open()
    h.delay = 500
    _rapid(h, first, second)
    # while the request is in flight every related button is disabled and marked busy
    assert h.page.is_disabled("#head") and h.page.is_disabled("#side")
    assert h.page.evaluate("[...document.querySelectorAll('[data-follow-btn]')].every(b => b.dataset.followBusy === '1')")
    h.page.wait_for_timeout(1300)
    assert [m[1] for m in h.mutations()] == ["/api/profile/target/follow/"]
    assert "Following" in h.page.inner_text("#head") and "Following" in h.page.inner_text("#side")
    assert not h.page.is_disabled("#head") and not h.page.is_disabled("#side")
    assert h.page.evaluate("window.__toasts") == ["Now following user!|success"]
    assert h.page.inner_text("[data-follower-count]") == "6"            # counted once


@pytest.mark.parametrize("first,second", [("#head", "#side"), ("#side", "#head")])
def test_header_and_sidebar_clicked_together_make_exactly_one_unfollow_request(make, first, second):
    h = make(state="following")
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "following"}, "application/json")
    h.responses["/api/profile/target/unfollow/"] = (200, {"success": True}, "application/json")
    h.open()
    h.delay = 500
    _rapid(h, first, second)
    h.page.wait_for_timeout(1300)
    assert [m[1] for m in h.mutations()] == ["/api/profile/target/unfollow/"]
    assert h.dialogs == ["Unfollow this user?"]                          # one confirmation, not two
    assert "Follow" in h.page.inner_text("#side") and "Following" not in h.page.inner_text("#side")
    assert h.page.inner_text("[data-follower-count]") == "4"


def test_a_failed_request_restores_every_button_and_allows_a_clean_retry(make):
    h = make(state="none")
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none"}, "application/json")
    h.responses["/api/profile/target/follow/"] = (500, "<html>Server Error</html>", "text/html")
    h.open()
    h.delay = 400
    _rapid(h, "#head", "#side")
    h.page.wait_for_timeout(1000)
    assert len(h.mutations()) == 1
    for sel in ("#head", "#side"):                                         # both restored, both usable
        assert not h.page.is_disabled(sel) and h.page.inner_text(sel).strip() == "Follow"
    assert h.page.evaluate("[...document.querySelectorAll('[data-follow-btn]')].every(b => b.dataset.followBusy === '0')")
    assert h.page.evaluate("window.__toasts") == ["Failed to follow user|error"]
    h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "followed"}, "application/json")
    h.delay = 0
    h.page.click("#side")
    h.page.wait_for_timeout(300)
    assert len(h.mutations()) == 2 and "Following" in h.page.inner_text("#head")


def test_a_pending_request_stays_disabled_and_private_after_a_rapid_double_click(make):
    h = make(state="none", private=True)
    h.responses["/api/profile/target/follow/status/"] = (200, {"relationship_state": "none", "is_private_account": True}, "application/json")
    h.responses["/api/profile/target/follow/"] = (200, {"success": True, "action": "request_sent"}, "application/json")
    h.open()
    h.delay = 400
    _rapid(h, "#side", "#head")
    h.page.wait_for_timeout(1000)
    assert [m[1] for m in h.mutations()] == ["/api/profile/target/follow/"]
    assert h.page.is_disabled("#head") and h.page.is_disabled("#side")
    assert "Requested" in h.page.inner_text("#head") and "Requested" in h.page.inner_text("#side")
    assert h.page.evaluate("window.__toasts") == ["Follow request sent!|success"]
    h.page.dispatch_event("#head", "click")
    h.page.wait_for_timeout(200)
    assert len(h.mutations()) == 1
