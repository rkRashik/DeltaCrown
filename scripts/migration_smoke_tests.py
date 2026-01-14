"""Smoke tests for critical endpoints after migration repair."""
import django
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import time

User = get_user_model()

def test_endpoints():
    client = Client()
    
    # Create unique username with timestamp
    timestamp = str(int(time.time() * 1000))[-8:]
    username = f"smoketest_{timestamp}"
    
    # Create test user
    print(f"Creating test user {username}...")
    try:
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="testpass123"
        )
        user.refresh_from_db()  # Refresh to get related objects
        print(f"[SUCCESS] User created: {user.username} (ID: {user.id})")
        
        # Ensure UserProfile exists (query directly from DB)
        from apps.user_profile.models import UserProfile
        try:
            profile = UserProfile.objects.get(user=user)
            print(f"[SUCCESS] UserProfile exists for user {user.id} (public_id: {profile.public_id})")
        except UserProfile.DoesNotExist:
            print(f"[ERROR] UserProfile missing for user {user.id}")
            return False
            return False
            
    except Exception as e:
        print(f"[ERROR] User creation failed: {e}")
        return False
    
    # Test 1: GET /me/settings/ (authenticated)
    print("\n--- TEST 1: GET /me/settings/ ---")
    try:
        client.force_login(user)
        response = client.get('/me/settings/')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("[PASS] /me/settings/ returns 200")
        else:
            print(f"[FAIL] /me/settings/ returned {response.status_code}")
            if response.status_code == 500:
                print(f"Content preview: {str(response.content[:500])}")
            return False
    except Exception as e:
        print(f"[FAIL] /me/settings/ raised exception: {e}")
        return False
    
    # Test 2: GET /@username/
    profile_test_passed = False
    print(f"\n--- TEST 2: GET /@{user.username}/ ---")
    try:
        response = client.get(f'/@{user.username}/')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print(f"[PASS] /@{user.username}/ returns 200")
            profile_test_passed = True
        else:
            print(f"[FAIL] /@{user.username}/ returned {response.status_code}")
    except Exception as e:
        print(f"[FAIL] /@{user.username}/ raised exception: {e}")
    
    # Test 3: Make user superuser and test admin (ALWAYS RUN)
    admin_test_passed = False
    print("\n--- TEST 3: GET /admin/ (superuser) ---")
    try:
        user.is_staff = True
        user.is_superuser = True
        user.save()
        
        response = client.get('/admin/')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("[PASS] /admin/ returns 200")
            admin_test_passed = True
        else:
            print(f"[FAIL] /admin/ returned {response.status_code}")
            
        # Test admin user_profile page
        if admin_test_passed:
            response = client.get('/admin/user_profile/userprofile/')
            print(f"Admin UserProfile list status: {response.status_code}")
            if response.status_code == 200:
                print("[PASS] /admin/user_profile/userprofile/ returns 200")
            else:
                print(f"[FAIL] /admin/user_profile/userprofile/ returned {response.status_code}")
                admin_test_passed = False
            
    except Exception as e:
        print(f"[FAIL] Admin tests raised exception: {e}")
    
    # Return True only if ALL tests passed
    all_passed = profile_test_passed and admin_test_passed
    
    # Cleanup
    try:
        user.delete()
        print("\n[SUCCESS] Test user cleaned up")
    except:
        pass
    
    return all_passed

if __name__ == '__main__':
    print("=" * 60)
    print("MIGRATION REPAIR SMOKE TESTS")
    print("=" * 60)
    
    success = test_endpoints()
    
    print("\n" + "=" * 60)
    if success:
        print("SMOKE TESTS: PASS")
    else:
        print("SMOKE TESTS: FAIL")
    print("=" * 60)
    
    sys.exit(0 if success else 1)
