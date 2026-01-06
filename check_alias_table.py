import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'user_profile_gameprofilealias' 
    ORDER BY ordinal_position
""")

print("GameProfileAlias table columns:")
print("-" * 60)
for row in cursor.fetchall():
    print(f"{row[0]:<40} {row[1]}")
