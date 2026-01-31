"""Add missing accent_color column"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        ALTER TABLE organizations_team 
        ADD COLUMN IF NOT EXISTS accent_color varchar(7) DEFAULT '#10B981'
    """)
    print("✓ Added accent_color column")
