"""
UP-UI-REBIRTH-01: Tests for new Profile + Settings UI (no v2/v3 naming)
Tests owner vs spectator vs anonymous views, role removal from passport, templates.
"""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client
from apps.user_profile.models import UserProfile, GamePassportSchema as GamePassport
from apps.games.models import Game


User = get_user_model()


@pytest.fixture
def owner_user(db):
    """Create a user who owns their profile."""
    return User.objects.create_user(
        username="pro_player",
        email="pro@example.com",
        password="testpass123"
    )


@pytest.fixture
def spectator_user(db):
    """Create a user viewing someone else's profile."""
    return User.objects.create_user(
        username="fan123",
        email="fan@example.com",
        password="testpass123"
    )


@pytest.fixture
def owner_profile(owner_user):
    """Get owner's UserProfile."""
    profile, _ = UserProfile.objects.get_or_create(user=owner_user)
    profile.display_name = "ProPlayer"
    profile.bio = "Top esports competitor"
    profile.save()
    return profile


@pytest.fixture
def sample_game(db):
    """Create a sample game for passports."""
    return Game.objects.create(
        slug="valorant",
        name="Valorant",
        is_active=True
    )


@pytest.fixture
def owner_passport(owner_user, sample_game):
    """Create a game passport for owner."""
    return GamePassport.objects.create(
        user=owner_user,
        game=sample_game,
        identity_key="ProPlayer#123",
        rank_name="Radiant",
        looking_for_team=True,
        visibility="public",
        is_pinned=True
    )


class TestPublicProfileOwnerView:
    """Tests for owner viewing their own profile."""

    def test_owner_sees_all_sections(self, client, owner_user, owner_profile):
        """Owner should see ALL sections including Economy + Shop."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['is_owner'] is True
        
        # Owner should have Economy + Shop in nav_sections
        sections = response.context['nav_sections']
        section_ids = [s['id'] for s in sections]
        assert 'economy' in section_ids
        assert 'shop' in section_ids
        assert 'stats' in section_ids
        assert 'passports' in section_ids

    def test_owner_sees_edit_profile_button(self, client, owner_user, owner_profile):
        """Owner should see 'Edit Profile' button, not 'Follow'."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        content = response.content.decode()
        assert 'Edit Profile' in content
        assert '+ Follow' not in content

    def test_owner_sees_passport_with_no_role(self, client, owner_user, owner_profile, owner_passport):
        """Owner should see passport WITHOUT role field (Task E)."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        # Check context: passports should exist
        assert 'pinned_passports' in response.context or 'passports' in response.context
        
        # Check template: should NOT contain role display
        content = response.content.decode()
        # The passport card should NOT have role text
        assert 'Role:' not in content  # Old v2 used "Role:" label
        assert 'role-badge' not in content  # No role badge class


class TestPublicProfileSpectatorView:
    """Tests for logged-in user viewing another user's profile."""

    def test_spectator_sees_limited_sections(self, client, spectator_user, owner_user, owner_profile):
        """Spectator should NOT see Economy/Shop sections."""
        client.force_login(spectator_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['is_owner'] is False
        
        # Spectator should NOT have Economy + Shop in nav_sections
        sections = response.context['nav_sections']
        section_ids = [s['id'] for s in sections]
        assert 'economy' not in section_ids
        assert 'shop' not in section_ids
        assert 'stats' in section_ids  # Public sections still visible

    def test_spectator_sees_follow_button(self, client, spectator_user, owner_user, owner_profile):
        """Spectator should see 'Follow' button, not 'Edit Profile'."""
        client.force_login(spectator_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        content = response.content.decode()
        assert '+ Follow' in content
        assert 'Edit Profile' not in content

    def test_spectator_sees_passport_without_role(self, client, spectator_user, owner_user, owner_profile, owner_passport):
        """Spectator viewing passport should NOT see role (Task E)."""
        client.force_login(spectator_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        content = response.content.decode()
        assert 'Role:' not in content
        assert owner_passport.identity_key in content  # IGN should be visible


class TestPublicProfileAnonymousView:
    """Tests for anonymous (not logged in) user viewing profile."""

    def test_anonymous_sees_limited_sections(self, client, owner_user, owner_profile):
        """Anonymous user should NOT see Economy/Shop."""
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        assert response.status_code == 200
        assert response.context['is_owner'] is False
        
        sections = response.context['nav_sections']
        section_ids = [s['id'] for s in sections]
        assert 'economy' not in section_ids
        assert 'shop' not in section_ids

    def test_anonymous_cannot_see_private_passports(self, client, owner_user, owner_passport):
        """Anonymous users should only see public passports."""
        # Make passport private
        owner_passport.visibility = 'private'
        owner_passport.save()
        
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)
        
        # Passport should NOT be in pinned_passports
        pinned = response.context.get('pinned_passports', [])
        assert len(pinned) == 0


class TestSettingsView:
    """Tests for profile settings hub."""

    def test_settings_requires_login(self, client):
        """Settings page should require authentication."""
        url = reverse('user_profile:profile_settings_v2')
        response = client.get(url)
        
        # Should redirect to login
        assert response.status_code == 302
        assert '/accounts/login/' in response.url or '/login/' in response.url

    def test_owner_accesses_settings(self, client, owner_user, owner_profile):
        """Owner can access their settings page."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_settings_v2')
        response = client.get(url)

        assert response.status_code == 200
        assert 'profile' in response.context  # Profile data available

    def test_settings_has_passports_context(self, client, owner_user, owner_profile, owner_passport):
        """Settings page should include passports in context."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_settings_v2')
        response = client.get(url)

        # View adds 'passports' alias
        assert 'passports' in response.context
        passports = response.context['passports']
        assert len(passports) == 1
        assert passports[0].identity_key == owner_passport.identity_key


class TestTemplateCompilation:
    """Tests to ensure new templates compile without errors."""

    def test_public_template_compiles(self, client, owner_user, owner_profile):
        """Public profile template should render without TemplateSyntaxError."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        
        try:
            response = client.get(url)
            assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"Template compilation failed: {e}")

    def test_settings_template_compiles(self, client, owner_user, owner_profile):
        """Settings template should render without TemplateSyntaxError."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_settings_v2')
        
        try:
            response = client.get(url)
            assert response.status_code == 200
        except Exception as e:
            pytest.fail(f"Template compilation failed: {e}")

    def test_partials_included_correctly(self, client, owner_user, owner_profile, owner_passport):
        """Partial components should be included in public template."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        content = response.content.decode()
        # Check for partial-specific elements
        assert 'battle-card' in content  # battle_card.html class
        assert 'section-header' in content or 'Stats Overview' in content  # section_header.html


class TestTaskEVerification:
    """Specific tests for Task E: Role removal from passport."""

    def test_passport_context_has_no_role_attribute(self, client, owner_user, owner_profile, owner_passport):
        """Passport objects in context should NOT have 'team_role' attribute."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        # Get passports from context
        pinned = response.context.get('pinned_passports', [])
        unpinned = response.context.get('unpinned_passports', [])
        all_passports = list(pinned) + list(unpinned)

        for passport in all_passports:
            # Should NOT have team_role attribute
            assert not hasattr(passport, 'team_role'), \
                f"Passport {passport.id} has 'team_role' attribute (Task E violation)"

    def test_view_code_does_not_assign_role(self):
        """Verify view code doesn't assign team_role to passport."""
        # Read view source
        from apps.user_profile.views import fe_v2
        import inspect
        
        source = inspect.getsource(fe_v2.profile_public_v2)
        
        # Should NOT contain assignment to team_role
        assert 'passport.team_role' not in source, \
            "View code still assigns team_role to passport (Task E violation)"
        
        # Should contain UP-UI-REBIRTH-01 comment
        assert 'UP-UI-REBIRTH-01' in source, \
            "Missing UP-UI-REBIRTH-01 marker comment"


class TestResponsiveDesign:
    """Tests for responsive behavior (non-functional)."""

    def test_mobile_viewport_meta(self, client, owner_user, owner_profile):
        """Template should include viewport meta for mobile."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        content = response.content.decode()
        # Should extend base that has viewport meta
        assert '<meta' in content or 'viewport' in content.lower()

    def test_tailwind_responsive_classes(self, client, owner_user, owner_profile):
        """Template should use Tailwind responsive classes."""
        client.force_login(owner_user)
        url = reverse('user_profile:profile_public_v2', args=[owner_user.username])
        response = client.get(url)

        content = response.content.decode()
        # Check for Tailwind breakpoint classes
        assert 'md:' in content or 'lg:' in content or 'sm:' in content
