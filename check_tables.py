import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()

# Check ALL schemas (not just specific ones)
cursor.execute("""
    SELECT schemaname, tablename 
    FROM pg_tables 
    WHERE tablename LIKE 'organizations_%'
    ORDER BY schemaname, tablename
""")

# Also check which schema Django is using
print(f"Django is using schema: {connection.settings_dict.get('OPTIONS', {}).get('options', 'public')}")
print()

tables = cursor.fetchall()
print(f"Found {len(tables)} tables:")
for schema, table in tables:
    print(f"  {schema}.{table}")

# Drop them from ALL schemas
for schema, table in tables:
    print(f"Dropping {schema}.{table}...")
    cursor.execute(f"DROP TABLE IF EXISTS {schema}.{table} CASCADE")

print("\n✅ Dropped all organizations tables from all schemas")
