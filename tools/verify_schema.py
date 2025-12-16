#!/usr/bin/env python
"""Verify that legacy game ID columns have been removed from the database."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

def check_columns():
    """Check which columns exist in user_profile_userprofile table."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_profile_userprofile'
            ORDER BY ordinal_position
        """)
        columns = [row[0] for row in cursor.fetchall()]
    
    # Legacy game ID fields that should be removed
    legacy_fields = [
        'riot_id', 'riot_tagline', 'efootball_id', 'steam_id',
        'mlbb_id', 'mlbb_server_id', 'pubg_mobile_id', 'free_fire_id',
        'ea_id', 'codm_uid'
    ]
    
    print("=== User Profile Table Columns ===")
    print(f"Total columns: {len(columns)}\n")
    
    # Check for legacy fields
    found_legacy = [field for field in legacy_fields if field in columns]
    
    if found_legacy:
        print("❌ LEGACY FIELDS STILL EXIST:")
        for field in found_legacy:
            print(f"  - {field}")
        print("\nThese fields should have been removed by migration 0011.")
        return False
    else:
        print("✅ All legacy game ID fields have been removed!")
    
    # Check for game_profiles
    if 'game_profiles' in columns:
        print("✅ game_profiles JSON field exists!")
    else:
        print("❌ game_profiles JSON field is missing!")
        return False
    
    print("\n=== Key columns ===")
    for col in ['id', 'user_id', 'display_name', 'game_profiles', 'region', 'created_at']:
        if col in columns:
            print(f"  ✓ {col}")
    
    return True

if __name__ == '__main__':
    success = check_columns()
    sys.exit(0 if success else 1)
