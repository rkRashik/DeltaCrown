"""Batch D regressions: public profile, team, organization and rankings presentation.

These pin presentation decisions (no placeholder panels, no fake claims, one accent) and the privacy-safe rendering of
the public profile. Backend visibility rules are covered by the existing profile/team/org suites.
"""
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from apps.organizations.tests.factories import OrganizationFactory, TeamFactory

User = get_user_model()
ROOT = Path(settings.BASE_DIR)


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def _profile(client, username):
    return client.get(f"/@{username}/")


@pytest.mark.django_db
class TestPublicProfile:
    def _user(self, name="batchd_player"):
        from apps.user_profile.models import UserProfile
        user = User.objects.create_user(username=name, email=f"{name}@example.test", password="pw-12345-x")
        UserProfile.objects.get_or_create(user=user)
        return user

    def test_visitor_sees_no_wallet_stream_or_empty_widget_clutter(self, client):
        user = self._user()
        html = _profile(client, user.username).content.decode()
        assert "ol-identity" in html
        for text in ("Wallet balance is private", "No stream configured", "No loadout configured",
                     "No team affiliations yet", "No social links connected", "LVL ", "Verified Pro"):
            assert text not in html, text
        assert "No matches played yet" in html  # honest empty state instead of 0% / "Not tracked yet"
        assert "Not tracked yet" not in html

    def test_profile_has_no_fake_mobile_toolbar_and_share_has_a_name(self, client):
        user = self._user("batchd_player2")
        html = _profile(client, user.username).content.decode()
        assert "fa-plus text-xl" not in html          # the unlabeled, action-less floating "+" bar
        assert 'data-share-profile' in html and 'aria-label="Copy profile link"' in html

    def test_owner_still_gets_wallet_and_edit_controls(self, client):
        user = self._user("batchd_owner")
        client.force_login(user)
        html = _profile(client, user.username).content.decode()
        assert "Edit Profile" in html
        assert "Current Balance" in html

    def test_visitor_never_receives_owner_wallet_balance(self, client):
        owner = self._user("batchd_owner2")
        visitor = self._user("batchd_visitor")
        client.force_login(visitor)
        html = _profile(client, owner.username).content.decode()
        # the wallet card and the economy tab are owner-only; the site header's own wallet link is not part of the profile
        assert 'data-profile-tab-target="economy"' not in html
        assert 'id="tab-economy"' not in html
        assert "Wallet balance is private" not in html

    def test_follow_script_skips_status_call_for_visitors_and_uses_brand_buttons(self):
        js = _read("static/siteui/js/follow.js")
        assert "viewer_is_authenticated" in js and "FOLLOW_CLASS" in js
        assert "uppercase tracking-wider px-10 py-4" not in js

    def test_initials_avatars_use_muted_brand_tones(self):
        from apps.siteui.templatetags.dc_avatar import AVATAR_GRADIENTS
        neon = {"00D9FF", "FF0080", "00FF88", "A100FF", "00FFF0", "0099FF", "FFD700", "FF6B00"}
        assert not neon & {c for pair in AVATAR_GRADIENTS for c in pair}


@pytest.mark.django_db
class TestPublicTeam:
    def test_team_without_a_banner_gets_the_compact_hero_and_no_not_set_chips(self, client):
        team = TeamFactory(name="Batch D Team")
        html = client.get(f"/orgs/{team.organization.slug}/teams/{team.slug}/").content.decode()
        assert "dc-hero-shell--compact" in html
        assert "Not Set" not in html
        assert "default-banner" not in re.findall(r'<img[^>]+dc-hero-banner[^>]*>', html).__str__()

    def test_mobile_action_bar_cannot_float_over_the_desktop_page(self):
        css = _read("templates/organizations/team/partials/_head_assets.html")
        assert "@media (min-width: 768px) { #dc-mobile-actionbar { display: none !important; } }" in css

    def test_team_page_defaults_to_the_brand_accent_not_blue_or_cyan(self):
        css = _read("templates/organizations/team/partials/_head_assets.html")
        assert "--team-action: #E2B761" in css
        assert "--team-action: #22D3EE" not in css

    def test_teams_hub_copy_has_no_invented_claims(self, client):
        html = client.get("/teams/").content.decode()
        for text in ("Season 1", "Find a Squad", "Select Combat Zone", "Start Your Legacy", "Prize Pool"):
            assert text not in html, text
        assert "Build your team" in html


@pytest.mark.django_db
class TestPublicOrganization:
    def test_org_page_has_no_placeholder_panels_stock_photos_or_fake_badges(self, client):
        org = OrganizationFactory(name="Batch D Org", is_verified=False)
        html = client.get(f"/orgs/{org.slug}/").content.decode()
        for text in ("Pro Organization", "coming soon", "Official Merch", "Partner with Us", "dicebear", "unsplash",
                     "Verified organization", "/ 10 Slots", "Operations Log", "Active Squads"):
            assert text not in html, text
        assert "ol-identity" in html

    def test_verified_mark_only_for_verified_organizations(self, client):
        verified = OrganizationFactory(name="Batch D Verified", is_verified=True)
        assert "Verified organization" in client.get(f"/orgs/{verified.slug}/").content.decode()

    def test_org_detail_lists_streams_tab_with_a_target(self, client):
        org = OrganizationFactory(name="Batch D Streams")
        html = client.get(f"/orgs/{org.slug}/").content.decode()
        assert 'href="#streams"' in html and 'id="streams"' in html


@pytest.mark.django_db
class TestRankingsPresentation:
    def test_global_rankings_use_one_accent_and_name_the_compare_column(self):
        tpl = _read("templates/competition/leaderboards/leaderboard_global.html")
        for neon in ("#6849E5", "#0A84FF", "#8B5CF6"):
            assert neon.lower() not in tpl.lower(), neon
        assert 'Select to compare' in tpl
