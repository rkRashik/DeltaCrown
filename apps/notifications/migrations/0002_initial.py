# Adds FKs + indexes
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("notifications", "0001_initial"),
        ("user_profile", "0001_initial"),
        ("tournaments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="recipient",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="notifications",
                to="user_profile.userprofile",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="tournament",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notifications",
                to="tournaments.tournament",
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="match",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="notifications",
                to="tournaments.match",
            ),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "is_read", "created_at"], name="noti_rec_read_created_idx"),
        ),
        migrations.AddIndex(
            model_name="notification",
            index=models.Index(fields=["recipient", "type", "tournament", "match"], name="noti_rec_type_tour_match_idx"),
        ),
    ]
