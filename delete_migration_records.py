import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()

# Delete migration records
cursor.execute("""
    DELETE FROM django_migrations 
    WHERE app = 'organizations'
""")

rows_deleted = cursor.rowcount
print(f"✅ Deleted {rows_deleted} organizations migration records from django_migrations")
