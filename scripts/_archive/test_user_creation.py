"""Test user creation to identify required missing tables."""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()

def test_user_creation():
    print("Testing user creation...")
    
    try:
        with transaction.atomic():
            # Try to create a test user
            user = User.objects.create_user(
                username=f"test_migration_check",
                email="test_migration@example.com",
                password="testpass123"
            )
            print(f"[SUCCESS] User created: {user.username}")
            print(f"           User ID: {user.id}")
            
            # Check if UserProfile was auto-created
            if hasattr(user, 'userprofile'):
                profile = user.userprofile
                print(f"[SUCCESS] UserProfile auto-created")
                print(f"           Profile ID: {profile.id}")
                print(f"           Public ID: {profile.public_id}")
            else:
                print(f"[WARNING] UserProfile not auto-created")
            
            # Rollback the transaction (don't actually save test user)
            transaction.set_rollback(True)
            print("\n[INFO] Test transaction rolled back (no data saved)")
            
            return True
            
    except Exception as e:
        print(f"[ERROR] User creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_user_creation()
    sys.exit(0 if success else 1)
