from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0010_migrate_legacy_game_ids'),
    ]

    operations = [
        # Use DROP COLUMN IF EXISTS to be resilient when the schema is already partially modified
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS riot_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS riot_tagline"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS efootball_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS steam_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS mlbb_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS mlbb_server_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS pubg_mobile_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS free_fire_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS ea_id"),
        migrations.RunSQL("ALTER TABLE user_profile_userprofile DROP COLUMN IF EXISTS codm_uid"),
    ]
