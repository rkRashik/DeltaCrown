from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0006_align_user_fk"),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE user_profile_userprofile DROP CONSTRAINT IF EXISTS "
                "user_profile_userprofile_user_id_84fd5b2a_fk_auth_user_id;"
                "ALTER TABLE user_profile_userprofile DROP CONSTRAINT IF EXISTS "
                "user_profile_userprofile_user_id_fkey;"
                "ALTER TABLE user_profile_userprofile ADD CONSTRAINT "
                "user_profile_userprofile_user_id_fk_accounts_user "
                "FOREIGN KEY (user_id) REFERENCES accounts_user(id) "
                "DEFERRABLE INITIALLY IMMEDIATE;"
            ),
            reverse_sql=(
                "ALTER TABLE user_profile_userprofile DROP CONSTRAINT IF EXISTS "
                "user_profile_userprofile_user_id_fk_accounts_user;"
                "ALTER TABLE user_profile_userprofile ADD CONSTRAINT "
                "user_profile_userprofile_user_id_84fd5b2a_fk_auth_user_id "
                "FOREIGN KEY (user_id) REFERENCES auth_user(id) "
                "DEFERRABLE INITIALLY IMMEDIATE;"
            ),
        ),
    ]
