#!/usr/bin/env python
"""
Debug admin interface issues for DeltaCrown teams app
"""
import os
import django
import requests

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

def test_admin_interface():
    print("🔍 Testing Django Admin Interface")
    print("=" * 50)
    
    # Test 1: Check URL routing
    from django.urls import reverse
    from django.test import Client
    
    try:
        admin_url = reverse('admin:teams_team_changelist')
        print(f"✅ Admin URL exists: {admin_url}")
    except Exception as e:
        print(f"❌ Admin URL error: {e}")
        return False
    
    # Test 2: Check with test client
    client = Client()
    
    try:
        # Try to access admin login first
        response = client.get('/admin/')
        print(f"✅ Admin login page status: {response.status_code}")
        
        # Try to access teams admin without auth (should redirect)
        response = client.get('/admin/teams/team/')
        print(f"✅ Teams admin page status: {response.status_code}")
        
        if response.status_code == 302:
            print("   → Redirects to login (expected behavior)")
        elif response.status_code == 200:
            print("   → Loads successfully")
        else:
            print(f"   → Unexpected status code: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test client error: {e}")
        return False
    
    # Test 3: Check model registration
    from django.contrib import admin
    from apps.teams.models import Team
    
    try:
        if Team in admin.site._registry:
            admin_class = admin.site._registry[Team]
            print(f"✅ Team model registered with: {admin_class}")
            print(f"   List display: {getattr(admin_class, 'list_display', 'Not set')}")
        else:
            print("❌ Team model not registered in admin")
            return False
    except Exception as e:
        print(f"❌ Admin registration check failed: {e}")
        return False
    
    # Test 4: Check for template issues
    try:
        from django.template.loader import get_template
        template = get_template('admin/base.html')
        print("✅ Admin base template found")
    except Exception as e:
        print(f"❌ Admin template error: {e}")
    
    # Test 5: Live server test
    try:
        response = requests.get('http://192.168.68.100:8000/admin/', timeout=5)
        print(f"✅ Live server responds: {response.status_code}")
        
        if response.status_code == 200:
            if 'Django administration' in response.text:
                print("   → Admin login page loads correctly")
            else:
                print("   → Page loads but may have content issues")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Live server not responding: {e}")
        return False
    except Exception as e:
        print(f"❌ Live server test error: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Admin interface tests completed!")
    return True

if __name__ == "__main__":
    test_admin_interface()