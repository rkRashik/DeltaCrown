from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0008_follow"),
    ]

    operations = [
        # Use RunSQL with IF NOT EXISTS to make this migration idempotent
        # This is necessary because riot_id already exists in 0001_initial (after squashing)
        migrations.RunSQL(
            sql="""
            ALTER TABLE user_profile_userprofile 
            ADD COLUMN IF NOT EXISTS riot_id VARCHAR(100) DEFAULT '' NOT NULL;
            
            COMMENT ON COLUMN user_profile_userprofile.riot_id IS 'Riot ID (Name#TAG) for Valorant';
            """,
            reverse_sql="ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS riot_id;",
        ),
    ]
