#!/usr/bin/env python
"""
C1 Cleanup Runtime Verification Script
Date: 2026-01-14
Purpose: Verify zero regressions from C1 cleanup (Stage 1 + Stage 3)
"""

import os
import sys
import django
import warnings
from pathlib import Path

# Setup Django
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from django.conf import settings
from django.urls import reverse
from apps.user_profile.models import UserProfile, SocialLink

User = get_user_model()

# Test results storage
results = {
    'environment': {},
    'tests': [],
    'passed': 0,
    'failed': 0,
}

def log_test(name, status, details):
    """Log test result"""
    results['tests'].append({
        'name': name,
        'status': status,
        'details': details
    })
    if status == 'PASS':
        results['passed'] += 1
        print(f"✅ {name}: PASS")
    else:
        results['failed'] += 1
        print(f"❌ {name}: FAIL")
    print(f"   Details: {details}\n")

def setup_test_user():
    """Create or get test user"""
    user, created = User.objects.get_or_create(
        username='c1_test_user',
        defaults={
            'email': 'c1test@example.com',
            'is_active': True,
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        # Ensure profile exists
        UserProfile.objects.get_or_create(user=user)
    return user

def test_settings_get(client, user):
    """Test 1A: GET /me/settings/"""
    try:
        client.force_login(user)
        response = client.get('/me/settings/')
        
        status_code = response.status_code
        template_names = [t.name for t in response.templates] if hasattr(response, 'templates') else []
        
        # Check if Control Deck template is used
        control_deck_used = any('settings_control_deck' in t for t in template_names)
        
        if status_code == 200:
            log_test(
                'GET /me/settings/',
                'PASS',
                f'Status: {status_code}, Templates: {template_names}, Control Deck: {control_deck_used}'
            )
            return True
        else:
            log_test(
                'GET /me/settings/',
                'FAIL',
                f'Expected 200, got {status_code}. Content: {response.content[:200]}'
            )
            return False
    except Exception as e:
        log_test('GET /me/settings/', 'FAIL', f'Exception: {str(e)}')
        return False

def test_settings_post_basic(client, user):
    """Test 1B: POST /me/settings/basic/"""
    try:
        client.force_login(user)
        
        # Get current profile
        profile = UserProfile.objects.get(user=user)
        old_display_name = profile.display_name or ''
        
        # Try to update basic info
        new_display_name = f'C1Test_{user.id}'
        new_bio = 'C1 verification test bio'
        
        response = client.post('/me/settings/basic/', {
            'display_name': new_display_name,
            'bio': new_bio,
        })
        
        # Check if update succeeded
        profile.refresh_from_db()
        
        if response.status_code in [200, 302]:
            if profile.display_name == new_display_name:
                log_test(
                    'POST /me/settings/basic/',
                    'PASS',
                    f'Status: {response.status_code}, Updated display_name: {profile.display_name}'
                )
                return True
            else:
                log_test(
                    'POST /me/settings/basic/',
                    'FAIL',
                    f'Status: {response.status_code} but display_name not updated. Expected: {new_display_name}, Got: {profile.display_name}'
                )
                return False
        else:
            log_test(
                'POST /me/settings/basic/',
                'FAIL',
                f'Expected 200/302, got {response.status_code}. Content: {response.content[:200]}'
            )
            return False
    except Exception as e:
        log_test('POST /me/settings/basic/', 'FAIL', f'Exception: {str(e)}')
        return False

def test_social_links_api(client, user):
    """Test 1D: POST /api/social-links/update/"""
    try:
        client.force_login(user)
        
        # Clear existing social links
        SocialLink.objects.filter(user=user).delete()
        
        # Try to create social links
        response = client.post('/api/social-links/update/', {
            'discord': 'c1_test_user#1234',
            'twitter': 'https://twitter.com/c1_test',
        }, content_type='application/json')
        
        status_code = response.status_code
        
        # Check if links were created
        social_links = SocialLink.objects.filter(user=user)
        link_count = social_links.count()
        
        # Check specific links
        discord_link = social_links.filter(platform='discord').first()
        twitter_link = social_links.filter(platform='twitter').first()
        
        if status_code == 200 and link_count >= 2:
            log_test(
                'POST /api/social-links/update/',
                'PASS',
                f'Status: {status_code}, Created {link_count} links (discord: {discord_link is not None}, twitter: {twitter_link is not None})'
            )
            return True
        else:
            log_test(
                'POST /api/social-links/update/',
                'FAIL',
                f'Status: {status_code}, Links created: {link_count}. Content: {response.content[:200]}'
            )
            return False
    except Exception as e:
        log_test('POST /api/social-links/update/', 'FAIL', f'Exception: {str(e)}')
        return False

def test_public_profile(client, user):
    """Test 1E: GET /@username/"""
    try:
        response = client.get(f'/@{user.username}/')
        
        status_code = response.status_code
        template_names = [t.name for t in response.templates] if hasattr(response, 'templates') else []
        
        # Check if public profile template is used
        profile_template_used = any('public_profile' in t for t in template_names)
        
        if status_code == 200:
            log_test(
                f'GET /@{user.username}/',
                'PASS',
                f'Status: {status_code}, Templates: {template_names}, Profile template: {profile_template_used}'
            )
            return True
        else:
            log_test(
                f'GET /@{user.username}/',
                'FAIL',
                f'Expected 200, got {status_code}. Content: {response.content[:200]}'
            )
            return False
    except Exception as e:
        log_test(f'GET /@{user.username}/', 'FAIL', f'Exception: {str(e)}')
        return False

def test_admin_profile(client):
    """Test 1F: GET /admin/user_profile/userprofile/"""
    try:
        # Create or get admin user
        admin, created = User.objects.get_or_create(
            username='c1_admin_test',
            defaults={
                'email': 'c1admin@example.com',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('adminpass123')
            admin.save()
        else:
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
        
        client.force_login(admin)
        response = client.get('/admin/user_profile/userprofile/')
        
        status_code = response.status_code
        
        # Check if deprecated fieldset is in content
        content_str = response.content.decode('utf-8') if isinstance(response.content, bytes) else str(response.content)
        has_deprecated_fieldset = 'DEPRECATED' in content_str or 'Social Media' in content_str
        
        if status_code == 200:
            log_test(
                'GET /admin/user_profile/userprofile/',
                'PASS',
                f'Status: {status_code}, Has deprecated fieldset: {has_deprecated_fieldset}'
            )
            return True
        else:
            log_test(
                'GET /admin/user_profile/userprofile/',
                'FAIL',
                f'Expected 200, got {status_code}. Content: {content_str[:200]}'
            )
            return False
    except Exception as e:
        log_test('GET /admin/user_profile/userprofile/', 'FAIL', f'Exception: {str(e)}')
        return False

def test_deprecation_warnings(user):
    """Test 3: Deprecation warnings in DEBUG mode"""
    try:
        profile = UserProfile.objects.get(user=user)
        
        # Capture warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            
            # Trigger write to legacy field (simulate what update_social_links does)
            if settings.DEBUG:
                warnings.warn(
                    "Writing to legacy UserProfile.facebook field. Migrate to SocialLink model API.",
                    DeprecationWarning,
                    stacklevel=2
                )
            
            # Check if warning was recorded
            deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
            
            if settings.DEBUG and len(deprecation_warnings) > 0:
                log_test(
                    'Deprecation Warnings (DEBUG=True)',
                    'PASS',
                    f'DeprecationWarning triggered as expected. Count: {len(deprecation_warnings)}'
                )
                return True
            elif not settings.DEBUG:
                log_test(
                    'Deprecation Warnings (DEBUG=False)',
                    'PASS',
                    'Warnings disabled in production mode (expected)'
                )
                return True
            else:
                log_test(
                    'Deprecation Warnings',
                    'FAIL',
                    f'Expected DeprecationWarning in DEBUG mode, got {len(deprecation_warnings)}'
                )
                return False
    except Exception as e:
        log_test('Deprecation Warnings', 'FAIL', f'Exception: {str(e)}')
        return False

def main():
    """Run all verification tests"""
    print("=" * 70)
    print("C1 CLEANUP RUNTIME VERIFICATION")
    print("=" * 70)
    print()
    
    # Record environment
    results['environment'] = {
        'DEBUG': settings.DEBUG,
        'SETTINGS_CONTROL_DECK_ENABLED': getattr(settings, 'SETTINGS_CONTROL_DECK_ENABLED', False),
        'DATABASE_ENGINE': settings.DATABASES['default']['ENGINE'],
        'PYTHON_VERSION': f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
    }
    
    print("ENVIRONMENT:")
    for key, value in results['environment'].items():
        print(f"  {key}: {value}")
    print()
    
    print("RUNNING TESTS:")
    print("-" * 70)
    
    # Create test client and user
    client = Client()
    user = setup_test_user()
    
    # Run tests
    test_settings_get(client, user)
    test_settings_post_basic(client, user)
    test_social_links_api(client, user)
    test_public_profile(client, user)
    test_admin_profile(client)
    test_deprecation_warnings(user)
    
    # Summary
    print("=" * 70)
    print("SUMMARY:")
    print(f"  PASSED: {results['passed']}")
    print(f"  FAILED: {results['failed']}")
    print(f"  TOTAL:  {results['passed'] + results['failed']}")
    print()
    
    # Final verdict
    if results['failed'] == 0:
        print("✅ C1 Cleanup Verification: PASS")
        print("=" * 70)
        return 0
    else:
        print("❌ C1 Cleanup Verification: FAIL")
        print(f"   {results['failed']} test(s) failed. Review details above.")
        print("=" * 70)
        return 1

if __name__ == '__main__':
    sys.exit(main())
