# Generated for schema drift repair
# Date: 2026-01-14
# Purpose: Restore missing left_at column on teams_teammembership table
#          Column was defined in migration 0021 but missing from database

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0023_remove_teammembership_teams_member_left_at_idx'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Repair: Add left_at column if missing (from migration 0021)
            -- Must target public schema explicitly to avoid test_schema drift
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'teams_teammembership'
                      AND column_name = 'left_at'
                ) THEN
                    ALTER TABLE public.teams_teammembership
                    ADD COLUMN left_at timestamp with time zone NULL;
                    
                    RAISE NOTICE 'Added left_at column to teams_teammembership';
                ELSE
                    RAISE NOTICE 'left_at column already exists, skipping';
                END IF;
            END $$;
            
            -- Recreate index if missing (originally from migration 0021)
            -- Note: Migration 0023 removed this index, but we recreate for consistency
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes
                    WHERE schemaname = 'public'
                      AND tablename = 'teams_teammembership'
                      AND indexname = 'teams_member_left_at_idx'
                ) THEN
                    CREATE INDEX teams_member_left_at_idx
                    ON public.teams_teammembership (profile_id, left_at);
                    
                    RAISE NOTICE 'Created index teams_member_left_at_idx';
                ELSE
                    RAISE NOTICE 'Index teams_member_left_at_idx already exists, skipping';
                END IF;
            END $$;
            """,
            reverse_sql="-- No reverse operation needed (idempotent)",
        ),
    ]
