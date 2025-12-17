#!/usr/bin/env python
"""
Test script for the new game profile system with 11 games.
This verifies that the unified game_profiles field works correctly.
"""

import os
import sys
import django

# Setup Django before any imports
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

# Force database connection
from django.db import connection
connection.ensure_connection()

from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.games.constants import ALL_GAMES, SUPPORTED_GAMES, get_game_info
from apps.games.models import Game

User = get_user_model()

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")

def print_success(text):
    print(f"✅ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def print_error(text):
    print(f"❌ {text}")

def test_game_constants():
    """Test that game constants are properly set up."""
    print_header("Testing Game Constants")
    
    # Test ALL_GAMES
    print_info(f"ALL_GAMES contains {len(ALL_GAMES)} games")
    expected_games = ['valorant', 'cs2', 'dota2', 'ea-fc', 'efootball', 'pubgm', 'mlbb', 'freefire', 'codm', 'rocketleague', 'r6siege']
    
    if set(ALL_GAMES) == set(expected_games):
        print_success(f"ALL_GAMES correct: {', '.join(ALL_GAMES)}")
    else:
        print_error(f"ALL_GAMES mismatch! Expected: {expected_games}")
        return False
    
    # Test SUPPORTED_GAMES structure
    for game in ALL_GAMES:
        game_info = get_game_info(game)
        if game_info:
            print_success(f"{game}: {game_info['display_name']} ({game_info['category']})")
        else:
            print_error(f"Missing game info for {game}")
            return False
    
    return True

def test_database_games():
    """Test that games are properly seeded in database."""
    print_header("Testing Database Games")
    
    total_games = Game.objects.count()
    active_games = Game.objects.filter(is_active=True).count()
    featured_games = Game.objects.filter(is_featured=True).count()
    
    print_info(f"Total Games in DB: {total_games}")
    print_info(f"Active Games: {active_games}")
    print_info(f"Featured Games: {featured_games}")
    
    if total_games >= 11:
        print_success(f"Database has {total_games} games (expected at least 11)")
    else:
        print_error(f"Database only has {total_games} games (expected at least 11)")
        return False
    
    # Check each game exists
    for game_slug in ALL_GAMES:
        game_info = SUPPORTED_GAMES.get(game_slug, {})
        game = Game.objects.filter(slug=game_slug).first()
        if game:
            print_success(f"{game_info.get('display_name', game_slug)}: ✓ Found in DB")
        else:
            print_error(f"{game_slug}: Missing from database!")
            return False
    
    return True

def test_user_profile_methods():
    """Test UserProfile game profile methods."""
    print_header("Testing UserProfile Methods")
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_game_profile_user',
        defaults={'email': 'test@deltacrown.com'}
    )
    profile = user.profile
    
    if created:
        print_info("Created test user: test_game_profile_user")
    else:
        print_info("Using existing test user: test_game_profile_user")
    
    # Test 1: Add VALORANT profile
    print_info("\nTest 1: Adding VALORANT profile...")
    profile.set_game_profile('valorant', {
        'game': 'valorant',
        'ign': 'TestPlayer#0001',
        'role': 'Duelist',
        'rank': 'Immortal 2',
        'platform': 'PC',
        'is_verified': False,
        'metadata': {}
    })
    profile.save()
    
    valorant_profile = profile.get_game_profile('valorant')
    if valorant_profile and valorant_profile['ign'] == 'TestPlayer#0001':
        print_success("VALORANT profile added successfully")
        print_info(f"  IGN: {valorant_profile['ign']}")
        print_info(f"  Role: {valorant_profile.get('role')}")
        print_info(f"  Rank: {valorant_profile.get('rank')}")
    else:
        print_error("Failed to add VALORANT profile")
        return False
    
    # Test 2: Add MLBB profile with server_id
    print_info("\nTest 2: Adding MLBB profile with server_id...")
    profile.set_game_profile('mlbb', {
        'game': 'mlbb',
        'ign': '123456789',
        'role': 'Marksman',
        'rank': 'Mythic Glory',
        'platform': 'Mobile',
        'is_verified': False,
        'metadata': {'server_id': '1234'}
    })
    profile.save()
    
    mlbb_profile = profile.get_game_profile('mlbb')
    if mlbb_profile and mlbb_profile['ign'] == '123456789':
        print_success("MLBB profile added successfully")
        print_info(f"  IGN: {mlbb_profile['ign']}")
        print_info(f"  Server ID: {mlbb_profile.get('metadata', {}).get('server_id')}")
    else:
        print_error("Failed to add MLBB profile")
        return False
    
    # Test 3: Get all profiles
    print_info("\nTest 3: Getting all game profiles...")
    all_profiles = profile.get_all_game_profiles()
    if len(all_profiles) == 2:
        print_success(f"Found {len(all_profiles)} game profiles")
        for gp in all_profiles:
            print_info(f"  - {gp.get('game')}: {gp.get('ign')}")
    else:
        print_error(f"Expected 2 profiles, found {len(all_profiles)}")
        return False
    
    # Test 4: Get game_id shorthand
    print_info("\nTest 4: Testing get_game_id() shorthand...")
    valorant_ign = profile.get_game_id('valorant')
    if valorant_ign == 'TestPlayer#0001':
        print_success(f"get_game_id('valorant'): {valorant_ign}")
    else:
        print_error(f"get_game_id failed: {valorant_ign}")
        return False
    
    # Test 5: Update profile
    print_info("\nTest 5: Updating VALORANT profile...")
    profile.set_game_id('valorant', 'UpdatedPlayer#9999')
    profile.save()
    
    updated_ign = profile.get_game_id('valorant')
    if updated_ign == 'UpdatedPlayer#9999':
        print_success("Profile updated successfully")
    else:
        print_error(f"Update failed: {updated_ign}")
        return False
    
    # Test 6: Remove profile
    print_info("\nTest 6: Removing MLBB profile...")
    profile.remove_game_profile('mlbb')
    profile.save()
    
    mlbb_after_remove = profile.get_game_profile('mlbb')
    if mlbb_after_remove is None:
        print_success("MLBB profile removed successfully")
    else:
        print_error("Failed to remove MLBB profile")
        return False
    
    # Test 7: has_game_profile check
    print_info("\nTest 7: Testing has_game_profile()...")
    has_valorant = profile.has_game_profile('valorant')
    has_mlbb = profile.has_game_profile('mlbb')
    
    if has_valorant and not has_mlbb:
        print_success("has_game_profile() works correctly")
        print_info(f"  has_game_profile('valorant'): {has_valorant}")
        print_info(f"  has_game_profile('mlbb'): {has_mlbb}")
    else:
        print_error("has_game_profile() failed")
        return False
    
    # Cleanup: Remove test profile
    print_info("\nCleaning up test data...")
    profile.remove_game_profile('valorant')
    profile.save()
    print_success("Test data cleaned up")
    
    return True

def test_add_game_profile_method():
    """Test the add_game_profile convenience method."""
    print_header("Testing add_game_profile() Convenience Method")
    
    user, _ = User.objects.get_or_create(
        username='test_game_profile_user',
        defaults={'email': 'test@deltacrown.com'}
    )
    profile = user.profile
    
    # Test add_game_profile
    print_info("Adding CS2 profile using add_game_profile()...")
    profile.add_game_profile(
        game_code='cs2',
        ign='s1mple',
        role='AWPer',
        rank='Global Elite',
        platform='PC'
    )
    profile.save()
    
    cs2_profile = profile.get_game_profile('cs2')
    if cs2_profile and cs2_profile['ign'] == 's1mple':
        print_success("add_game_profile() works correctly")
        print_info(f"  IGN: {cs2_profile['ign']}")
        print_info(f"  Role: {cs2_profile.get('role')}")
    else:
        print_error("add_game_profile() failed")
        return False
    
    # Cleanup
    profile.remove_game_profile('cs2')
    profile.save()
    
    return True

def run_all_tests():
    """Run all tests and report results."""
    print_header("GAME PROFILE SYSTEM TEST SUITE")
    print_info("Testing the unified game_profiles field with 11 games")
    
    tests = [
        ("Game Constants", test_game_constants),
        ("Database Games", test_database_games),
        ("UserProfile Methods", test_user_profile_methods),
        ("add_game_profile() Method", test_add_game_profile_method),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Exception in {test_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Print summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{'='*70}")
    print(f"Results: {passed}/{total} tests passed")
    print(f"{'='*70}\n")
    
    if passed == total:
        print_success("ALL TESTS PASSED! 🎉")
        print_info("The game profile system is working correctly.")
        return True
    else:
        print_error(f"{total - passed} test(s) failed.")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
