"""
Tests for Frontend V2 Views (UP-FE-MVP-01)

Privacy-safe profile views with context service.
Tests verify NO raw ORM objects passed to templates and privacy enforcement.

Test Coverage:
- profile_public_v2: Public profile rendering
- profile_activity_v2: Activity feed with pagination
- profile_settings_v2: Owner-only settings page
- profile_privacy_v2: Owner-only privacy settings
- Context safety: NO raw User/Profile objects in context
- Privacy filtering: Email/staff fields not exposed
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.user_profile.models import UserProfile, UserProfileStats, UserActivity, PrivacySettings
from apps.user_profile.services.profile_context import build_public_profile_context

User = get_user_model()

pytestmark = pytest.mark.django_db


# ============================================
# FIXTURES
# ============================================

@pytest.fixture
def alice_fe_v2(db):
    """Create test user Alice with profile"""
    user = User.objects.create_user(
        username='alice_fe_v2',
        email='alice@example.com',
        password='testpass123'
    )
    # Profile is auto-created by signal - just update it
    profile = user.profile
    profile.display_name = 'Alice Frontend'
    profile.bio = 'Test bio for Alice'
    profile.public_id = 'DC-25-000001'
    profile.country = 'Bangladesh'
    profile.game_profiles = {'valorant': {'ign': 'AliceVAL', 'role': 'Duelist', 'rank': 'Platinum'}}
    profile.save()
    
    # Create stats
    UserProfileStats.objects.create(
        user_profile=profile,
        tournaments_played=5,
        tournaments_won=2,
        matches_played=20,
        matches_won=12
    )
    
    # Create privacy settings (get_or_create to avoid IntegrityError)
    PrivacySettings.objects.get_or_create(
        user_profile=profile,
        defaults={'show_email': False, 'show_real_name': False}
    )
    
    return user


@pytest.fixture
def bob_fe_v2(db):
    """Create test user Bob with profile"""
    user = User.objects.create_user(
        username='bob_fe_v2',
        email='bob@example.com',
        password='testpass123'
    )
    # Profile is auto-created by signal - just update it
    profile = user.profile
    profile.display_name = 'Bob Frontend'
    profile.bio = 'Test bio for Bob'
    profile.public_id = 'DC-25-000002'
    profile.game_profiles = {}
    profile.save()
    
    UserProfileStats.objects.create(user_profile=profile)
    return user


# ============================================
# TEST: build_public_profile_context()
# ============================================

def test_context_builder_returns_safe_primitives(alice_fe_v2):
    """Context builder returns ONLY primitives/JSON (NO ORM objects)"""
    context = build_public_profile_context(None, 'alice_fe_v2')
    
    # Should be able to view (public profile)
    assert context['can_view'] is True
    assert context['is_owner'] is False
    
    # Profile data should be dict (NOT UserProfile object)
    assert isinstance(context['profile'], dict)
    assert 'username' in context['profile']
    assert 'display_name' in context['profile']
    assert context['profile']['username'] == 'alice_fe_v2'
    
    # Stats should be dict (NOT UserProfileStats object)
    assert isinstance(context['stats'], dict)
    assert context['stats']['tournaments_played'] == 5
    assert context['stats']['tournaments_won'] == 2
    
    # NO raw User object in context
    assert 'user' not in context
    assert 'user_profile' not in context


def test_context_builder_filters_pii_for_anonymous(alice_fe_v2):
    """Anonymous viewer does NOT see email or other PII"""
    context = build_public_profile_context(None, 'alice_fe_v2')
    
    # Profile dict should NOT contain email
    assert 'email' not in context['profile']
    
    # Owner-only data should NOT be present
    assert 'owner_data' not in context


def test_context_builder_shows_owner_data_for_owner(alice_fe_v2):
    """Owner viewing own profile sees email and wallet"""
    context = build_public_profile_context(
        alice_fe_v2,
        'alice_fe_v2',
        requested_sections=['basic', 'owner_only']
    )
    
    assert context['is_owner'] is True
    assert 'owner_data' in context
    assert context['owner_data']['email'] == 'alice@example.com'
    assert 'wallet' in context['owner_data']


def test_context_builder_handles_nonexistent_user():
    """Context builder returns error for nonexistent user"""
    context = build_public_profile_context(None, 'nonexistent_user_xyz')
    
    assert context['can_view'] is False
    assert context['profile'] is None
    assert 'not found' in context['error'].lower()


# ============================================
# TEST: profile_public_v2 View
# ============================================

def test_profile_public_v2_renders_successfully(client, alice_fe_v2):
    """Public profile v2 renders for anonymous user"""
    response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'alice_fe_v2'}))
    
    assert response.status_code == 200
    assert b'Alice Frontend' in response.content
    assert b'alice_fe_v2' in response.content


def test_profile_public_v2_no_raw_user_in_context(client, alice_fe_v2):
    """Profile v2 does NOT pass raw User object to template"""
    response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'alice_fe_v2'}))
    
    context = response.context
    
    # Should NOT have raw User or UserProfile objects
    assert 'user' not in context or context['user'] != alice_fe_v2
    assert 'user_profile' not in context
    assert 'profile_obj' not in context
    
    # Should have safe profile dict
    assert 'profile' in context
    assert isinstance(context['profile'], dict)


def test_profile_public_v2_does_not_expose_email_to_anonymous(client, alice_fe_v2):
    """Anonymous user cannot see email in context"""
    response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'alice_fe_v2'}))
    
    # Email should NOT appear in rendered HTML
    assert b'alice@example.com' not in response.content
    
    # Context should NOT contain email in profile dict
    if 'profile' in response.context:
        assert 'email' not in response.context['profile']


def test_profile_public_v2_returns_404_for_nonexistent_user(client):
    """Profile v2 returns 404 for nonexistent user"""
    response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'nonexistent_xyz'}))
    
    assert response.status_code == 404


# ============================================
# TEST: profile_activity_v2 View
# ============================================

def test_profile_activity_v2_renders_successfully(client, alice_fe_v2):
    """Activity page renders for anonymous user"""
    response = client.get(reverse('user_profile:profile_activity_v2', kwargs={'username': 'alice_fe_v2'}))
    
    assert response.status_code == 200
    assert b'Activity Feed' in response.content


def test_profile_activity_v2_paginates_events(client, alice_fe_v2):
    """Activity page paginates events correctly"""
    # Create 30 activity events
    for i in range(30):
        UserActivity.objects.create(
            user=alice_fe_v2,  # ForeignKey to User, not UserProfile
            event_type='tournament_registered',
            metadata={'tournament_id': i}  # Field is 'metadata', not 'event_data'
        )
    
    # First page should show 25 events
    response = client.get(reverse('user_profile:profile_activity_v2', kwargs={'username': 'alice_fe_v2'}))
    assert response.status_code == 200
    
    context = response.context
    assert 'activity' in context
    assert len(context['activity']['activities']) == 25
    assert context['activity']['has_next'] is True
    assert context['activity']['total_count'] == 30


def test_profile_activity_v2_page_2_works(client, alice_fe_v2):
    """Activity page 2 renders correctly"""
    # Create 30 activity events
    for i in range(30):
        UserActivity.objects.create(
            user=alice_fe_v2,  # ForeignKey to User
            event_type='tournament_registered',
            metadata={'tournament_id': i}  # Field is 'metadata'
        )
    
    # Page 2 should show remaining 5 events
    response = client.get(
        reverse('user_profile:profile_activity_v2', kwargs={'username': 'alice_fe_v2'}) + '?page=2'
    )
    assert response.status_code == 200
    
    context = response.context
    assert len(context['activity']['activities']) == 5
    assert context['activity']['has_previous'] is True


# ============================================
# TEST: profile_settings_v2 View (Owner-Only)
# ============================================

def test_profile_settings_v2_requires_authentication(client, alice_fe_v2):
    """Settings page requires login"""
    response = client.get(reverse('user_profile:profile_settings_v2'))
    
    # Should redirect to login
    assert response.status_code == 302
    assert '/accounts/login/' in response.url or '/login/' in response.url


def test_profile_settings_v2_renders_for_owner(client, alice_fe_v2):
    """Settings page renders for authenticated owner"""
    client.force_login(alice_fe_v2)
    response = client.get(reverse('user_profile:profile_settings_v2'))
    
    assert response.status_code == 200
    assert b'Profile Settings' in response.content
    assert b'Alice Frontend' in response.content


def test_profile_settings_v2_shows_game_profiles(client, alice_fe_v2):
    """Settings page shows existing game profiles"""
    client.force_login(alice_fe_v2)
    response = client.get(reverse('user_profile:profile_settings_v2'))
    
    assert response.status_code == 200
    # Should show game profile data from context
    context = response.context
    assert 'games' in context
    assert len(context['games']) == 1
    assert context['games'][0]['game'] == 'valorant'
    assert context['games'][0]['ign'] == 'AliceVAL'


# ============================================
# TEST: profile_privacy_v2 View (Owner-Only)
# ============================================

def test_profile_privacy_v2_requires_authentication(client, alice_fe_v2):
    """Privacy page requires login"""
    response = client.get(reverse('user_profile:profile_privacy_v2'))
    
    # Should redirect to login
    assert response.status_code == 302


def test_profile_privacy_v2_renders_for_owner(client, alice_fe_v2):
    """Privacy page renders for authenticated owner"""
    client.force_login(alice_fe_v2)
    response = client.get(reverse('user_profile:profile_privacy_v2'))
    
    assert response.status_code == 200
    assert b'Privacy Settings' in response.content


def test_profile_privacy_v2_shows_current_settings(client, alice_fe_v2):
    """Privacy page shows current privacy settings"""
    # Create or update privacy settings (get_or_create to avoid IntegrityError)
    profile = alice_fe_v2.profile
    privacy, created = PrivacySettings.objects.get_or_create(
        user_profile=profile,
        defaults={
            'show_email': False,
            'allow_friend_requests': True
        }
    )
    if not created:
        privacy.show_email = False
        privacy.allow_friend_requests = True
        privacy.save()
    
    client.force_login(alice_fe_v2)
    response = client.get(reverse('user_profile:profile_privacy_v2'))
    
    assert response.status_code == 200
    context = response.context
    assert 'owner_data' in context
    assert 'privacy_settings' in context['owner_data']
    assert context['owner_data']['privacy_settings']['show_email'] is False
    assert context['owner_data']['privacy_settings']['allow_friend_requests'] is True


# ============================================
# TEST: Privacy Enforcement
# ============================================

def test_public_profile_does_not_expose_is_staff(client):
    """Public profile does NOT expose is_staff field"""
    # Create staff user
    staff_user = User.objects.create_user(
        username='staff_user_fe',
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )
    # Profile auto-created by signal
    profile = staff_user.profile
    profile.display_name = 'Staff User'
    profile.save()
    
    # Anonymous view should NOT see is_staff
    response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'staff_user_fe'}))
    
    # is_staff should NOT appear in HTML
    assert b'is_staff' not in response.content.lower()
    assert b'True' not in response.content or b'staff_user_fe' not in response.content
    
    # Context should NOT have is_staff in profile dict
    if 'profile' in response.context:
        assert 'is_staff' not in response.context['profile']


# ============================================
# REGRESSION TEST: Follow Import (UP-PHASE10)
# ============================================

def test_profile_public_v2_follow_import_regression(client, alice_fe_v2, bob_fe_v2):
    """
    Regression test for Follow ImportError (UP-PHASE10 Blocker A).
    
    Before fix: ImportError: cannot import name 'Follow' from apps.user_profile.models
    After fix: Follow is properly exported from models.__init__.py
    
    This test ensures profile pages load without import errors.
    """
    # Create a follow relationship
    from apps.user_profile.models import Follow
    Follow.objects.create(follower=bob_fe_v2, following=alice_fe_v2)
    
    # Test 1: Profile loads for anonymous user (no follow context)
    response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'alice_fe_v2'}))
    assert response.status_code == 200, "Profile should load without Follow import error"
    assert 'follower_count' in response.context
    assert response.context['follower_count'] == 1
    
    # Test 2: Profile loads for authenticated user (with follow check)
    client.force_login(bob_fe_v2)
    response = client.get(reverse('user_profile:profile_public_v2', kwargs={'username': 'alice_fe_v2'}))
    assert response.status_code == 200
    assert response.context['is_following'] is True
    assert response.context['following_count'] == 0  # Bob is following 1 (Alice)
    assert response.context['follower_count'] == 1  # Alice has 1 follower (Bob)


# ============================================
# REGRESSION TEST: Settings Page Alpine (UP-PHASE10)
# ============================================

def test_settings_page_loads_without_js_errors(client, alice_fe_v2):
    """
    Regression test for Settings Page Alpine boot failure (UP-PHASE10 Blocker B).
    
    Before fix: settingsApp is not defined, Alpine expression errors
    After fix: settingsApp() is properly defined on window before Alpine loads
    
    This test ensures /me/settings/ renders with correct JS includes.
    """
    client.force_login(alice_fe_v2)
    response = client.get(reverse('user_profile:profile_settings_v2'))
    
    assert response.status_code == 200, "Settings page should load"
    
    # Check Alpine CDN is loaded
    assert b'alpinejs' in response.content, "Alpine.js should be included"
    
    # Check settingsApp() is defined (should be in window scope)
    assert b'window.settingsApp' in response.content or b'function settingsApp()' in response.content, \
        "settingsApp() must be defined before Alpine initializes"
    
    # Check main settings container has x-data attribute
    assert b'x-data="settingsApp()"' in response.content, \
        "Settings container must have Alpine x-data directive"
    
    # Check no obvious JS syntax errors (emojis should be UTF-8 encoded properly)
    content_str = response.content.decode('utf-8')
    assert '⚙️' in content_str or 'Menu' in content_str, "Emojis or fallback text should render"


def test_settings_page_includes_all_sections(client, alice_fe_v2):
    """Verify settings page includes all required sections."""
    client.force_login(alice_fe_v2)
    response = client.get(reverse('user_profile:profile_settings_v2'))
    
    content = response.content.decode('utf-8')
    
    # Check all section navigation items exist
    assert 'activeSection === \'profile\'' in content
    assert 'activeSection === \'privacy\'' in content
    assert 'activeSection === \'notifications\'' in content
    assert 'activeSection === \'platform\'' in content
    assert 'activeSection === \'wallet\'' in content
    assert 'activeSection === \'account\'' in content


def test_settings_page_requires_authentication(client):
    """Unauthenticated users should be redirected to login."""
    response = client.get(reverse('user_profile:profile_settings_v2'))
    
    # Should redirect to login (302) or return 403/401
    assert response.status_code in [302, 401, 403], \
        "Settings page should require authentication"

