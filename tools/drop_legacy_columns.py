#!/usr/bin/env python
"""Manually drop legacy game ID columns from the database."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

def drop_legacy_columns():
    """Drop legacy game ID columns that should have been removed by migration 0011."""
    legacy_fields = [
        'riot_id', 'riot_tagline', 'efootball_id', 'steam_id',
        'mlbb_id', 'mlbb_server_id', 'pubg_mobile_id', 'free_fire_id',
        'ea_id', 'codm_uid'
    ]
    
    print("Dropping legacy game ID columns from user_profile_userprofile...")
    
    with connection.cursor() as cursor:
        for field in legacy_fields:
            try:
                print(f"  Dropping {field}...", end=" ")
                cursor.execute(f"ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS {field}")
                print("✓")
            except Exception as e:
                print(f"✗ Error: {e}")
    
    print("\n✅ All legacy columns dropped successfully!")

if __name__ == '__main__':
    drop_legacy_columns()
