"""
GP-2A Fix: Idempotent migration to add missing structured identity columns
"""
from django.db import migrations, connection


def add_columns_if_not_exist(apps, schema_editor):
    """
    Idempotently add ign, discriminator, platform columns to GameProfile.
    Safe to run even if columns already exist (IF NOT EXISTS).
    """
    with connection.cursor() as cursor:
        # Check which columns exist
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns 
            WHERE table_name = 'user_profile_gameprofile'
        """)
        existing_columns = {row[0] for row in cursor.fetchall()}
        
        print(f"Existing columns: {existing_columns}")
        
        # Add ign if missing
        if 'ign' not in existing_columns:
            print("Adding column: ign")
            cursor.execute("""
                ALTER TABLE user_profile_gameprofile 
                ADD COLUMN IF NOT EXISTS ign VARCHAR(64) NULL
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS user_profile_gameprofile_ign_idx 
                ON user_profile_gameprofile(ign)
            """)
        else:
            print("Column ign already exists, skipping")
        
        # Add discriminator if missing
        if 'discriminator' not in existing_columns:
            print("Adding column: discriminator")
            cursor.execute("""
                ALTER TABLE user_profile_gameprofile 
                ADD COLUMN IF NOT EXISTS discriminator VARCHAR(32) NULL
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS user_profile_gameprofile_discriminator_idx 
                ON user_profile_gameprofile(discriminator)
            """)
        else:
            print("Column discriminator already exists, skipping")
        
        # Add platform if missing
        if 'platform' not in existing_columns:
            print("Adding column: platform")
            cursor.execute("""
                ALTER TABLE user_profile_gameprofile 
                ADD COLUMN IF NOT EXISTS platform VARCHAR(32) NULL
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS user_profile_gameprofile_platform_idx 
                ON user_profile_gameprofile(platform)
            """)
        else:
            print("Column platform already exists, skipping")
        
        # Verify region exists (should already exist)
        if 'region' not in existing_columns:
            print("WARNING: region column missing! Adding it...")
            cursor.execute("""
                ALTER TABLE user_profile_gameprofile 
                ADD COLUMN IF NOT EXISTS region VARCHAR(10) DEFAULT '' NOT NULL
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS user_profile_gameprofile_region_idx 
                ON user_profile_gameprofile(region)
            """)
        else:
            print("Column region exists")
        
        print("[OK] All GP-2A columns verified/added")


def reverse_migration(apps, schema_editor):
    """
    Reverse: DO NOTHING (safer to keep columns)
    """
    print("Reverse migration: keeping columns for safety")
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0026_gp2a_add_structured_identity'),
    ]

    operations = [
        migrations.RunPython(
            add_columns_if_not_exist,
            reverse_migration
        ),
    ]
