# Generated for GP-STABILIZE-01 - Add timestamps to GameProfileConfig
# Safe for production: columns may already exist from manual SQL
from django.db import migrations, models
from django.utils import timezone


def add_timestamps_if_missing(apps, schema_editor):
    """
    Add created_at/updated_at columns if they don't exist.
    Safe for databases where columns were already added manually.
    """
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check if columns exist
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'user_profile_gameprofileconfig' 
            AND column_name IN ('created_at', 'updated_at')
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        # Add created_at if missing
        if 'created_at' not in existing_columns:
            cursor.execute("""
                ALTER TABLE user_profile_gameprofileconfig 
                ADD COLUMN created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            """)
        
        # Add updated_at if missing
        if 'updated_at' not in existing_columns:
            cursor.execute("""
                ALTER TABLE user_profile_gameprofileconfig 
                ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            """)


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0020_gp0_game_passport_rebuild'),
    ]

    operations = [
        # Custom SQL to add columns idempotently
        migrations.RunPython(
            add_timestamps_if_missing,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
