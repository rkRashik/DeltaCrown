"""Check database name and connection."""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection
from django.conf import settings

print("=" * 60)
print("DATABASE CONNECTION INFO")
print("=" * 60)

db_settings = settings.DATABASES['default']
print(f"Engine: {db_settings['ENGINE']}")
print(f"Name: {db_settings['NAME']}")
print(f"User: {db_settings['USER']}")
print(f"Host: {db_settings['HOST']}")
print(f"Port: {db_settings['PORT']}")

# Query the database for the table
cursor = connection.cursor()

# Get current database name
cursor.execute("SELECT current_database()")
current_db = cursor.fetchone()[0]
print(f"\nCurrent Database: {current_db}")

# Check if table exists
cursor.execute("""
    SELECT table_name, table_schema
    FROM information_schema.tables 
    WHERE table_name='accounts_accountdeletionrequest'
""")
result = cursor.fetchone()

if result:
    print(f"\n[OK] Table EXISTS: {result[0]} (schema: {result[1]})")
else:
    print("\n[MISSING] accounts_accountdeletionrequest NOT FOUND")
    
# Try to import and check the model
try:
    from apps.accounts.models import AccountDeletionRequest
    print(f"\n[OK] Model imported: {AccountDeletionRequest}")
    print(f"Table name from model: {AccountDeletionRequest._meta.db_table}")
    
    # Try to query the model
    count = AccountDeletionRequest.objects.count()
    print(f"[OK] Model query works! Count: {count}")
except Exception as e:
    print(f"\n[ERROR] Model import/query failed: {e}")
