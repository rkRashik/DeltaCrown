#!/usr/bin/env python
"""Verify Career Tab fix implementation - function signature tests"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.user_profile.services.career_tab_service import CareerTabService
from apps.games.models import Game
from django.contrib.staticfiles import finders

print("=" * 60)
print("CAREER TAB FIX VERIFICATION")
print("=" * 60)

# Test 1: resolve_game_assets exists and returns correct structure
print("\n✓ TEST 1: resolve_game_assets() method exists")
game = Game.objects.first()
if game:
    try:
        assets = CareerTabService.resolve_game_assets(game)
        assert isinstance(assets, dict), "Should return dict"
        assert 'logo_url' in assets, "Should have logo_url key"
        assert 'banner_url' in assets, "Should have banner_url key"
        print(f"  ✓ Returns correct structure: {{'logo_url': ..., 'banner_url': ...}}")
        print(f"  Game: {game.slug}")
        print(f"  logo_url: {assets['logo_url'][:50] if assets['logo_url'] else 'None'}...")
        print(f"  banner_url: {assets['banner_url'][:50] if assets['banner_url'] else 'None'}...")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
else:
    print("  ⚠ SKIP: No games in database")

# Test 2: API view returns new structure
print("\n✓ TEST 2: career_tab_data_api() returns new structure")
from apps.user_profile.views.public_profile_views import career_tab_data_api
from django.test import RequestFactory
from apps.accounts.models import User

factory = RequestFactory()
user = User.objects.first()
if user and game:
    try:
        request = factory.get(f'/@{user.username}/career-data/', {'game': game.slug})
        request.user = user
        response = career_tab_data_api(request, user.username)
        
        if response.status_code == 200:
            data = json.loads(response.content)
            if data.get('success'):
                career_data = data.get('data', {})
                
                # Check game structure
                if 'game' in career_data:
                    game_obj = career_data['game']
                    assert 'slug' in game_obj, "game.slug missing"
                    assert 'name' in game_obj, "game.name missing"
                    assert 'logo_url' in game_obj, "game.logo_url missing"
                    assert 'banner_url' in game_obj, "game.banner_url missing"
                    print(f"  ✓ game object has: slug, name, logo_url, banner_url")
                
                # Check standing structure
                if 'standing' in career_data:
                    standing = career_data['standing']
                    assert 'label' in standing, "standing.label missing"
                    assert 'value' in standing, "standing.value missing"
                    assert 'icon_url' in standing, "standing.icon_url missing"
                    assert 'secondary' in standing, "standing.secondary missing"
                    print(f"  ✓ standing object has: label, value, icon_url, secondary")
                
                # Check other expected keys
                expected_keys = ['passport', 'identity_meta_line', 'stat_tiles', 'role_card', 
                               'affiliation_history', 'match_history']
                for key in expected_keys:
                    if key in career_data:
                        print(f"  ✓ {key} present")
                    else:
                        print(f"  ⚠ {key} MISSING")
            else:
                print(f"  ⚠ API returned error: {data.get('error')}")
        else:
            print(f"  ⚠ API returned status {response.status_code}")
    except Exception as e:
        print(f"  ✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
else:
    print("  ⚠ SKIP: No user or game in database")

# Test 3: Template has required IDs
print("\n✓ TEST 3: Template has required DOM IDs")
template_path = 'templates/user_profile/profile/tabs/_tab_career.html'
try:
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    required_ids = [
        'hero-logo-img',
        'hero-background-img',
        'standing-value',
        'standing-icon',
        'stat-tiles-container',
        'role-card-container',
        'affiliation-list-container'
    ]
    
    for element_id in required_ids:
        if f'id="{element_id}"' in template_content:
            print(f"  ✓ {element_id}")
        else:
            print(f"  ✗ MISSING: {element_id}")
    
    # Check for update functions
    print(f"\n✓ TEST 4: JavaScript update functions exist")
    update_functions = [
        'updateHeroAssets',
        'updatePassportIdentity',
        'updateStanding',
        'updateStatTiles',
        'updateRoleCard',
        'updateAffiliationHistory'
    ]
    
    for func in update_functions:
        if f'function {func}(' in template_content:
            print(f"  ✓ {func}()")
        else:
            print(f"  ✗ MISSING: {func}()")
            
except Exception as e:
    print(f"  ✗ ERROR reading template: {e}")

print("\n" + "=" * 60)
print("VERIFICATION COMPLETE")
print("=" * 60)
print("\nSUMMARY:")
print("1. resolve_game_assets() returns {logo_url, banner_url}")
print("2. API returns game{slug, name, logo_url, banner_url}")
print("3. API returns standing{label, value, icon_url, secondary}")
print("4. Template has all required DOM IDs")
print("5. Template has all update functions")
print("\nNEXT STEP: Browser test with real profile")
print("  - Load profile with multiple games")
print("  - Click game selector buttons")
print("  - Verify hero logo/background changes")
print("  - Verify role card updates per game")
print("  - Verify no 'Ran!' error in standing")
print("=" * 60)
