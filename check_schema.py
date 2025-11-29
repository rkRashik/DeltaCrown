import os
import django
import sys

# Add the project directory to the Python path
sys.path.insert(0, os.path.dirname(__file__))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection
cursor = connection.cursor()
cursor.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'tournaments_tournament' AND column_name LIKE '%registration%' ORDER BY column_name;")
rows = cursor.fetchall()
for row in rows:
    print(f"{row[0]}: {row[1]} (nullable: {row[2]})")

# Also check for 'overrides' columns
cursor.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'tournaments_tournament' AND column_name LIKE '%override%' ORDER BY column_name;")
rows = cursor.fetchall()
for row in rows:
    print(f"{row[0]}: {row[1]} (nullable: {row[2]})")

# Check registration table fields
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'tournaments_registration' AND column_name IN ('completion_percentage', 'current_step', 'time_spent_seconds');")
rows = cursor.fetchall()
for row in rows:
    print(f"Registration field exists: {row[0]}")