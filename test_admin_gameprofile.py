"""Test GameProfile admin to reproduce old_ign error"""
import django
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from apps.user_profile.models import GameProfile

User = get_user_model()

# Create test client
client = Client()

# Get or create superuser
try:
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No superuser found. Create one with: python manage.py createsuperuser")
        sys.exit(1)
    
    print(f"✅ Using superuser: {admin_user.username}")
    
    # Login
    client.force_login(admin_user)
    
    # Test 1: GameProfile changelist
    print("\n1️⃣ Testing GameProfile changelist...")
    url = reverse('admin:user_profile_gameprofile_changelist')
    print(f"URL: {url}")
    response = client.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Changelist loads OK")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.content.decode()[:500])
    
    # Test 2: GameProfile add form
    print("\n2️⃣ Testing GameProfile add form...")
    url = reverse('admin:user_profile_gameprofile_add')
    print(f"URL: {url}")
    response = client.get(url)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Add form loads OK")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.content.decode()[:500])
    
    # Test 3: GameProfile change form (if passports exist)
    print("\n3️⃣ Testing GameProfile change form...")
    passport = GameProfile.objects.first()
    if passport:
        url = reverse('admin:user_profile_gameprofile_change', args=[passport.pk])
        print(f"URL: {url}")
        print(f"Testing with passport ID={passport.pk} for {passport.user.username} / {passport.game}")
        response = client.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Change form loads OK")
            # Check if aliases are shown
            if passport.aliases.exists():
                print(f"   Passport has {passport.aliases.count()} aliases")
        else:
            print(f"❌ ERROR: {response.status_code}")
            if response.status_code == 500:
                print("\n🔴 ERROR DETAILS:")
                print(response.content.decode()[:1000])
    else:
        print("⚠️ No GameProfile objects exist - skipping change form test")
    
    print("\n" + "="*60)
    print("Admin tests complete!")
    
except Exception as e:
    print(f"❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
