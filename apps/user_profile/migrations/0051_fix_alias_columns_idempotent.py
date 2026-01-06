"""
Phase 9A-8: Idempotent migration to fix GameProfileAlias columns

This migration safely adds missing columns to GameProfileAlias if they don't exist.
It's designed to work even if migrations were faked or partially applied.

Columns added:
- old_ign VARCHAR(64)
- old_discriminator VARCHAR(32)
- old_platform VARCHAR(32)
- old_region VARCHAR(10)

These columns track structured identity history for the Fair Play Protocol (30-day lock).
"""

from django.db import migrations, connection


def fix_alias_columns(apps, schema_editor):
    """
    Idempotently add missing columns to GameProfileAlias.
    Safe to run multiple times - uses IF NOT EXISTS.
    """
    db_vendor = connection.vendor
    
    with connection.cursor() as cursor:
        if db_vendor == 'postgresql':
            # PostgreSQL supports IF NOT EXISTS
            print("📝 Checking GameProfileAlias columns (PostgreSQL)...")
            
            # Check existing columns
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_name = 'user_profile_gameprofilealias'
                  AND table_schema = 'public'
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}
            print(f"   Existing columns: {len(existing_columns)}")
            
            # Add old_ign if missing
            if 'old_ign' not in existing_columns:
                print("   ✅ Adding column: old_ign")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN IF NOT EXISTS old_ign VARCHAR(64) NULL
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS user_profile_gameprofilealias_old_ign_idx 
                    ON user_profile_gameprofilealias(old_ign)
                """)
            else:
                print("   ⏭️  Column old_ign already exists")
            
            # Add old_discriminator if missing
            if 'old_discriminator' not in existing_columns:
                print("   ✅ Adding column: old_discriminator")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN IF NOT EXISTS old_discriminator VARCHAR(32) NULL
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS user_profile_gameprofilealias_old_discriminator_idx 
                    ON user_profile_gameprofilealias(old_discriminator)
                """)
            else:
                print("   ⏭️  Column old_discriminator already exists")
            
            # Add old_platform if missing
            if 'old_platform' not in existing_columns:
                print("   ✅ Adding column: old_platform")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN IF NOT EXISTS old_platform VARCHAR(32) NULL
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS user_profile_gameprofilealias_old_platform_idx 
                    ON user_profile_gameprofilealias(old_platform)
                """)
            else:
                print("   ⏭️  Column old_platform already exists")
            
            # Add old_region if missing
            if 'old_region' not in existing_columns:
                print("   ✅ Adding column: old_region")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN IF NOT EXISTS old_region VARCHAR(10) DEFAULT '' NOT NULL
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS user_profile_gameprofilealias_old_region_idx 
                    ON user_profile_gameprofilealias(old_region)
                """)
            else:
                print("   ⏭️  Column old_region already exists")
            
            print("✅ GameProfileAlias columns verified/added")
            
        elif db_vendor == 'sqlite':
            # SQLite doesn't support IF NOT EXISTS for columns
            # Use PRAGMA table_info to check
            print("📝 Checking GameProfileAlias columns (SQLite)...")
            
            cursor.execute("PRAGMA table_info(user_profile_gameprofilealias)")
            columns = [row[1] for row in cursor.fetchall()]
            existing_columns = set(columns)
            print(f"   Existing columns: {len(existing_columns)}")
            
            # SQLite requires manual field addition via Django ORM if columns missing
            if 'old_ign' not in existing_columns:
                print("   ✅ Adding column: old_ign")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN old_ign VARCHAR(64) NULL
                """)
            else:
                print("   ⏭️  Column old_ign already exists")
            
            if 'old_discriminator' not in existing_columns:
                print("   ✅ Adding column: old_discriminator")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN old_discriminator VARCHAR(32) NULL
                """)
            else:
                print("   ⏭️  Column old_discriminator already exists")
            
            if 'old_platform' not in existing_columns:
                print("   ✅ Adding column: old_platform")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN old_platform VARCHAR(32) NULL
                """)
            else:
                print("   ⏭️  Column old_platform already exists")
            
            if 'old_region' not in existing_columns:
                print("   ✅ Adding column: old_region")
                cursor.execute("""
                    ALTER TABLE user_profile_gameprofilealias 
                    ADD COLUMN old_region VARCHAR(10) DEFAULT '' NOT NULL
                """)
            else:
                print("   ⏭️  Column old_region already exists")
            
            print("✅ GameProfileAlias columns verified/added (SQLite)")
            
        elif db_vendor == 'mysql':
            # MySQL - check information_schema
            print("📝 Checking GameProfileAlias columns (MySQL)...")
            
            cursor.execute("""
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'user_profile_gameprofilealias'
            """)
            existing_columns = {row[0] for row in cursor.fetchall()}
            print(f"   Existing columns: {len(existing_columns)}")
            
            # MySQL - use IF NOT EXISTS if MySQL 8.0+, otherwise try/except
            if 'old_ign' not in existing_columns:
                print("   ✅ Adding column: old_ign")
                try:
                    cursor.execute("""
                        ALTER TABLE user_profile_gameprofilealias 
                        ADD COLUMN old_ign VARCHAR(64) NULL
                    """)
                except Exception as e:
                    if 'Duplicate column' in str(e):
                        print("   ⏭️  Column old_ign already exists (duplicate detected)")
                    else:
                        raise
            else:
                print("   ⏭️  Column old_ign already exists")
            
            if 'old_discriminator' not in existing_columns:
                print("   ✅ Adding column: old_discriminator")
                try:
                    cursor.execute("""
                        ALTER TABLE user_profile_gameprofilealias 
                        ADD COLUMN old_discriminator VARCHAR(32) NULL
                    """)
                except Exception as e:
                    if 'Duplicate column' in str(e):
                        print("   ⏭️  Column old_discriminator already exists")
                    else:
                        raise
            else:
                print("   ⏭️  Column old_discriminator already exists")
            
            if 'old_platform' not in existing_columns:
                print("   ✅ Adding column: old_platform")
                try:
                    cursor.execute("""
                        ALTER TABLE user_profile_gameprofilealias 
                        ADD COLUMN old_platform VARCHAR(32) NULL
                    """)
                except Exception as e:
                    if 'Duplicate column' in str(e):
                        print("   ⏭️  Column old_platform already exists")
                    else:
                        raise
            else:
                print("   ⏭️  Column old_platform already exists")
            
            if 'old_region' not in existing_columns:
                print("   ✅ Adding column: old_region")
                try:
                    cursor.execute("""
                        ALTER TABLE user_profile_gameprofilealias 
                        ADD COLUMN old_region VARCHAR(10) DEFAULT '' NOT NULL
                    """)
                except Exception as e:
                    if 'Duplicate column' in str(e):
                        print("   ⏭️  Column old_region already exists")
                    else:
                        raise
            else:
                print("   ⏭️  Column old_region already exists")
            
            print("✅ GameProfileAlias columns verified/added (MySQL)")
        
        else:
            print(f"⚠️  Unknown database vendor: {db_vendor}")
            print("   Migration skipped - manual intervention required")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration: DO NOTHING (safer to keep columns)
    Manually drop columns if needed:
      ALTER TABLE user_profile_gameprofilealias DROP COLUMN old_ign;
      ALTER TABLE user_profile_gameprofilealias DROP COLUMN old_discriminator;
      ALTER TABLE user_profile_gameprofilealias DROP COLUMN old_platform;
      ALTER TABLE user_profile_gameprofilealias DROP COLUMN old_region;
    """
    print("⏪ Reverse migration: keeping columns for safety")
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0050_phase8b_verification_status'),
    ]

    operations = [
        migrations.RunPython(
            fix_alias_columns,
            reverse_migration
        ),
    ]
