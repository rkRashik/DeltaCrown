"""Detailed smoke test with full error output."""
import django
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile

User = get_user_model()

# Create unique username
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
    print(f"[SUCCESS] User created: {user.username} (ID: {user.id})")
    
    # Check UserProfile
    profile = UserProfile.objects.get(user=user)
    print(f"[SUCCESS] UserProfile exists (public_id: {profile.public_id})")
    
    # Try GET /me/settings/ with client
    print("\n--- TEST: GET /me/settings/ ---")
    client = Client()
    client.force_login(user)
    response = client.get('/me/settings/')
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print(f"[FAIL] Response status: {response.status_code}")
        print(f"Content type: {response.get('Content-Type', 'unknown')}")
        if response.status_code == 500:
            print("\n[ERROR CONTENT]:")
            print(response.content.decode('utf-8')[:2000])
    else:
        print("[PASS] /me/settings/ returns 200")
    
    # Cleanup
    user.delete()
    print("\n[SUCCESS] Test user cleaned up")
    
except Exception as e:
    import traceback
    print(f"\n[ERROR] Test failed:")
    print(traceback.format_exc())
