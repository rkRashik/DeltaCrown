"""
Migration to ensure legacy game ID fields are removed idempotently.

This migration addresses the issue where migration 0012 uses Django's RemoveField
which fails if the columns don't exist, but migration 0011 already removed them
using DROP COLUMN IF EXISTS.

This migration ensures that whether or not the fields exist, the final schema
is consistent and tests can run both with and without --keepdb.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0021_extend_social_and_privacy'),
    ]

    operations = [
        # Ensure all legacy game ID fields are removed using safe DROP COLUMN IF EXISTS
        # This is idempotent - it won't fail if the columns are already gone
        migrations.RunSQL(
            sql="""
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS riot_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS riot_tagline;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS efootball_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS steam_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS mlbb_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS mlbb_server_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS pubg_mobile_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS free_fire_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS ea_id;
            ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS codm_uid;
            """,
            reverse_sql=migrations.RunSQL.noop,  # Rollback not supported for this cleanup
        ),
    ]
