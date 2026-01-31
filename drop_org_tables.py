import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

# Find all organizations tables
cursor.execute("""
    SELECT tablename FROM pg_tables 
    WHERE schemaname='public' AND tablename LIKE 'organizations_%'
""")

tables = [row[0] for row in cursor.fetchall()]
print(f"Found {len(tables)} tables: {tables}")

# Drop each table
for table in tables:
    print(f"Dropping {table}...")
    cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

print("✅ Dropped all organizations tables")
