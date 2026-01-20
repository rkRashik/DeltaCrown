# Generated migration to drop orphaned social media columns from UserProfile
# These columns exist in database but were removed from model after social links were moved to SocialLink model

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0088_drop_orphaned_privacy_fields'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN
                -- Drop orphaned social media link columns
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile_userprofile' AND column_name='discord_id') THEN
                    ALTER TABLE user_profile_userprofile DROP COLUMN discord_id CASCADE;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile_userprofile' AND column_name='facebook') THEN
                    ALTER TABLE user_profile_userprofile DROP COLUMN facebook CASCADE;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile_userprofile' AND column_name='instagram') THEN
                    ALTER TABLE user_profile_userprofile DROP COLUMN instagram CASCADE;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile_userprofile' AND column_name='tiktok') THEN
                    ALTER TABLE user_profile_userprofile DROP COLUMN tiktok CASCADE;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile_userprofile' AND column_name='twitch_link') THEN
                    ALTER TABLE user_profile_userprofile DROP COLUMN twitch_link CASCADE;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile_userprofile' AND column_name='twitter') THEN
                    ALTER TABLE user_profile_userprofile DROP COLUMN twitter CASCADE;
                END IF;
                
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='user_profile_userprofile' AND column_name='youtube_link') THEN
                    ALTER TABLE user_profile_userprofile DROP COLUMN youtube_link CASCADE;
                END IF;
            END $$;
            """,
            reverse_sql="""
            -- No reverse: these fields were already removed from the model
            -- Cannot safely recreate them
            """
        ),
    ]
