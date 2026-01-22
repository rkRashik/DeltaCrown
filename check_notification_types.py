#!/usr/bin/env python
"""Quick script to check if notification types exist."""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.notifications.models import Notification

print("=" * 60)
print("NOTIFICATION TYPES CHECK")
print("=" * 60)

# Check if USER_FOLLOWED exists
if hasattr(Notification.Type, 'USER_FOLLOWED'):
    print("✅ USER_FOLLOWED exists")
    print(f"   Value: {Notification.Type.USER_FOLLOWED}")
else:
    print("❌ USER_FOLLOWED does NOT exist")

# List all available types
print("\n📋 All available notification types:")
print("-" * 60)
for choice in Notification.Type.choices:
    print(f"  {choice[0]:<30} → {choice[1]}")

print("\n" + "=" * 60)
