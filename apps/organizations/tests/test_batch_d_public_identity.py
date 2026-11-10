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

    def test_follow_is_handled_once_and_toasts_use_the_toast_api(self, client):
        """The profile page had a second inline follow handler (two POSTs per click, old button classes), and
        follow.js passed a bare string to window.showToast, which expects an options object."""
        user = self._user("batchd_player3")
        html = _profile(client, user.username).content.decode()
        assert "fetch(url, {" not in html and "Follow error:" not in html
        js = _read("static/siteui/js/follow.js")
        assert "function followToast" in js and "window.showToast(payload, type)" in js
        assert "showToast.length" not in js          # no function.length contract
        assert "showToast('" not in js.replace("followToast('", "")

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

    def test_working_staff_management_stays_manager_only_and_wired(self, client):
        """What was removed had no handler or link (no id, class or href was referenced by the page script); what stays
        is the real staff management: Invite/Edit staff, change role, remove, and the three vnext member endpoints."""
        org = OrganizationFactory(name="Batch D Managed")
        raw = client.get(f"/orgs/{org.slug}/").content.decode()
        visitor_html = re.sub(r"<(?:script|style)[^>]*>.*?</(?:script|style)>", "", raw, flags=re.S)  # DOM only
        for marker in ('id="inviteStaffBtn"', 'id="editStaffBtn"', 'id="addMemberModal"', 'id="changeRoleModal"',
                       'id="removeMemberModal"', "Open Control Plane", "Treasury", "Pending Actions"):
            assert marker not in visitor_html, f"manager-only marker leaked to a visitor: {marker}"
        client.force_login(org.ceo)
        manager_html = client.get(f"/orgs/{org.slug}/").content.decode()
        for marker in ('id="inviteStaffBtn"', 'id="editStaffBtn"', 'id="addMemberModal"', 'id="changeRoleModal"',
                       'id="removeMemberModal"', 'id="confirmRemoveBtn"', "/members/add/", "/role/", "/remove/",
                       "Open Control Plane", f"/orgs/{org.slug}/control-plane/"):
            assert marker in manager_html, f"manager control missing: {marker}"

    def test_removed_placeholders_had_no_script_hooks(self):
        """Guard for the claim above: none of the removed elements can be re-added unnoticed with a script hook."""
        tpl = _read("templates/organizations/org/org_detail.html")
        script = tpl[tpl.index("{% block extra_js %}"):]
        for hook in ("mediaKit", "media-kit", "partner", "merch", "viewAllStreams", "newTeamBtn", "walletBtn", "manageAll"):
            assert hook.lower() not in script.lower(), hook

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


@pytest.mark.django_db
class TestPrivateProfileState:
    def _private_user(self):
        from apps.user_profile.models import PrivacySettings, UserProfile
        owner = User.objects.create_user(username="batchd_private", email="bp@example.test", password="pw-12345-x")
        profile, _ = UserProfile.objects.get_or_create(user=owner)
        profile.bio = "Secret bio text for the owner only"
        profile.save()
        settings_row, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        settings_row.is_private_account = True
        settings_row.visibility_preset = "PRIVATE"
        settings_row.save()
        return owner

    def test_private_profile_shows_only_the_restricted_card(self, client):
        owner = self._private_user()
        html = client.get(f"/@{owner.username}/").content.decode()
        assert "This profile is private" in html and "ol-identity" in html
        assert "Secret bio text" not in html and "bp@example.test" not in html
        assert "bg-gray-800" not in html and "bg-green-600" not in html  # the old slate card / green button

    def test_request_button_uses_the_real_follow_endpoint(self, client):
        owner = self._private_user()
        visitor = User.objects.create_user(username="batchd_visitor2", email="bv@example.test", password="pw-12345-x")
        client.force_login(visitor)
        html = client.get(f"/@{owner.username}/").content.decode()
        assert 'id="follow-request-btn"' in html
        assert f"/api/profile/{owner.username}/follow/" in html
        assert "/profiles/" not in html.split("sendFollowRequest")[-1]   # the old URL answered 404


class TestTierPalette:
    TIERS = ("crown", "legend", "master", "elite", "challenger", "rookie")

    def _tokens(self):
        css = _read("static/ownlobby/foundation.css")
        out = {}
        for tier in self.TIERS:
            hex_ = re.search(rf"--ol-tier-{tier}:\s*(#[0-9A-Fa-f]{{6}})", css).group(1)
            rgb = tuple(int(x) for x in re.search(rf"--ol-tier-{tier}-rgb:\s*([\d, ]+);", css).group(1).split(","))
            out[tier] = (hex_, rgb)
        return out

    def test_every_tier_hex_matches_its_rgb_triple(self):
        for tier, (hex_, rgb) in self._tokens().items():
            assert tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5)) == rgb, tier

    def test_tiers_are_distinct_and_readable_on_their_tinted_badge(self):
        def lum(c):
            f = lambda v: v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
            r, g, b = (f(x / 255) for x in c)
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        surface = (0x17, 0x18, 0x1A)
        tokens = self._tokens()
        assert len({h for h, _ in tokens.values()}) == len(self.TIERS)            # CHALLENGER is not saffron, MASTER is not CROWN ...
        for tier, (_, rgb) in tokens.items():
            badge = tuple(round(rgb[i] * 0.12 + surface[i] * 0.88) for i in range(3))
            ratio = (max(lum(rgb), lum(badge)) + 0.05) / (min(lum(rgb), lum(badge)) + 0.05)
            assert ratio >= 4.5, (tier, round(ratio, 2))

    def test_pages_take_tier_colours_from_the_tokens_not_literals(self):
        rankings = _read("templates/competition/leaderboards/leaderboard_global.html")
        hub = _read("templates/organizations/hub/team_hub.html")
        for tier in self.TIERS:
            assert f"var(--ol-tier-{tier})" in rankings or tier in ("crown",) or f"--ol-tier-{tier}" in rankings
            assert f"--ol-tier-{tier}" in hub
        assert not re.search(r'\[data-tier="CHALLENGER"\]\s*\{\s*--tc:#', rankings)
        assert "#22c55e" not in hub.split(".tier-challenger")[1].split("}")[0]   # challenger was green here, violet there


class TestFindTeamAccessibility:
    def test_find_team_controls_have_names_and_valid_aria(self):
        tpl = _read("templates/organizations/teams/partials/find_team_v2.html")
        js = _read("static/organizations/team_find/find_team_v2.js")
        assert tpl.count('aria-label="Close') >= 2
        for name in ('aria-label="Region"', 'aria-label="Platform"', 'aria-label="Sort by"'):
            assert name in tpl
        assert '<aside class="spotlight' not in tpl            # a complementary landmark nested in another landmark
        assert 'getAttribute("role") === "tab" ? "aria-selected" : "aria-pressed"' in js
