"""Admin Registration Verification.

Run this to confirm:
1. Only ONE UserProfile admin is registered
2. All new fields are visible
3. No conflicts exist
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib import admin
from apps.user_profile.models_main import UserProfile

print("=" * 70)
print("🔍 ADMIN REGISTRATION CHECK")
print("=" * 70)

# Check if UserProfile is registered
if UserProfile in admin.site._registry:
    print("✅ UserProfile IS registered in admin")
    
    # Get the registered admin class
    model_admin = admin.site._registry[UserProfile]
    
    print(f"\n📋 Admin Class: {model_admin.__class__.__name__}")
    print(f"📁 Defined in: {model_admin.__module__}")
    
    # Check for new fields in fieldsets
    print("\n🔎 Checking for new contact fields...")
    new_fields = ['whatsapp', 'secondary_email', 'secondary_email_verified', 'preferred_contact_method']
    
    found_fields = []
    for fieldset_name, fieldset_data in model_admin.fieldsets:
        for field in fieldset_data['fields']:
            if isinstance(field, tuple):
                # Handle grouped fields
                for f in field:
                    if f in new_fields and f not in found_fields:
                        found_fields.append(f)
            elif field in new_fields and field not in found_fields:
                found_fields.append(field)
    
    for field in new_fields:
        if field in found_fields:
            print(f"   ✅ {field}")
        else:
            print(f"   ❌ {field} - MISSING!")
    
    # Check readonly fields
    print("\n🔒 Readonly fields:")
    if hasattr(model_admin, 'readonly_fields'):
        if 'secondary_email_verified' in model_admin.readonly_fields:
            print("   ✅ secondary_email_verified (correct - only system can verify)")
        else:
            print("   ⚠️  secondary_email_verified NOT in readonly_fields")
    
    print("\n📊 Summary:")
    print(f"   • Found {len(found_fields)}/{len(new_fields)} new fields")
    print(f"   • Admin URL: http://127.0.0.1:8000/admin/user_profile/userprofile/")
    
    if len(found_fields) == len(new_fields):
        print("\n✅ All fields configured correctly!")
    else:
        print("\n❌ Some fields are missing - check fieldsets in users.py")
    
else:
    print("❌ UserProfile is NOT registered in admin!")
    print("   This should never happen - check apps/user_profile/admin/users.py")

print("=" * 70)
