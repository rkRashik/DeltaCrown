#!/usr/bin/env python
"""List all team-related tables."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' AND table_name LIKE '%team%'
    ORDER BY table_name
""")
tables = cursor.fetchall()
print("Team-related tables:")
for row in tables:
    print(f"  - {row[0]}")
