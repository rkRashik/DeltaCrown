# apps/tournaments/migrations/00xx_attendance.py
from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("tournaments", "0007_user_prefs"),  # or your current latest tournaments migration
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="MatchAttendance",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
                ("status", models.CharField(max_length=16, choices=[("invited","Invited"),("confirmed","Confirmed"),("declined","Declined"),("late","Late"),("absent","Absent")], default="invited", db_index=True)),
                ("note", models.CharField(max_length=200, blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="match_attendance", to=settings.AUTH_USER_MODEL)),
                ("match", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attendance", to="tournaments.match")),
            ],
            options={},
        ),
        migrations.AddConstraint(
            model_name="matchattendance",
            constraint=models.UniqueConstraint(fields=("user","match"), name="uq_match_attendance_user_match"),
        ),
    ]
