"""
Test Email Verification System
Tests both primary and custom email flows
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.cache import cache
from apps.user_profile.views.email_verification_api import generate_otp

User = get_user_model()

print("=" * 70)
print("📧 EMAIL VERIFICATION SYSTEM TEST")
print("=" * 70)

# Test 1: OTP Generation
print("\n✅ Test 1: OTP Generation")
otp = generate_otp()
print(f"   Generated OTP: {otp}")
assert len(otp) == 6, "OTP should be 6 digits"
assert otp.isdigit(), "OTP should only contain digits"
print("   ✓ OTP format correct")

# Test 2: Cache Connection
print("\n✅ Test 2: Cache Connection")
try:
    test_key = "test_email_verification"
    cache.set(test_key, "test_value", timeout=10)
    cached_value = cache.get(test_key)
    assert cached_value == "test_value", "Cache read/write failed"
    cache.delete(test_key)
    print("   ✓ Cache is working correctly")
except Exception as e:
    print(f"   ✗ Cache error: {e}")
    print("   Make sure Redis/Memcached is running!")

# Test 3: User Profile Check
print("\n✅ Test 3: User Profile Model")
try:
    user = User.objects.first()
    if user:
        profile = user.userprofile
        print(f"   User: {user.username}")
        print(f"   Primary Email: {user.email}")
        print(f"   Secondary Email: {profile.secondary_email or 'Not set'}")
        print(f"   Verified: {profile.secondary_email_verified}")
        print("   ✓ User profile accessible")
    else:
        print("   ⚠️  No users found. Create a test user first.")
except Exception as e:
    print(f"   ✗ Error: {e}")

# Test 4: Email Backend
print("\n✅ Test 4: Email Backend Configuration")
from django.conf import settings
print(f"   Backend: {settings.EMAIL_BACKEND}")
if 'console' in settings.EMAIL_BACKEND:
    print("   ✓ Console backend active (emails will print to console)")
elif 'smtp' in settings.EMAIL_BACKEND:
    print("   ✓ SMTP backend active")
    print(f"   Host: {settings.EMAIL_HOST}")
    print(f"   Port: {settings.EMAIL_PORT}")
else:
    print(f"   ⚠️  Unknown backend: {settings.EMAIL_BACKEND}")

# Test 5: URL Routes
print("\n✅ Test 5: URL Routes")
from django.urls import reverse
try:
    url1 = reverse('user_profile:send_verification_otp')
    url2 = reverse('user_profile:verify_otp_code')
    print(f"   Send OTP: {url1}")
    print(f"   Verify OTP: {url2}")
    print("   ✓ URLs configured correctly")
except Exception as e:
    print(f"   ✗ URL error: {e}")

# Test 6: Model Fields
print("\n✅ Test 6: Model Fields Check")
try:
    from apps.user_profile.models_main import UserProfile
    field_names = [f.name for f in UserProfile._meta.fields]
    
    required_fields = ['secondary_email', 'secondary_email_verified']
    missing = [f for f in required_fields if f not in field_names]
    
    if not missing:
        print("   ✓ All required fields present")
        print("   - secondary_email")
        print("   - secondary_email_verified")
    else:
        print(f"   ✗ Missing fields: {missing}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print("\n" + "=" * 70)
print("📊 TEST SUMMARY")
print("=" * 70)
print("""
READY TO TEST:
1. Navigate to: http://127.0.0.1:8000/me/settings/
2. Click "Connections" tab
3. Test PRIMARY EMAIL:
   - Click "Use Primary Email" button
   - Click "Verify Email Now"
   - Should verify immediately (no OTP needed)
   
4. Test CUSTOM EMAIL:
   - Click "Custom Email" button
   - Enter a custom email address
   - Click "Verify Email Now"
   - Check console for OTP code
   - Enter the 6-digit code
   - Should verify successfully

ENDPOINTS:
- POST /me/settings/send-verification-otp/
- POST /me/settings/verify-otp-code/

NOTE: Check terminal for email output if using console backend.
""")
print("=" * 70)
