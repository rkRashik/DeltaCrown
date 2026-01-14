#!/usr/bin/env python
"""
UP.2 FIX PASS - Verify Canonical Fields
Check actual values from Admin/DB for user rkrashik
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile, GameProfile, PrivacySettings

User = get_user_model()

def verify_user_canonical_fields(username='rkrashik'):
    """Check canonical field values for a user"""
    try:
        user = User.objects.get(username=username)
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            profile = UserProfile.objects.get(user=user)
        
        privacy, _ = PrivacySettings.objects.get_or_create(user_profile=profile)
        
        print(f"\n{'='*60}")
        print(f"CANONICAL FIELD VERIFICATION: @{username}")
        print(f"{'='*60}\n")
        
        print(f"🔍 LEVEL (UserProfile.level):")
        print(f"   Value: {profile.level}")
        print(f"   Expected in template: {{ user_profile.level }}\n")
        
        print(f"🔍 KYC STATUS (UserProfile.kyc_status):")
        print(f"   Value: '{profile.kyc_status}'")
        print(f"   Choices: {dict(UserProfile._meta.get_field('kyc_status').choices)}")
        print(f"   Is Verified: {profile.kyc_status == 'verified'}")
        print(f"   Template check: {{% if user_profile.kyc_status == 'verified' %}}\n")
        
        print(f"🔍 GAME PASSPORTS (GameProfile):")
        passports = GameProfile.objects.filter(user=user)
        print(f"   Total: {passports.count()}")
        for idx, gp in enumerate(passports, 1):
            print(f"   {idx}. {gp.game}: {gp.in_game_name}", end="")
            if gp.discriminator:
                print(f"#{gp.discriminator}", end="")
            print(f" (Pinned: {gp.is_pinned})")
        print()
        
        print(f"🔍 PRIVACY SETTINGS:")
        print(f"   show_social_links: {privacy.show_social_links}")
        print(f"   show_game_ids: {privacy.show_game_ids}")
        print(f"   Template: Owner always sees, visitors respect these flags\n")
        
        print(f"✅ VERIFICATION COMPLETE")
        print(f"{'='*60}\n")
        
        return {
            'level': profile.level,
            'kyc_status': profile.kyc_status,
            'passport_count': passports.count(),
            'privacy_social': privacy.show_social_links,
            'privacy_games': privacy.show_game_ids,
        }
        
    except User.DoesNotExist:
        print(f"❌ User @{username} not found")
        return None
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    result = verify_user_canonical_fields('rkrashik')
    if result:
        print("\n📊 QUICK REFERENCE:")
        print(f"   LVL: {result['level']}")
        print(f"   KYC: {result['kyc_status']}")
        print(f"   Passports: {result['passport_count']}")
