"""
Script to add database-level DEFAULT value to bio column.

The issue: bio field has NOT NULL constraint but no database-level default.
Django's model default="" only works when Django creates the object,
but if the field is somehow omitted from INSERT, database rejects it.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    print("Adding database-level DEFAULT '' to bio column...")
    
    # Add default value to bio column
    cursor.execute("""
        ALTER TABLE user_profile_userprofile 
        ALTER COLUMN bio SET DEFAULT '';
    """)
    
    print("✅ Successfully added DEFAULT '' to bio column")
    
    # Verify the change
    cursor.execute("""
        SELECT 
            a.attname as column_name,
            pg_get_expr(d.adbin, d.adrelid) as default_value,
            a.attnotnull as not_null
        FROM pg_catalog.pg_attribute a
        LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid, a.attnum) = (d.adrelid, d.adnum)
        WHERE a.attrelid = 'user_profile_userprofile'::regclass
        AND a.attname = 'bio'
        AND NOT a.attisdropped;
    """)
    
    result = cursor.fetchone()
    if result:
        col_name, default, not_null = result
        print(f"\nVerification:")
        print(f"  Column: {col_name}")
        print(f"  NOT NULL: {not_null}")
        print(f"  DEFAULT: {default}")
