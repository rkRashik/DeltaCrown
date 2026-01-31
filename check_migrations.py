import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()

# Check if migration records exist
cursor.execute("""
    SELECT app, name, applied 
    FROM django_migrations 
    WHERE app = 'organizations'
    ORDER BY id
""")

migrations = cursor.fetchall()
print(f"Found {len(migrations)} migration records:")
for app, name, applied in migrations:
    print(f"  {app}.{name} - {applied}")
