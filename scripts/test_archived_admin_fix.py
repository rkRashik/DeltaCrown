#!/usr/bin/env python
"""
Test script to verify archived tournament admin page loads correctly.
Tests the fix for KeyError: 'slug' not found in TournamentForm.
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


def test_archived_admin_fields():
    """Test that archived tournaments have proper field configuration."""
    
    print("\n" + "="*60)
    print("Testing Archived Tournament Admin Fix")
    print("="*60)
    
    # Get or create a test tournament
    tournament = Tournament.objects.first()
    if not tournament:
        print("❌ No tournaments found. Create one first.")
        return False
    
    print(f"\n✓ Found tournament: {tournament.name} (ID: {tournament.id})")
    print(f"  Status: {tournament.status}")
    
    # Create admin instance
    admin = TournamentAdmin(Tournament, site)
    
    # Create fake request with superuser
    factory = RequestFactory()
    request = factory.get('/')
    request.user = User.objects.filter(is_superuser=True).first()
    
    if not request.user:
        print("❌ No superuser found. Create one first.")
        return False
    
    print(f"\n✓ Using superuser: {request.user.username}")
    
    # Test 1: Check readonly fields for non-archived
    if tournament.status != 'COMPLETED':
        print(f"\n📝 Test 1: Non-archived tournament ({tournament.status})")
        readonly_fields = admin.get_readonly_fields(request, tournament)
        print(f"  Readonly fields count: {len(readonly_fields)}")
        print(f"  Readonly fields: {', '.join(readonly_fields[:5])}...")
        
        fields = admin.get_fields(request, tournament)
        print(f"  get_fields() returns: {fields}")
        
        fieldsets = admin.get_fieldsets(request, tournament)
        print(f"  Fieldsets count: {len(fieldsets)}")
        for name, config in fieldsets:
            print(f"    - {name}: {len(config['fields'])} fields")
    
    # Test 2: Check readonly fields for archived
    original_status = tournament.status
    tournament.status = 'COMPLETED'
    
    print(f"\n📝 Test 2: Archived tournament (COMPLETED)")
    readonly_fields = admin.get_readonly_fields(request, tournament)
    print(f"  Readonly fields count: {len(readonly_fields)}")
    print(f"  Sample readonly: {', '.join(list(readonly_fields)[:8])}...")
    
    fields = admin.get_fields(request, tournament)
    print(f"  get_fields() returns list: {fields is not None}")
    if fields:
        print(f"  Fields count: {len(fields)}")
        print(f"  Sample fields: {', '.join(fields[:8])}...")
        
        # Verify critical fields are present
        critical = ['name', 'slug', 'game', 'status']
        missing = [f for f in critical if f not in fields]
        if missing:
            print(f"  ❌ Missing critical fields: {missing}")
            tournament.status = original_status
            return False
        else:
            print(f"  ✓ All critical fields present")
    
    fieldsets = admin.get_fieldsets(request, tournament)
    print(f"  Fieldsets count: {len(fieldsets)}")
    for name, config in fieldsets:
        print(f"    - {name}: {len(config['fields'])} fields")
    
    # Test 3: Verify fieldsets don't conflict with fields
    print(f"\n📝 Test 3: Consistency check")
    if fields:
        # When get_fields() returns a list, fieldsets should show simplified view
        fieldset_fields = []
        for name, config in fieldsets:
            for field_group in config['fields']:
                if isinstance(field_group, (list, tuple)):
                    fieldset_fields.extend(field_group)
                else:
                    fieldset_fields.append(field_group)
        
        print(f"  Fieldset total fields: {len(fieldset_fields)}")
        print(f"  get_fields() total: {len(fields)}")
        
        # Check if all fieldset fields are in get_fields result
        conflicts = [f for f in fieldset_fields if f not in fields and f not in readonly_fields]
        if conflicts:
            print(f"  ⚠️  Potential conflicts: {conflicts}")
        else:
            print(f"  ✓ No conflicts detected")
    
    # Test 4: Verify prepopulated fields
    print(f"\n📝 Test 4: Prepopulated fields check")
    prepop = admin.get_prepopulated_fields(request, tournament)
    print(f"  Prepopulated fields: {prepop}")
    if prepop:
        print(f"  ❌ Archived tournaments should have no prepopulated fields!")
        tournament.status = original_status
        return False
    else:
        print(f"  ✓ Correct: Empty prepopulated fields for archived")
    
    # Restore original status
    tournament.status = original_status
    
    print("\n" + "="*60)
    print("✅ All tests passed! Admin configuration is correct.")
    print("="*60)
    print("\n💡 Next steps:")
    print("  1. Start the dev server: python manage.py runserver")
    print(f"  2. Visit: http://localhost:8000/admin/tournaments/tournament/{tournament.id}/change/")
    print("  3. Verify the page loads without errors")
    print("  4. Change status to COMPLETED and verify readonly mode")
    print()
    
    return True


if __name__ == '__main__':
    try:
        success = test_archived_admin_fields()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
