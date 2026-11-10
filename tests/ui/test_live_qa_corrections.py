"""Regression tests for the live QA findings D1 (footer), D2 (legacy social defaults), D3 (dead team links)
and the public-profile bounty cache.
"""
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import resolve

from apps.common.context_processors import site_footer

BASE = Path(settings.BASE_DIR)
OFFICIAL_FB = "https://www.facebook.com/ownlobbygg"
OFFICIAL_IG = "https://www.instagram.com/ownlobbygg/"


# ---------------------------------------------------------------- D1: footer
@pytest.mark.parametrize("path,mode", [
    ("/about/", "full"), ("/faq/", "full"), ("/tournaments/", "full"), ("/community/", "full"), ("/arena/", "full"),
    ("/orgs/", "full"), ("/competition/rankings/", "full"), ("/", "full"),
    ("/account/login/", "legal"), ("/account/signup/", "legal"), ("/account/verify/otp/", "legal"),
    ("/dashboard/competitive/", "none"), ("/wallet/", "none"), ("/me/settings/", "none"), ("/notifications/", "none"),
    ("/api/tournaments/", "none"), ("/teams/protocol-v/manage/", "none"), ("/orgs/x/control-plane/", "none"),
])
def test_footer_mode_by_path(path, mode):
    assert site_footer(RequestFactory().get(path)) == {"site_footer_mode": mode}


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/about/", "/faq/", "/tournaments/", "/community/", "/arena/", "/orgs/", "/competition/rankings/"])
def test_public_pages_render_exactly_one_footer_with_legal_and_official_social_links(client, path):
    html = client.get(path).content.decode()
    assert html.count("<footer") == 1, path
    assert 'href="/terms/"' in html and 'href="/privacy/"' in html, path
    assert OFFICIAL_FB in html and OFFICIAL_IG in html, path
    assert "deltacrown.gg" not in html.lower() and "deltacrowngg" not in html.lower(), path


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/account/login/", "/account/signup/"])
def test_auth_pages_get_the_compact_legal_footer_only(client, path):
    html = client.get(path).content.decode()
    assert html.count("<footer") == 1
    assert "ol-footer-legal" in html
    assert 'href="/terms/"' in html and 'href="/privacy/"' in html and OFFICIAL_FB in html
    assert "ol-footer-legacy" not in html  # not the full marketing footer


@pytest.mark.django_db
def test_homepage_keeps_its_own_footers(client):
    html = client.get("/").content.decode()
    assert "dc-footer-desktop" in html and "dc-footer-mobile" in html  # home overrides the block: no third footer
    assert html.count("<footer") == 2


# ---------------------------------------------------------------- D2: social defaults
def test_toc_default_socials_never_prefill_the_retired_deltacrown_accounts():
    from apps.tournaments.api.toc.settings_service import TOCSettingsService

    values = " ".join(TOCSettingsService.OFFICIAL_SOCIAL_DEFAULTS.values()).lower()
    assert "deltacrown" not in values
    assert TOCSettingsService.OFFICIAL_SOCIAL_DEFAULTS["social_youtube"] == ""
    assert TOCSettingsService.OFFICIAL_SOCIAL_DEFAULTS["social_facebook"] == OFFICIAL_FB
    assert TOCSettingsService.OFFICIAL_SOCIAL_DEFAULTS["social_instagram"] == OFFICIAL_IG
    js = (BASE / "static/tournaments/toc/js/toc-settings.js").read_text(encoding="utf-8")
    assert "DeltaCrownGG" not in js


def test_official_tournament_detail_defaults_use_official_accounts_and_hide_youtube():
    from apps.tournaments.views.detail import _resolve_default_vanguard_socials

    t = SimpleNamespace(is_official=True, social_discord="", social_facebook="", social_youtube="", social_instagram="")
    resolved = _resolve_default_vanguard_socials(t)
    assert resolved["facebook"] == OFFICIAL_FB and resolved["instagram"] == OFFICIAL_IG and resolved["youtube"] == ""


def test_organizer_owned_social_values_are_not_overwritten_by_defaults():
    from apps.tournaments.views.detail import _resolve_default_vanguard_socials

    t = SimpleNamespace(is_official=True, social_discord="", social_facebook="https://facebook.com/partner", social_youtube="", social_instagram="")
    assert _resolve_default_vanguard_socials(t)["facebook"] == "https://facebook.com/partner"


def test_no_runtime_template_links_to_the_retired_social_accounts():
    offenders = []
    for path in (BASE / "templates").rglob("*.html"):
        if "My drafts" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'href="https?://[^"]*(deltacrowngg|deltacrown\.gg)', text, re.I):
            offenders.append(str(path.relative_to(BASE)))
    assert offenders == []


# ---------------------------------------------------------------- D3: dead team links
def test_no_runtime_template_links_to_ranking_policy_or_team_guide():
    offenders = []
    for path in (BASE / "templates").rglob("*.html"):
        if "My drafts" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if re.search(r'href="/(ranking-policy|team-guide)"', text):
            offenders.append(str(path.relative_to(BASE)))
    assert offenders == []


def test_team_hub_static_internal_links_all_resolve():
    text = (BASE / "templates/organizations/hub/team_hub.html").read_text(encoding="utf-8")
    hrefs = set(re.findall(r'href="(/[A-Za-z0-9_\-/]*)"', text))
    assert hrefs  # the template does link to site pages
    unresolved = []
    for href in sorted(hrefs):
        try:
            resolve(href)
        except Exception:
            unresolved.append(href)
    assert unresolved == []


# ---------------------------------------------------------------- profile: bounty cache
@pytest.fixture
def profile_user(db, django_user_model):
    return django_user_model.objects.create_user(username="bountycache", email="bountycache@example.test", password="x" * 20)


def _bounty_queries(ctx):
    return [q for q in ctx.captured_queries if "user_profile_bounty" in q["sql"]]


@pytest.mark.django_db
def test_second_visitor_request_skips_the_bounty_queries(client, profile_user):
    cache.clear()
    first = client.get("/@bountycache/")
    assert first.status_code == 200
    with CaptureQueriesContext(connection) as ctx:
        second = client.get("/@bountycache/")
    assert second.status_code == 200
    assert _bounty_queries(ctx) == []


@pytest.mark.django_db
def test_owner_always_reads_fresh_bounty_data(client, profile_user):
    cache.clear()
    client.force_login(profile_user)
    client.get("/@bountycache/")
    with CaptureQueriesContext(connection) as ctx:
        assert client.get("/@bountycache/").status_code == 200
    assert _bounty_queries(ctx) != []


@pytest.mark.django_db
def test_bounty_cache_is_isolated_per_role_and_per_user(profile_user, django_user_model):
    from apps.user_profile.services.profile_context import _profile_cache_version, build_public_bounty_context_cached

    other = django_user_model.objects.create_user(username="bountyother", email="bountyother@example.test", password="x" * 20)
    cache.clear()
    build_public_bounty_context_cached(profile_user, "guest")
    key = lambda user, role: f"profile:bounty:{user.username}:{_profile_cache_version(user.username)}:{role}"
    assert cache.get(key(profile_user, "guest")) is not None
    assert cache.get(key(profile_user, "follower")) is None
    assert cache.get(key(other, "guest")) is None
    build_public_bounty_context_cached(profile_user, "owner")
    assert cache.get(key(profile_user, "owner")) is None  # owners never populate or read the shared entry
