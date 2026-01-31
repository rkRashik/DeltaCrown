"""Add missing uuid and public_id columns to organizations_organization"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        ALTER TABLE organizations_organization 
        ADD COLUMN IF NOT EXISTS uuid uuid DEFAULT gen_random_uuid() UNIQUE
    """)
    print("✓ Added uuid column")
    
    cursor.execute("""
        ALTER TABLE organizations_organization 
        ADD COLUMN IF NOT EXISTS public_id varchar(12) DEFAULT '' 
    """)
    print("✓ Added public_id column")
