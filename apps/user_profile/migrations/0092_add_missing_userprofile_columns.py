# Generated migration to add missing UserProfile fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0091_add_missing_userprofile_fields'),
        ('games', '0001_initial'),  # For ForeignKey to Game
        ('teams', '0001_initial'),  # For ForeignKey to Team
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- Add profile_story field
            ALTER TABLE user_profile_userprofile 
            ADD COLUMN IF NOT EXISTS profile_story TEXT NOT NULL DEFAULT '';
            
            -- Add competitive_goal field
            ALTER TABLE user_profile_userprofile 
            ADD COLUMN IF NOT EXISTS competitive_goal VARCHAR(160) NOT NULL DEFAULT '';
            
            -- Add lft_status field
            ALTER TABLE user_profile_userprofile 
            ADD COLUMN IF NOT EXISTS lft_status VARCHAR(20) NOT NULL DEFAULT 'NOT_LOOKING';
            
            -- Add primary_team_id field (ForeignKey)
            ALTER TABLE user_profile_userprofile 
            ADD COLUMN IF NOT EXISTS primary_team_id INTEGER NULL;
            
            -- Add primary_game_id field (ForeignKey)
            ALTER TABLE user_profile_userprofile 
            ADD COLUMN IF NOT EXISTS primary_game_id INTEGER NULL;
            
            -- Add foreign key constraints
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'user_profile_userpro_primary_team_id_fkey'
                ) THEN
                    ALTER TABLE user_profile_userprofile 
                    ADD CONSTRAINT user_profile_userpro_primary_team_id_fkey 
                    FOREIGN KEY (primary_team_id) 
                    REFERENCES teams_team(id) 
                    ON DELETE SET NULL;
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'user_profile_userpro_primary_game_id_fkey'
                ) THEN
                    ALTER TABLE user_profile_userprofile 
                    ADD CONSTRAINT user_profile_userpro_primary_game_id_fkey 
                    FOREIGN KEY (primary_game_id) 
                    REFERENCES games_game(id) 
                    ON DELETE SET NULL;
                END IF;
            END $$;
            
            -- Create indexes for foreign keys
            CREATE INDEX IF NOT EXISTS idx_userprofile_primary_team 
            ON user_profile_userprofile(primary_team_id);
            
            CREATE INDEX IF NOT EXISTS idx_userprofile_primary_game 
            ON user_profile_userprofile(primary_game_id);
            """,
            reverse_sql="""
            DROP INDEX IF EXISTS idx_userprofile_primary_game;
            DROP INDEX IF EXISTS idx_userprofile_primary_team;
            ALTER TABLE user_profile_userprofile DROP CONSTRAINT IF EXISTS user_profile_userpro_primary_game_id_fkey;
            ALTER TABLE user_profile_userprofile DROP CONSTRAINT IF EXISTS user_profile_userpro_primary_team_id_fkey;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS primary_game_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS primary_team_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS lft_status;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS competitive_goal;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS profile_story;
            """
        ),
    ]
