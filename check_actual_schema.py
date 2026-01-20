import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    # Get all columns with their constraints
    cursor.execute("""
        SELECT 
            a.attname as column_name,
            a.attnum as position,
            pg_catalog.format_type(a.atttypid, a.atttypmod) as data_type,
            a.attnotnull as not_null,
            pg_get_expr(d.adbin, d.adrelid) as default_value
        FROM pg_catalog.pg_attribute a
        LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid, a.attnum) = (d.adrelid, d.adnum)
        WHERE a.attrelid = 'user_profile_userprofile'::regclass
        AND a.attnum > 0
        AND NOT a.attisdropped
        ORDER BY a.attnum;
    """)
    
    columns = cursor.fetchall()
    
    print("=" * 100)
    print("FULL SCHEMA FOR user_profile_userprofile")
    print("=" * 100)
    
    for col in columns:
        col_name, pos, dtype, not_null, default = col
        not_null_str = "NOT NULL" if not_null else "NULLABLE"
        default_str = f"DEFAULT: {default}" if default else "NO DEFAULT"
        
        # Highlight columns with "bio" or "about" in the name
        if "bio" in col_name.lower() or "about" in col_name.lower():
            print(f">>> {pos:3d}. {col_name:30s} {dtype:20s} {not_null_str:10s} {default_str}")
        else:
            print(f"    {pos:3d}. {col_name:30s} {dtype:20s} {not_null_str:10s} {default_str}")
    
    print("\n" + "=" * 100)
    print("COLUMNS WITH NOT NULL CONSTRAINT AND NO DEFAULT:")
    print("=" * 100)
    
    for col in columns:
        col_name, pos, dtype, not_null, default = col
        if not_null and not default:
            print(f"  Position {pos:3d}: {col_name:30s} {dtype:20s}")
