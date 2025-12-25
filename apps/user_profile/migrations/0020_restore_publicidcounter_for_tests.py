# Generated for UP-UI-FIX-03: Restore PublicIDCounter for test DB

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0027_gp2a_fix_missing_columns"),
    ]

    operations = [
        migrations.CreateModel(
            name="PublicIDCounter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "year",
                    models.IntegerField(
                        help_text="Year (YY format, e.g., 25 for 2025)",
                        unique=True,
                    ),
                ),
                (
                    "counter",
                    models.IntegerField(
                        default=0,
                        help_text="Sequential counter for this year",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True),
                ),
            ],
            options={
                "verbose_name": "Public ID Counter",
                "verbose_name_plural": "Public ID Counters",
                "db_table": "user_profile_publicidcounter",
            },
        ),
        migrations.AddIndex(
            model_name="publicidcounter",
            index=models.Index(fields=["year"], name="idx_publicid_year"),
        ),
    ]
