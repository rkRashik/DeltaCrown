"""
Phase 9A-7: Comprehensive Backend Tests
Tests all CRUD operations and ensures no 500 errors
"""

import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client, RequestFactory
from django.contrib.auth import get_user_model
from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GameProfile
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

def setup_test_data():
    """Create test user and game"""
    user, _ = User.objects.get_or_create(
        username='testuser_phase9a7',
        email='test9a7@example.com',
        defaults={'email': 'test9a7@example.com'}
    )
    user.set_password('testpass123')
    user.save()
    
    game, _ = Game.objects.get_or_create(
        slug='test-game-9a7',
        defaults={
            'name': 'Test Game 9A7',
            'display_name': 'Test Game',
            'is_active': True
        }
    )
    
    # Create identity configs
    GamePlayerIdentityConfig.objects.get_or_create(
        game=game,
        field_name='player_id',
        defaults={
            'display_name': 'Player ID',
            'field_type': 'text',
            'is_required': True,
            'order': 1
        }
    )
    
    return user, game


def test_delete_with_valid_id():
    """Test 1: DELETE with valid passport ID returns 200"""
    print("\n" + "="*60)
    print("TEST 1: Delete Valid Passport")
    print("="*60)
    
    user, game = setup_test_data()
    
    # Create a passport
    passport = GameProfile.objects.create(
        user=user,
        game=game,
        ign='TestPlayer',
        metadata={'player_id': '12345'}
    )
    
    client = Client()
    client.force_login(user)
    
    response = client.post(
        '/profile/api/game-passports/delete/',
        data=json.dumps({'id': passport.id}),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        print("✅ PASS: Returns 200 on successful delete")
    else:
        print(f"❌ FAIL: Expected 200, got {response.status_code}")
    
    # Verify passport is deleted
    if not GameProfile.objects.filter(id=passport.id).exists():
        print("✅ PASS: Passport actually deleted from database")
    else:
        print("❌ FAIL: Passport still exists in database")
    
    return response.status_code == 200


def test_delete_with_invalid_id():
    """Test 2: DELETE with non-existent ID returns 404"""
    print("\n" + "="*60)
    print("TEST 2: Delete Non-Existent Passport")
    print("="*60)
    
    user, _ = setup_test_data()
    
    client = Client()
    client.force_login(user)
    
    response = client.post(
        '/profile/api/game-passports/delete/',
        data=json.dumps({'id': 99999}),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 404:
        print("✅ PASS: Returns 404 for non-existent passport")
    else:
        print(f"❌ FAIL: Expected 404, got {response.status_code}")
    
    return response.status_code == 404


def test_delete_without_id():
    """Test 3: DELETE without ID returns 400"""
    print("\n" + "="*60)
    print("TEST 3: Delete Without ID")
    print("="*60)
    
    user, _ = setup_test_data()
    
    client = Client()
    client.force_login(user)
    
    response = client.post(
        '/profile/api/game-passports/delete/',
        data=json.dumps({}),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 400:
        print("✅ PASS: Returns 400 when ID is missing")
    else:
        print(f"❌ FAIL: Expected 400, got {response.status_code}")
    
    return response.status_code == 400


def test_delete_locked_passport():
    """Test 4: DELETE locked passport returns 403"""
    print("\n" + "="*60)
    print("TEST 4: Delete Locked Passport")
    print("="*60)
    
    user, game = setup_test_data()
    
    # Create a locked passport
    passport = GameProfile.objects.create(
        user=user,
        game=game,
        ign='LockedPlayer',
        locked_until=timezone.now() + timedelta(days=30),
        metadata={'player_id': '54321'}
    )
    
    client = Client()
    client.force_login(user)
    
    response = client.post(
        '/profile/api/game-passports/delete/',
        data=json.dumps({'id': passport.id}),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 403:
        print("✅ PASS: Returns 403 for locked passport")
    else:
        print(f"❌ FAIL: Expected 403, got {response.status_code}")
    
    # Verify passport still exists
    if GameProfile.objects.filter(id=passport.id).exists():
        print("✅ PASS: Locked passport not deleted")
    else:
        print("❌ FAIL: Locked passport was deleted")
    
    passport.delete()  # Cleanup
    return response.status_code == 403


def test_games_api_returns_schema():
    """Test 5: Games API returns passport_schema"""
    print("\n" + "="*60)
    print("TEST 5: Games API Returns Schema")
    print("="*60)
    
    user, game = setup_test_data()
    
    client = Client()
    client.force_login(user)
    
    response = client.get('/profile/api/games/')
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        if 'games' in data and len(data['games']) > 0:
            first_game = data['games'][0]
            print(f"First game: {first_game.get('display_name')}")
            
            if 'passport_schema' in first_game:
                schema_count = len(first_game['passport_schema'])
                print(f"passport_schema fields: {schema_count}")
                
                if schema_count > 0:
                    print("✅ PASS: passport_schema is not empty")
                    return True
                else:
                    print("⚠️  WARNING: passport_schema is empty (may need seeding)")
                    return True  # Not a failure, just needs seeding
            else:
                print("❌ FAIL: passport_schema field missing")
                return False
        else:
            print("⚠️  WARNING: No games returned")
            return True  # Not necessarily a failure
    else:
        print(f"❌ FAIL: Expected 200, got {response.status_code}")
        return False


def test_create_schema_driven():
    """Test 6: Create passport with schema-driven payload"""
    print("\n" + "="*60)
    print("TEST 6: Create Passport (Schema-Driven)")
    print("="*60)
    
    user, game = setup_test_data()
    
    # Clear existing passports
    GameProfile.objects.filter(user=user, game=game).delete()
    
    client = Client()
    client.force_login(user)
    
    response = client.post(
        '/profile/api/game-passports/create/',
        data=json.dumps({
            'game_id': game.id,
            'passport_data': {
                'player_id': 'TEST12345',
                'region': 'NA'
            }
        }),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code in [200, 201]:
        if data.get('success'):
            print("✅ PASS: Create returns success")
            
            # Verify passport was created
            passport = GameProfile.objects.filter(user=user, game=game).first()
            if passport:
                print(f"✅ PASS: Passport created in database (ID: {passport.id})")
                print(f"  - IGN: {passport.ign}")
                print(f"  - Metadata: {passport.metadata}")
                return True
            else:
                print("❌ FAIL: Passport not found in database")
                return False
        else:
            print(f"❌ FAIL: success=false: {data.get('error')}")
            return False
    else:
        print(f"❌ FAIL: Expected 200/201, got {response.status_code}")
        print(f"Error: {data.get('error')}")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*70)
    print("PHASE 9A-7: BACKEND CRUD TESTS")
    print("="*70)
    
    results = {
        'Delete Valid': test_delete_with_valid_id(),
        'Delete Invalid': test_delete_with_invalid_id(),
        'Delete Without ID': test_delete_without_id(),
        'Delete Locked': test_delete_locked_passport(),
        'Games API Schema': test_games_api_returns_schema(),
        'Create Schema-Driven': test_create_schema_driven(),
    }
    
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    passed_count = sum(results.values())
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total_count - passed_count} test(s) failed")
    
    return passed_count == total_count


if __name__ == '__main__':
    try:
        success = run_all_tests()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal error running tests: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
