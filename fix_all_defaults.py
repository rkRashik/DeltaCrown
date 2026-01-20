"""
Add database-level defaults to ALL NOT NULL columns that don't have them.
This ensures database will accept INSERT even if Django omits fields.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

# Map of columns to their appropriate default values based on data type
DEFAULT_VALUES = {
    # Already handled
    'bio': "''",  # Already fixed
    
    # Text/String fields - use empty string
    'display_name': "''",
    'slug': "''",
    'nationality': "''",
    'real_full_name': "''",
    'address': "''",
    'city': "''",
    'country': "''",
    'postal_code': "''",
    'gender': "''",
    'pronouns': "''",
    'phone': "''",
    'whatsapp': "''",
    'secondary_email': "''",
    'preferred_contact_method': "''",
    'emergency_contact_name': "''",
    'emergency_contact_phone': "''",
    'emergency_contact_relation': "''",
    'preferred_language': "'en'",
    'theme_preference': "'dark'",
    'time_format': "'12h'",
    'timezone_pref': "'UTC'",
    'device_platform': "''",
    'active_hours': "''",
    'main_role': "''",
    'play_style': "''",
    'secondary_role': "''",
    
    # Numeric fields
    'deltacoin_balance': "0",
    'level': "1",
    'xp': "0",
    'reputation_score': "100",
    'skill_rating': "1000",
    'lifetime_earnings': "0",
    
    # Boolean fields
    'stream_status': "FALSE",
    'secondary_email_verified': "FALSE",
    'lan_availability': "FALSE",
    
    # JSONB fields - use empty JSON object or array
    'attributes': "'{}'",
    'system_settings': "'{}'",
    'game_profiles': "'[]'",
    'inventory_items': "'[]'",
    'pinned_badges': "'[]'",
    'communication_languages': "'[]'",
    
    # Special fields
    'region': "'BD'",
    'kyc_status': "'unverified'",
}

with connection.cursor() as cursor:
    print("=" * 80)
    print("ADDING DATABASE-LEVEL DEFAULTS TO ALL NOT NULL COLUMNS")
    print("=" * 80)
    
    # Get current schema
    cursor.execute("""
        SELECT 
            a.attname as column_name,
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
    
    updated_count = 0
    skipped_count = 0
    
    for col_name, dtype, not_null, current_default in columns:
        # Skip if already has default or is nullable
        if current_default or not not_null:
            skipped_count += 1
            continue
            
        # Skip auto-managed fields
        if col_name in ['id', 'created_at', 'updated_at', 'uuid']:
            print(f"⏭  Skipping auto-managed field: {col_name}")
            skipped_count += 1
            continue
        
        # Get the default value for this column
        if col_name not in DEFAULT_VALUES:
            print(f"⚠  WARNING: No default defined for {col_name} ({dtype})")
            continue
            
        default_value = DEFAULT_VALUES[col_name]
        
        try:
            sql = f"ALTER TABLE user_profile_userprofile ALTER COLUMN {col_name} SET DEFAULT {default_value};"
            cursor.execute(sql)
            print(f"✅ {col_name:35s} → DEFAULT {default_value}")
            updated_count += 1
        except Exception as e:
            print(f"❌ Failed to set default for {col_name}: {e}")
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: Updated {updated_count} columns, Skipped {skipped_count} columns")
    print("=" * 80)
    
    # Verify critical fields
    print("\n" + "=" * 80)
    print("VERIFICATION OF KEY FIELDS:")
    print("=" * 80)
    
    cursor.execute("""
        SELECT 
            a.attname as column_name,
            pg_get_expr(d.adbin, d.adrelid) as default_value,
            a.attnotnull as not_null
        FROM pg_catalog.pg_attribute a
        LEFT JOIN pg_catalog.pg_attrdef d ON (a.attrelid, a.attnum) = (d.adrelid, d.adnum)
        WHERE a.attrelid = 'user_profile_userprofile'::regclass
        AND a.attname IN ('bio', 'display_name', 'slug', 'region', 'kyc_status')
        AND NOT a.attisdropped
        ORDER BY a.attname;
    """)
    
    for col_name, default, not_null in cursor.fetchall():
        status = "✅" if default else "❌"
        print(f"{status} {col_name:20s} NOT_NULL={not_null:5s} DEFAULT={default}")
