"""
Phase 4A: Direct runtime verification without test framework
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models_main import UserProfile, GameProfile, PrivacySettings
from apps.games.models import Game

User = get_user_model()

print("\n" + "="*70)
print("PHASE 4A: RUNTIME VERIFICATION")
print("="*70 + "\n")

# ==============================================================================
# TEST 1: Profile Data Sync (Settings → Profile Page)
# ==============================================================================

print("[TEST 1] Profile Data Sync")
print("-" * 70)

client = Client()

# Create test user
user = User.objects.create_user(
    username='testuser',
    email='test@example.com',
    password='testpass123'
)
profile = user.profile

print(f"✅ Created user: {user.username}")
print(f"✅ Profile exists: {profile.id}")

# Login
logged_in = client.login(username='testuser', password='testpass123')
print(f"✅ Logged in: {logged_in}")

# Test 1.1: Display Name Sync
print("\n[1.1] Display Name Update")
response = client.post('/me/settings/basic/', {
    'display_name': 'New Display Name',
    'bio': 'Test bio',
})
print(f"  POST /me/settings/basic/ → Status {response.status_code}")

if response.status_code == 200:
    profile.refresh_from_db()
    print(f"  DB display_name: {profile.display_name}")
    
    if profile.display_name == 'New Display Name':
        print("  ✅ DB updated correctly")
    else:
        print(f"  ❌ DB not updated (expected 'New Display Name', got '{profile.display_name}')")
    
    # Check if appears on profile page
    profile_response = client.get(f'/@{user.username}/')
    if profile_response.status_code == 200:
        if 'New Display Name' in profile_response.content.decode():
            print("  ✅ Appears on profile page")
        else:
            print("  ❌ NOT visible on profile page")
    else:
        print(f"  ❌ Profile page error: {profile_response.status_code}")
else:
    print(f"  ❌ Settings save failed: {response.status_code}")
    if response.status_code in [400, 403, 404, 500]:
        print(f"  Response: {response.content[:500]}")

# Test 1.2: Bio Sync
print("\n[1.2] Bio Update")
response = client.post('/me/settings/basic/', {
    'display_name': profile.display_name or user.username,
    'bio': 'This is my new bio from Phase 4A test',
})
print(f"  POST /me/settings/basic/ → Status {response.status_code}")

if response.status_code == 200:
    profile.refresh_from_db()
    if profile.bio == 'This is my new bio from Phase 4A test':
        print("  ✅ Bio saved to DB")
        
        profile_response = client.get(f'/@{user.username}/')
        if 'This is my new bio from Phase 4A test' in profile_response.content.decode():
            print("  ✅ Bio visible on profile page")
        else:
            print("  ❌ Bio NOT visible on profile page")
    else:
        print(f"  ❌ Bio not saved (got: {profile.bio})")
else:
    print(f"  ❌ Bio save failed: {response.status_code}")

# ==============================================================================
# TEST 2: Game Passport System
# ==============================================================================

print("\n" + "="*70)
print("[TEST 2] Game Passport System")
print("-" * 70)

# Check if games exist
games = Game.objects.all()[:5]
print(f"✅ Found {Game.objects.count()} games in DB")

if games:
    test_game = games[0]
    print(f"✅ Using test game: {test_game.name} (ID: {test_game.id})")
    
    # Test 2.1: API returns games
    print("\n[2.1] Games API")
    response = client.get('/api/games/')
    print(f"  GET /api/games/ → Status {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  ✅ Returned {len(data)} games")
    else:
        print(f"  ❌ Games API failed")
    
    # Test 2.2: Passport Creation
    print("\n[2.2] Passport Creation")
    response = client.post('/api/passports/create/', {
        'game_id': test_game.id,
        'ign': 'TestPlayer4A',
        'discriminator': '#1234',
        'platform': 'PC',
    }, content_type='application/json')
    
    print(f"  POST /api/passports/create/ → Status {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"  Response: {data}")
        
        # Check DB
        passport = GameProfile.objects.filter(
            user_profile=profile,
            game=test_game
        ).first()
        
        if passport:
            print(f"  ✅ Passport created in DB (ID: {passport.id})")
            print(f"  IGN: {passport.ign}")
            
            # Check profile page
            profile_response = client.get(f'/@{user.username}/')
            if 'TestPlayer4A' in profile_response.content.decode():
                print("  ✅ Passport visible on profile page")
            else:
                print("  ❌ Passport NOT visible on profile page")
        else:
            print("  ❌ Passport NOT created in DB")
    else:
        print(f"  ❌ Passport creation failed: {response.status_code}")
        print(f"  Response: {response.content[:500]}")
    
    # Test 2.3: Toggle LFT
    print("\n[2.3] Toggle LFT")
    passport = GameProfile.objects.filter(user_profile=profile).first()
    
    if passport:
        initial_lft = passport.is_looking_for_team
        response = client.post('/api/passports/toggle-lft/', {
            'passport_id': passport.id,
        }, content_type='application/json')
        
        print(f"  POST /api/passports/toggle-lft/ → Status {response.status_code}")
        
        if response.status_code == 200:
            passport.refresh_from_db()
            if passport.is_looking_for_team != initial_lft:
                print(f"  ✅ LFT toggled (was {initial_lft}, now {passport.is_looking_for_team})")
            else:
                print(f"  ❌ LFT NOT toggled (still {initial_lft})")
        else:
            print(f"  ❌ Toggle LFT failed: {response.status_code}")
    else:
        print("  ⚠️  No passport to test LFT toggle")

else:
    print("❌ No games in database - cannot test passport system")

# ==============================================================================
# TEST 3: Follow System
# ==============================================================================

print("\n" + "="*70)
print("[TEST 3] Follow System")
print("-" * 70)

# Create second user
user2 = User.objects.create_user(
    username='targetuser',
    email='target@example.com',
    password='testpass123'
)
profile2 = user2.profile

print(f"✅ Created target user: {user2.username}")

# Test follow
print("\n[3.1] Follow Action")
response = client.post(f'/actions/follow/{user2.username}/')
print(f"  POST /actions/follow/{user2.username}/ → Status {response.status_code}")

if response.status_code == 200:
    from apps.user_profile.models_main import Follow
    follow_exists = Follow.objects.filter(
        follower=profile,
        following=profile2
    ).exists()
    
    if follow_exists:
        print("  ✅ Follow record created")
        
        profile.refresh_from_db()
        profile2.refresh_from_db()
        
        print(f"  User1 following_count: {profile.following_count}")
        print(f"  User2 follower_count: {profile2.follower_count}")
        
        if profile.following_count > 0 and profile2.follower_count > 0:
            print("  ✅ Counts updated correctly")
        else:
            print("  ❌ Counts NOT updated")
    else:
        print("  ❌ Follow record NOT created")
else:
    print(f"  ❌ Follow failed: {response.status_code}")

# Test unfollow
print("\n[3.2] Unfollow Action")
response = client.post(f'/actions/unfollow/{user2.username}/')
print(f"  POST /actions/unfollow/{user2.username}/ → Status {response.status_code}")

if response.status_code == 200:
    from apps.user_profile.models_main import Follow
    follow_exists = Follow.objects.filter(
        follower=profile,
        following=profile2
    ).exists()
    
    if not follow_exists:
        print("  ✅ Follow record removed")
    else:
        print("  ❌ Follow record still exists")
else:
    print(f"  ❌ Unfollow failed: {response.status_code}")

# ==============================================================================
# TEST 4: Privacy Settings
# ==============================================================================

print("\n" + "="*70)
print("[TEST 4] Privacy System")
print("-" * 70)

# Check if PrivacySettings exists
privacy_settings = PrivacySettings.objects.filter(user_profile=profile).first()

if privacy_settings:
    print(f"✅ PrivacySettings exists for user")
    print(f"  profile_visibility: {privacy_settings.profile_visibility}")
else:
    print("❌ PrivacySettings NOT found (should be auto-created)")

# Check for duplicate privacy fields
has_profile_visibility = hasattr(profile, 'profile_visibility')
print(f"\nUserProfile.profile_visibility field exists: {has_profile_visibility}")
print(f"PrivacySettings model used: {privacy_settings is not None}")

if has_profile_visibility and privacy_settings:
    print("⚠️  WARNING: Dual privacy system detected (both field and model exist)")
elif not has_profile_visibility and privacy_settings:
    print("✅ Clean privacy system (PrivacySettings model only)")
elif has_profile_visibility and not privacy_settings:
    print("✅ Clean privacy system (UserProfile field only)")
else:
    print("❌ NO privacy system found")

# Test privacy save
print("\n[4.1] Privacy Settings Save")
response = client.post('/me/settings/privacy/save/', {
    'profile_visibility': 'FOLLOWERS_ONLY',
    'show_game_passports': 'on',
    'show_achievements': 'on',
})
print(f"  POST /me/settings/privacy/save/ → Status {response.status_code}")

if response.status_code == 200:
    if privacy_settings:
        privacy_settings.refresh_from_db()
        if privacy_settings.profile_visibility == 'FOLLOWERS_ONLY':
            print("  ✅ Privacy settings saved")
        else:
            print(f"  ❌ Privacy NOT saved (got: {privacy_settings.profile_visibility})")
    else:
        print("  ⚠️  Cannot verify save (no PrivacySettings model)")
else:
    print(f"  ❌ Privacy save failed: {response.status_code}")

# ==============================================================================
# SUMMARY
# ==============================================================================

print("\n" + "="*70)
print("PHASE 4A RUNTIME VERIFICATION COMPLETE")
print("="*70)
print("\nNext: Review failures and fix broken endpoints immediately")
