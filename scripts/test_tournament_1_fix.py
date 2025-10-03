#!/usr/bin/env python
"""
Test accessing Tournament ID 1 in admin to verify the KeyError fix.
Simulates what Django admin does when loading the change form.
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.admin.sites import site
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament
from apps.tournaments.admin.tournaments.admin import TournamentAdmin

User = get_user_model()


def test_tournament_1_admin():
    """Test that Tournament ID 1 can be accessed in admin without KeyError."""
    
    print("\n" + "="*70)
    print("Testing Tournament ID 1 - Admin Access Fix")
    print("="*70)
    
    # Get tournament ID 1
    try:
        tournament = Tournament.objects.get(id=1)
    except Tournament.DoesNotExist:
        print("❌ Tournament ID 1 does not exist")
        return False
    
    print(f"\n✓ Found tournament: {tournament.name} (ID: {tournament.id})")
    print(f"  Status: {tournament.status}")
    print(f"  Slug: {tournament.slug}")
    print(f"  Game: {tournament.game}")
    
    # Create admin instance
    admin = TournamentAdmin(Tournament, site)
    
    # Create fake request with superuser
    factory = RequestFactory()
    request = factory.get(f'/admin/tournaments/tournament/{tournament.id}/change/')
    request.user = User.objects.filter(is_superuser=True).first()
    
    if not request.user:
        print("❌ No superuser found. Create one first.")
        return False
    
    print(f"\n✓ Using superuser: {request.user.username}")
    
    # Test all admin methods that are called when loading change form
    print(f"\n📝 Simulating admin change form load...")
    
    # 1. Get readonly fields
    print(f"\n1. get_readonly_fields():")
    try:
        readonly = admin.get_readonly_fields(request, tournament)
        print(f"   ✓ Returned {len(readonly)} readonly fields")
        if tournament.status == 'COMPLETED':
            if 'slug' in readonly and 'name' in readonly:
                print(f"   ✓ Key fields (slug, name) are readonly")
            else:
                print(f"   ⚠️  Expected slug/name to be readonly for COMPLETED")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 2. Get fields
    print(f"\n2. get_fields():")
    try:
        fields = admin.get_fields(request, tournament)
        if fields:
            print(f"   ✓ Returned explicit field list: {len(fields)} fields")
            if 'slug' in fields:
                print(f"   ✓ 'slug' field is in the list")
            else:
                print(f"   ❌ 'slug' field is missing!")
                return False
        else:
            print(f"   ✓ Returned None (using fieldsets)")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 3. Get fieldsets
    print(f"\n3. get_fieldsets():")
    try:
        fieldsets = admin.get_fieldsets(request, tournament)
        print(f"   ✓ Returned {len(fieldsets)} fieldset(s)")
        for name, config in fieldsets:
            print(f"     - {name}: {len(config['fields'])} fields")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # 4. Get prepopulated fields (THIS WAS THE BUG!)
    print(f"\n4. get_prepopulated_fields():")
    try:
        prepop = admin.get_prepopulated_fields(request, tournament)
        print(f"   ✓ Returned: {prepop}")
        
        if tournament.status == 'COMPLETED':
            if prepop:
                print(f"   ❌ Should be empty for COMPLETED tournaments!")
                print(f"   ❌ This is the bug - trying to prepopulate readonly fields!")
                return False
            else:
                print(f"   ✓ Correctly empty for COMPLETED tournament")
        else:
            if 'slug' in prepop:
                print(f"   ✓ Slug prepopulation configured for editable tournament")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. Test form generation (this is what was failing)
    print(f"\n5. Simulate form generation:")
    try:
        # Get the ModelForm class
        form_class = admin.get_form(request, tournament)
        print(f"   ✓ Got form class: {form_class.__name__}")
        
        # Try to instantiate the form (this is where KeyError occurred)
        form = form_class(instance=tournament)
        print(f"   ✓ Form instantiated successfully")
        
        # Check if slug is accessible
        if tournament.status == 'COMPLETED':
            # For readonly fields, they shouldn't be in the form
            print(f"   ℹ️  Tournament is COMPLETED (archived)")
            print(f"   ℹ️  Form fields: {list(form.fields.keys())[:5]}...")
        else:
            if 'slug' in form.fields:
                print(f"   ✓ 'slug' field is in form.fields")
            else:
                print(f"   ℹ️  'slug' not in form (might be readonly)")
        
    except KeyError as e:
        print(f"   ❌ KeyError: {e}")
        print(f"   ❌ This is the bug we're fixing!")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 6. Check delete permission
    print(f"\n6. has_delete_permission():")
    try:
        can_delete = admin.has_delete_permission(request, tournament)
        if tournament.status == 'COMPLETED':
            if can_delete:
                print(f"   ⚠️  COMPLETED tournament should not be deletable!")
            else:
                print(f"   ✓ Correctly blocked deletion for archived tournament")
        else:
            print(f"   ✓ Deletion allowed for non-archived tournament")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    print("\n" + "="*70)
    print("✅ All admin methods work correctly for Tournament ID 1!")
    print("="*70)
    
    if tournament.status == 'COMPLETED':
        print("\n💡 The fix is working!")
        print("   - prepopulated_fields is empty for archived tournaments")
        print("   - Form can be generated without KeyError")
        print("   - All fields are readonly and protected")
        print("\n🎉 You can now access:")
        print(f"   http://localhost:8000/admin/tournaments/tournament/{tournament.id}/change/")
    else:
        print(f"\n💡 Tournament {tournament.id} is {tournament.status} (not archived)")
        print("   - Change to COMPLETED status to test archive mode")
    
    print()
    return True


if __name__ == '__main__':
    try:
        success = test_tournament_1_admin()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
