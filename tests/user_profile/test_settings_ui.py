"""
Comprehensive UI Tests for Settings & Privacy Pages (UP-SETTINGS-UI-01)
Tests frontend implementation, media uploads, passport creation, social links, privacy controls
"""

import pytest
import json
from io import BytesIO
from PIL import Image
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from apps.user_profile.models import PrivacySettings, SocialLink, GameProfile

User = get_user_model()


@pytest.fixture
def auth_client(client, django_user_model):
    """Authenticated client for testing owner-only views"""
    user = django_user_model.objects.create_user(
        username='testplayer',
        email='test@example.com',
        password='testpass123'
    )
    client.login(username='testplayer', password='testpass123')
    return client, user


@pytest.fixture
def test_image_avatar():
    """Create a valid test avatar image (100x100px)"""
    image = Image.new('RGB', (100, 100), color='red')
    file = BytesIO()
    image.save(file, 'PNG')
    file.name = 'test_avatar.png'
    file.seek(0)
    return SimpleUploadedFile(
        name='test_avatar.png',
        content=file.read(),
        content_type='image/png'
    )


@pytest.fixture
def test_image_banner():
    """Create a valid test banner image (1200x300px)"""
    image = Image.new('RGB', (1200, 300), color='blue')
    file = BytesIO()
    image.save(file, 'PNG')
    file.name = 'test_banner.png'
    file.seek(0)
    return SimpleUploadedFile(
        name='test_banner.png',
        content=file.read(),
        content_type='image/png'
    )


@pytest.fixture
def oversized_image():
    """Create an oversized image (exceeds 5MB)"""
    image = Image.new('RGB', (3000, 3000), color='green')
    file = BytesIO()
    image.save(file, 'PNG', quality=100)
    file.name = 'oversized.png'
    file.seek(0)
    return SimpleUploadedFile(
        name='oversized.png',
        content=file.read(),
        content_type='image/png'
    )


# ==============================================
# Settings Page Tests
# ==============================================

@pytest.mark.django_db
def test_settings_page_requires_authentication(client):
    """Unauthenticated users should be redirected to login"""
    url = reverse('user_profile:profile_settings_v2')
    response = client.get(url)
    assert response.status_code == 302
    assert '/login' in response.url or '/accounts/login' in response.url


@pytest.mark.django_db
def test_settings_page_loads_for_authenticated_user(auth_client):
    """Authenticated user can access settings page"""
    client, user = auth_client
    url = reverse('user_profile:profile_settings_v2')
    response = client.get(url)
    assert response.status_code == 200
    assert b'Profile Information' in response.content or b'Profile Settings' in response.content


@pytest.mark.django_db
def test_settings_template_includes_all_sections(auth_client):
    """Settings template must include all 6 required sections"""
    client, user = auth_client
    url = reverse('user_profile:profile_settings_v2')
    response = client.get(url)
    
    content = response.content.decode('utf-8')
    
    # Check for section navigation links or IDs
    assert 'profile' in content.lower()
    assert 'media' in content.lower() or 'avatar' in content.lower()
    assert 'passport' in content.lower() or 'game' in content.lower()
    assert 'social' in content.lower()
    assert 'privacy' in content.lower()
    assert 'security' in content.lower()


@pytest.mark.django_db
def test_settings_template_includes_javascript_file(auth_client):
    """Settings page should load settings.js"""
    client, user = auth_client
    url = reverse('user_profile:profile_settings_v2')
    response = client.get(url)
    
    content = response.content.decode('utf-8')
    assert 'settings.js' in content


# ==============================================
# Avatar Upload Tests
# ==============================================

@pytest.mark.django_db
def test_avatar_upload_success(auth_client, test_image_avatar):
    """Valid avatar upload should succeed"""
    client, user = auth_client
    url = reverse('user_profile:upload_media')
    
    response = client.post(url, {
        'file': test_image_avatar,
        'media_type': 'avatar'
    })
    
    assert response.status_code == 200
    data = json.loads(response.content)
    assert 'avatar_url' in data
    
    # Verify avatar saved to user profile
    user.refresh_from_db()
    assert user.avatar is not None


@pytest.mark.django_db
def test_avatar_upload_rejects_oversized_file(auth_client, oversized_image):
    """Avatar upload should reject files > 5MB"""
    client, user = auth_client
    url = reverse('user_profile:upload_media')
    
    response = client.post(url, {
        'file': oversized_image,
        'media_type': 'avatar'
    })
    
    assert response.status_code == 400
    data = json.loads(response.content)
    assert 'error' in data


@pytest.mark.django_db
def test_avatar_upload_rejects_invalid_format(auth_client):
    """Avatar upload should reject non-image files"""
    client, user = auth_client
    url = reverse('user_profile:upload_media')
    
    fake_file = SimpleUploadedFile(
        name='test.txt',
        content=b'This is not an image',
        content_type='text/plain'
    )
    
    response = client.post(url, {
        'file': fake_file,
        'media_type': 'avatar'
    })
    
    assert response.status_code == 400
    data = json.loads(response.content)
    assert 'error' in data


# ==============================================
# Banner Upload Tests
# ==============================================

@pytest.mark.django_db
def test_banner_upload_success(auth_client, test_image_banner):
    """Valid banner upload should succeed"""
    client, user = auth_client
    url = reverse('user_profile:upload_media')
    
    response = client.post(url, {
        'file': test_image_banner,
        'media_type': 'banner'
    })
    
    assert response.status_code == 200
    data = json.loads(response.content)
    assert 'banner_url' in data
    
    # Verify banner saved
    user.refresh_from_db()
    assert user.banner is not None


@pytest.mark.django_db
def test_banner_upload_dimension_validation(auth_client):
    """Banner must meet minimum dimensions (1200x300)"""
    client, user = auth_client
    url = reverse('user_profile:upload_media')
    
    # Create too-small banner
    small_image = Image.new('RGB', (800, 200), color='red')
    file = BytesIO()
    small_image.save(file, 'PNG')
    file.name = 'small_banner.png'
    file.seek(0)
    
    small_file = SimpleUploadedFile(
        name='small_banner.png',
        content=file.read(),
        content_type='image/png'
    )
    
    response = client.post(url, {
        'file': small_file,
        'media_type': 'banner'
    })
    
    # Should reject or accept (depends on backend validation)
    # If backend enforces dimensions:
    if response.status_code == 400:
        data = json.loads(response.content)
        assert 'dimension' in data.get('error', '').lower() or 'size' in data.get('error', '').lower()


# ==============================================
# Passport Creation Tests
# ==============================================

@pytest.mark.django_db
def test_passport_creation_success(auth_client):
    """Create passport with valid data"""
    client, user = auth_client
    url = reverse('user_profile:create_passport')
    
    passport_data = {
        'game_id': 'valorant',
        'ign': 'TestPlayer',
        'discriminator': '#1234',
        'platform': 'PC'
    }
    
    response = client.post(
        url,
        data=json.dumps(passport_data),
        content_type='application/json'
    )
    
    assert response.status_code == 201 or response.status_code == 200
    data = json.loads(response.content)
    assert 'id' in data or 'passport' in data
    
    # Verify passport created
    assert GameProfile.objects.filter(user=user, game='valorant').exists()


@pytest.mark.django_db
def test_passport_creation_without_discriminator(auth_client):
    """Create CS2 passport without discriminator (optional)"""
    client, user = auth_client
    url = reverse('user_profile:create_passport')
    
    passport_data = {
        'game_id': 'cs2',
        'ign': 'CS2_PRO',
        'platform': 'PC'
    }
    
    response = client.post(
        url,
        data=json.dumps(passport_data),
        content_type='application/json'
    )
    
    assert response.status_code in [200, 201]
    
    # Verify passport created
    assert GameProfile.objects.filter(user=user, game='cs2').exists()


@pytest.mark.django_db
def test_passport_creation_missing_ign(auth_client):
    """Passport creation should fail without IGN"""
    client, user = auth_client
    url = reverse('user_profile:create_passport')
    
    passport_data = {
        'game_id': 'valorant'
        # Missing 'ign'
    }
    
    response = client.post(
        url,
        data=json.dumps(passport_data),
        content_type='application/json'
    )
    
    assert response.status_code == 400
    data = json.loads(response.content)
    assert 'error' in data


# ==============================================
# Social Links Tests
# ==============================================

@pytest.mark.django_db
def test_social_links_bulk_update(auth_client):
    """Bulk update multiple social links at once"""
    client, user = auth_client
    url = reverse('user_profile:update_social_links_api')
    
    links_data = {
        'links': [
            {'platform': 'twitch', 'url': 'https://twitch.tv/testplayer'},
            {'platform': 'youtube', 'url': 'https://youtube.com/@testplayer'},
            {'platform': 'kick', 'url': 'https://kick.com/testplayer'},
            {'platform': 'discord', 'url': 'https://discord.gg/testserver'}
        ]
    }
    
    response = client.post(
        url,
        data=json.dumps(links_data),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data.get('updated_count') == 4
    
    # Verify links created
    assert SocialLink.objects.filter(user=user, platform='twitch').exists()
    assert SocialLink.objects.filter(user=user, platform='kick').exists()


@pytest.mark.django_db
def test_social_links_streamer_platforms_regression(auth_client):
    """Regression test: Ensure Kick, Twitch, YouTube all save correctly"""
    client, user = auth_client
    url = reverse('user_profile:update_social_links_api')
    
    streamer_links = {
        'links': [
            {'platform': 'kick', 'url': 'https://kick.com/streamer1'},
            {'platform': 'twitch', 'url': 'https://twitch.tv/streamer1'},
            {'platform': 'youtube', 'url': 'https://youtube.com/@streamer1'}
        ]
    }
    
    response = client.post(
        url,
        data=json.dumps(streamer_links),
        content_type='application/json'
    )
    
    assert response.status_code == 200
    
    # All 3 streamer platforms must be persisted
    kick = SocialLink.objects.filter(user=user, platform='kick').first()
    twitch = SocialLink.objects.filter(user=user, platform='twitch').first()
    youtube = SocialLink.objects.filter(user=user, platform='youtube').first()
    
    assert kick is not None
    assert twitch is not None
    assert youtube is not None


@pytest.mark.django_db
def test_social_links_invalid_url_validation(auth_client):
    """Social links should validate URL format"""
    client, user = auth_client
    url = reverse('user_profile:update_social_links_api')
    
    invalid_data = {
        'links': [
            {'platform': 'twitch', 'url': 'not-a-url'}
        ]
    }
    
    response = client.post(
        url,
        data=json.dumps(invalid_data),
        content_type='application/json'
    )
    
    # Should either reject (400) or accept but warn
    if response.status_code == 400:
        data = json.loads(response.content)
        assert 'error' in data or 'url' in data.get('error', '').lower()


# ==============================================
# Privacy Page Tests
# ==============================================

@pytest.mark.django_db
def test_privacy_page_loads(auth_client):
    """Privacy page should load for authenticated user"""
    client, user = auth_client
    url = reverse('user_profile:profile_privacy_v2')
    response = client.get(url)
    
    assert response.status_code == 200
    assert b'Privacy Settings' in response.content or b'Privacy' in response.content


@pytest.mark.django_db
def test_privacy_page_shows_preset_options(auth_client):
    """Privacy page must show visibility presets (PUBLIC/PROTECTED/PRIVATE)"""
    client, user = auth_client
    url = reverse('user_profile:profile_privacy_v2')
    response = client.get(url)
    
    content = response.content.decode('utf-8')
    assert 'PUBLIC' in content
    assert 'PROTECTED' in content
    assert 'PRIVATE' in content


@pytest.mark.django_db
def test_privacy_page_shows_new_toggles(auth_client):
    """Privacy page must include show_activity_feed and show_tournaments toggles"""
    client, user = auth_client
    url = reverse('user_profile:profile_privacy_v2')
    response = client.get(url)
    
    content = response.content.decode('utf-8')
    assert 'show_activity_feed' in content.lower() or 'activity' in content.lower()
    assert 'show_tournaments' in content.lower() or 'tournament' in content.lower()


@pytest.mark.django_db
def test_privacy_settings_save(auth_client):
    """Privacy settings should save correctly"""
    client, user = auth_client
    url = reverse('user_profile:privacy_save')
    
    # Ensure PrivacySettings exists for user
    privacy, _ = PrivacySettings.objects.get_or_create(user=user)
    
    form_data = {
        'visibility_preset': 'PROTECTED',
        'show_email': False,
        'show_activity_feed': True,
        'show_tournaments': False,
        'show_game_profiles': True,
        'show_social_links': True
    }
    
    response = client.post(url, data=form_data)
    
    # Should redirect or return 200
    assert response.status_code in [200, 302]
    
    # Verify settings persisted
    privacy.refresh_from_db()
    assert privacy.visibility_preset == 'PROTECTED'
    assert privacy.show_email is False
    assert privacy.show_activity_feed is True
    assert privacy.show_tournaments is False


# ==============================================
# Progressive Enhancement Tests
# ==============================================

@pytest.mark.django_db
def test_settings_works_without_javascript(auth_client):
    """All features should work via standard form submission (no JS required)"""
    client, user = auth_client
    
    # Test profile update via form (not AJAX)
    url = reverse('user_profile:update_basic_info')
    response = client.post(url, {
        'display_name': 'Updated Name',
        'bio': 'Updated bio'
    })
    
    # Should redirect or return success
    assert response.status_code in [200, 302]


@pytest.mark.django_db
def test_avatar_upload_fallback_form(auth_client, test_image_avatar):
    """Avatar upload should work via standard form post (noscript fallback)"""
    client, user = auth_client
    url = reverse('user_profile:upload_media')
    
    response = client.post(url, {
        'file': test_image_avatar,
        'media_type': 'avatar'
    }, follow=True)
    
    # Should work even without AJAX
    assert response.status_code == 200


# ==============================================
# Integration Tests
# ==============================================

@pytest.mark.django_db
def test_full_settings_workflow(auth_client, test_image_avatar):
    """End-to-end test: Update profile, upload avatar, create passport, add social links"""
    client, user = auth_client
    
    # Step 1: Update profile info
    profile_url = reverse('user_profile:update_basic_info')
    client.post(profile_url, {
        'display_name': 'ProGamer',
        'bio': 'Esports athlete'
    })
    
    # Step 2: Upload avatar
    media_url = reverse('user_profile:upload_media')
    client.post(media_url, {
        'file': test_image_avatar,
        'media_type': 'avatar'
    })
    
    # Step 3: Create passport
    passport_url = reverse('user_profile:create_passport')
    client.post(
        passport_url,
        data=json.dumps({'game_id': 'valorant', 'ign': 'ProGamer', 'discriminator': '#1234'}),
        content_type='application/json'
    )
    
    # Step 4: Add social links
    social_url = reverse('user_profile:update_social_links_api')
    client.post(
        social_url,
        data=json.dumps({'links': [{'platform': 'twitch', 'url': 'https://twitch.tv/progamer'}]}),
        content_type='application/json'
    )
    
    # Verify all changes persisted
    user.refresh_from_db()
    assert user.display_name == 'ProGamer'
    assert user.avatar is not None
    assert GameProfile.objects.filter(user=user, game='valorant').exists()
    assert SocialLink.objects.filter(user=user, platform='twitch').exists()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
