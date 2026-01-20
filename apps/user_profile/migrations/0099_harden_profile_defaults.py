from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("user_profile", "0098_add_about_bio_field"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="userprofile",
                    name="bio",
                    field=models.TextField(
                        blank=True,
                        default="",
                        db_default="",
                        help_text="Profile bio/headline",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="UPDATE user_profile_userprofile SET bio='' WHERE bio IS NULL;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN bio SET DEFAULT '';"
                    ),
                    reverse_sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN bio DROP DEFAULT;"
                    ),
                ),
                migrations.RunSQL(
                    sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN bio SET NOT NULL;"
                    ),
                    reverse_sql=(
                        "ALTER TABLE user_profile_userprofile "
                        "ALTER COLUMN bio DROP NOT NULL;"
                    ),
                ),
            ],
        ),
    ]
