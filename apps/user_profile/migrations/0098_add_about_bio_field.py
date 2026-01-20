from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user_profile", "0097_alter_verificationrecord_id_document_back_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="userprofile",
                    name="about_bio",
                    field=models.TextField(
                        blank=True,
                        default="",
                        db_default="",
                        help_text="Short about/bio copy used during account verification safety nets",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ADD COLUMN IF NOT EXISTS about_bio text;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "DROP COLUMN IF EXISTS about_bio;"
                    ),
                ),
                migrations.RunSQL(
                    sql="UPDATE user_profile_userprofile SET about_bio='' WHERE about_bio IS NULL;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN about_bio SET DEFAULT '';"
                    ),
                    reverse_sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN about_bio DROP DEFAULT;"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN about_bio SET NOT NULL;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN about_bio DROP NOT NULL;"
                    ),
                ),
            ],
        ),
    ]
