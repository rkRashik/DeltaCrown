import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("""
    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_name = 'user_profile_userprofile'
    ORDER BY column_name
""")

all_cols = cursor.fetchall()
print("All columns in user_profile_userprofile:")
for col in all_cols:
    print(f"  {col[0]}: {col[1]}, nullable={col[2]}, default={col[3]}")

print("\n\nColumns containing 'about' or 'bio':")
for col in all_cols:
    if 'about' in col[0].lower() or 'bio' in col[0].lower():
        print(f"  {col[0]}: {col[1]}, nullable={col[2]}, default={col[3]}")
