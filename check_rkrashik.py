#!/usr/bin/env python
"""Check if rkrashik user exists and list real users"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User

print("Checking for @rkrashik...")
exists = User.objects.filter(username='rkrashik').exists()
print(f"User.objects.filter(username='rkrashik').exists() = {exists}")

if not exists:
    print("\n@rkrashik DOES NOT EXIST")
    print("\nTop 10 real usernames in database:")
    users = User.objects.all()[:10]
    for idx, user in enumerate(users, 1):
        print(f"  {idx}. @{user.username}")
else:
    print("\n✓ @rkrashik EXISTS")
    user = User.objects.get(username='rkrashik')
    print(f"  ID: {user.id}")
    print(f"  Email: {user.email}")
