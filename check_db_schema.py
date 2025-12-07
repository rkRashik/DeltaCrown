import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, is_nullable, data_type, column_default 
    FROM information_schema.columns 
    WHERE table_name = 'teams_teammembership' 
    AND column_name LIKE '%metadata%'
""")

print("\nColumns containing 'metadata' in teams_teammembership table:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[2]}, nullable={row[1]}, default={row[3]}")
