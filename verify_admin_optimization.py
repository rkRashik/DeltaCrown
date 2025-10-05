#!/usr/bin/env python
"""
Verification script for Tournament Admin Optimization.
Checks that all admin components are properly configured.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib import admin
from apps.tournaments.models import Tournament
from apps.tournaments.admin.tournaments.admin import TournamentAdmin


def verify_admin_optimization():
    """Verify that admin optimization is working correctly."""
    
    print("=" * 60)
    print("🔍 TOURNAMENT ADMIN OPTIMIZATION VERIFICATION")
    print("=" * 60)
    print()
    
    # Check if TournamentAdmin is registered
    print("✓ Checking admin registration...")
    try:
        admin_instance = admin.site._registry[Tournament]
        assert isinstance(admin_instance, TournamentAdmin)
        print("  ✅ TournamentAdmin properly registered")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Check fieldsets structure
    print("\n✓ Checking fieldsets...")
    try:
        fieldsets = admin_instance.get_fieldsets(None, None)
        fieldset_names = [fs[0] for fs in fieldsets]
        print(f"  ✅ Found {len(fieldsets)} fieldsets:")
        for name in fieldset_names:
            print(f"     - {name}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Check list display
    print("\n✓ Checking list display...")
    try:
        list_display = admin_instance.get_list_display(None)
        print(f"  ✅ List display has {len(list_display)} columns:")
        for col in list_display:
            print(f"     - {col}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Check inlines
    print("\n✓ Checking inline configurations...")
    try:
        inlines = admin_instance.get_inline_instances(None, None)
        print(f"  ✅ Found {len(inlines)} inline configurations:")
        for inline in inlines:
            print(f"     - {inline.__class__.__name__}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Check readonly fields
    print("\n✓ Checking readonly fields...")
    try:
        readonly = admin_instance.get_readonly_fields(None, None)
        print(f"  ✅ Found {len(readonly)} readonly fields:")
        for field in readonly:
            print(f"     - {field}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Check actions
    print("\n✓ Checking admin actions...")
    try:
        actions = admin_instance.actions
        print(f"  ✅ Found {len(actions)} actions:")
        for action in actions[:5]:  # Show first 5
            print(f"     - {action}")
        if len(actions) > 5:
            print(f"     ... and {len(actions) - 5} more")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Check list filters
    print("\n✓ Checking list filters...")
    try:
        list_filter = admin_instance.list_filter
        print(f"  ✅ Found {len(list_filter)} filters:")
        for f in list_filter:
            print(f"     - {f}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Check search fields
    print("\n✓ Checking search fields...")
    try:
        search_fields = admin_instance.search_fields
        print(f"  ✅ Found {len(search_fields)} search fields:")
        for field in search_fields:
            print(f"     - {field}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False
    
    # Verify JavaScript file exists
    print("\n✓ Checking admin JavaScript...")
    js_path = "static/admin/js/tournament_admin.js"
    if os.path.exists(js_path):
        size = os.path.getsize(js_path)
        print(f"  ✅ JavaScript file exists ({size} bytes)")
    else:
        print(f"  ❌ JavaScript file not found at {js_path}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ ALL CHECKS PASSED - ADMIN OPTIMIZATION VERIFIED!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("  1. Run Django server: python manage.py runserver")
    print("  2. Navigate to: http://localhost:8000/admin/tournaments/tournament/")
    print("  3. Test creating a new tournament")
    print("  4. Verify game-specific configs appear dynamically")
    print("  5. Check capacity progress bars and schedule status indicators")
    print("  6. Test quick-fill buttons for team sizes")
    print("  7. Verify deprecated fields are hidden")
    print("  8. Try setting a tournament to COMPLETED (archive test)")
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = verify_admin_optimization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
