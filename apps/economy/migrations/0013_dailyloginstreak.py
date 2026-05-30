from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0012_phase_d_fortress_pin_hash"),
        ("user_profile", "0048_alter_communitypreferences_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="DailyLoginStreak",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("current_streak", models.PositiveIntegerField(default=0)),
                ("best_streak", models.PositiveIntegerField(default=0)),
                ("last_claim_date", models.DateField(blank=True, null=True)),
                ("total_claimed", models.PositiveIntegerField(default=0)),
                (
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_streak",
                        to="user_profile.userprofile",
                    ),
                ),
            ],
            options={"verbose_name": "Daily Login Streak"},
        ),
    ]
