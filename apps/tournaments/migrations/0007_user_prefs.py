# apps/tournaments/migrations/00xx_user_prefs.py
from django.db import migrations, models
import django.db.models.deletion

def backfill_calendar_tokens(apps, schema_editor):
    User = apps.get_model("auth", "User")
    CalendarFeedToken = apps.get_model("tournaments", "CalendarFeedToken")
    import secrets
    for u in User.objects.all():
        CalendarFeedToken.objects.get_or_create(user_id=u.id, defaults={"token": secrets.token_urlsafe(32)})

class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0001_initial"),  # adjust to your latest
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="CalendarFeedToken",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
                ("token", models.CharField(max_length=64, unique=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="auth.user", related_name="calendar_feed_token")),
            ],
        ),
        migrations.CreateModel(
            name="SavedMatchFilter",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
                ("name", models.CharField(max_length=48, default="Default")),
                ("is_default", models.BooleanField(default=False)),
                ("game", models.CharField(max_length=20, blank=True)),
                ("state", models.CharField(max_length=20, blank=True)),
                ("tournament_id", models.IntegerField(null=True, blank=True)),
                ("start_date", models.DateField(null=True, blank=True)),
                ("end_date", models.DateField(null=True, blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_match_filters", to="auth.user")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["user", "name"], name="uq_saved_match_filter_user_name")]},
        ),
        migrations.CreateModel(
            name="PinnedTournament",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
                ("tournament_id", models.IntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pinned_tournaments", to="auth.user")),
            ],
            options={"constraints": [models.UniqueConstraint(fields=["user", "tournament_id"], name="uq_pin_user_tournament")]},
        ),
        migrations.RunPython(backfill_calendar_tokens, reverse_code=migrations.RunPython.noop),
    ]
