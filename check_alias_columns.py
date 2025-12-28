#!/usr/bin/env python
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'user_profile_gameprofilealias' 
        ORDER BY column_name
    """)
    columns = [row[0] for row in cursor.fetchall()]
    print("GameProfileAlias columns:")
    for col in columns:
        print(f"  - {col}")
    
    if 'old_ign' in columns:
        print("\n✅ old_ign column EXISTS")
    else:
        print("\n❌ old_ign column MISSING!")
        print("\nNeed to run migration to add it.")
