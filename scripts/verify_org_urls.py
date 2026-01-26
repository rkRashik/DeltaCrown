#!/usr/bin/env python
"""
Quick verification script for organizations URL names.
Usage: python scripts/verify_org_urls.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.urls import reverse, NoReverseMatch

# Canonical URL names that must work
url_tests = [
    ('organizations:vnext_hub', {}, '/teams/vnext/'),
    ('organizations:team_create', {}, '/teams/create/'),
    ('organizations:team_invites', {}, '/teams/invites/'),
    ('organizations:team_detail', {'team_slug': 'test-team'}, '/teams/test-team/'),
    ('organizations:organization_detail', {'org_slug': 'test-org'}, '/orgs/test-org/'),
]

# Forbidden URL names that should NOT work
forbidden_tests = [
    ('organizations:hub', {}),  # Should be vnext_hub
    ('organizations:create', {}),  # Should be team_create
    ('organizations:invites', {}),  # Should be team_invites
    ('organizations:detail', {'slug': 'test'}),  # Should be team_detail or organization_detail
]

print("=" * 70)
print("Organizations URL Name Contract Verification")
print("=" * 70)
print()

print("✓ Testing canonical URL names...")
print("-" * 70)
passed = 0
failed = 0

for url_name, kwargs, expected_path in url_tests:
    try:
        path = reverse(url_name, kwargs=kwargs)
        if path == expected_path:
            print(f"✓ {url_name:45} → {path}")
            passed += 1
        else:
            print(f"✗ {url_name:45} → {path} (expected {expected_path})")
            failed += 1
    except NoReverseMatch as e:
        print(f"✗ {url_name:45} → NoReverseMatch: {e}")
        failed += 1
    except Exception as e:
        print(f"✗ {url_name:45} → Error: {e}")
        failed += 1

print()
print("✓ Verifying forbidden URL names are NOT registered...")
print("-" * 70)

for url_name, kwargs in forbidden_tests:
    try:
        path = reverse(url_name, kwargs=kwargs)
        print(f"✗ {url_name:45} → {path} (SHOULD NOT EXIST!)")
        failed += 1
    except NoReverseMatch:
        print(f"✓ {url_name:45} → Correctly raises NoReverseMatch")
        passed += 1
    except Exception as e:
        print(f"? {url_name:45} → Unexpected error: {e}")

print()
print("=" * 70)
print(f"Results: {passed} passed, {failed} failed")
print("=" * 70)

if failed > 0:
    sys.exit(1)
else:
    print("\n✓ All URL name contracts are correct!")
    sys.exit(0)
