#!/usr/bin/env python
"""Check team membership constraints."""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT conname, pg_get_constraintdef(oid) as definition
    FROM pg_constraint 
    WHERE conrelid = 'organizations_membership'::regclass
    AND contype = 'u'
    ORDER BY conname
""")

print("TeamMembership Unique Constraints:")
print("-" * 80)
for row in cursor.fetchall():
    print(f"\nConstraint: {row[0]}")
    print(f"Definition: {row[1]}")
