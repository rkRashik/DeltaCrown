#!/usr/bin/env python
"""Quick script to verify migration 0030 was successful."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
django.setup()

from apps.user_profile.models import NotificationPreferences, WalletSettings, UserProfile

print("\n✅ MIGRATION 0030 VERIFICATION")
print("=" * 50)

# Check models can be imported
print("\n1. Model Imports:")
print("   ✅ NotificationPreferences")
print("   ✅ WalletSettings")
print("   ✅ UserProfile")

# Check new fields exist on UserProfile
print("\n2. UserProfile New Fields:")
new_fields = ['preferred_language', 'timezone_pref', 'time_format', 'theme_preference']
for field_name in new_fields:
    try:
        field = UserProfile._meta.get_field(field_name)
        print(f"   ✅ {field_name} ({field.get_internal_type()})")
    except Exception as e:
        print(f"   ❌ {field_name}: {e}")

# Check NotificationPreferences fields
print("\n3. NotificationPreferences Fields:")
notif_fields = [
    'email_tournament_reminders', 'email_match_results', 'email_team_invites',
    'email_achievements', 'email_platform_updates', 'notify_tournament_start',
    'notify_team_messages', 'notify_follows', 'notify_achievements'
]
for field_name in notif_fields:
    try:
        field = NotificationPreferences._meta.get_field(field_name)
        print(f"   ✅ {field_name}")
    except Exception as e:
        print(f"   ❌ {field_name}: {e}")

# Check WalletSettings fields
print("\n4. WalletSettings Fields:")
wallet_fields = [
    'bkash_enabled', 'bkash_account', 'nagad_enabled', 'nagad_account',
    'rocket_enabled', 'rocket_account', 'auto_withdrawal_threshold', 'auto_convert_to_usd'
]
for field_name in wallet_fields:
    try:
        field = WalletSettings._meta.get_field(field_name)
        print(f"   ✅ {field_name}")
    except Exception as e:
        print(f"   ❌ {field_name}: {e}")

# Check relationships
print("\n5. Model Relationships:")
try:
    # Check reverse relation from UserProfile to NotificationPreferences
    UserProfile.notification_prefs
    print("   ✅ UserProfile.notification_prefs (OneToOne → NotificationPreferences)")
except AttributeError as e:
    print(f"   ❌ UserProfile.notification_prefs: {e}")

try:
    # Check reverse relation from UserProfile to WalletSettings
    UserProfile.wallet_settings
    print("   ✅ UserProfile.wallet_settings (OneToOne → WalletSettings)")
except AttributeError as e:
    print(f"   ❌ UserProfile.wallet_settings: {e}")

print("\n" + "=" * 50)
print("✅ VERIFICATION COMPLETE\n")
