# Generated for Django 4.2.x
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Notification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("type", models.CharField(
                    choices=[
                        ("reg_confirmed", "Registration confirmed"),
                        ("bracket_ready", "Bracket generated"),
                        ("match_scheduled", "Match scheduled"),
                        ("result_verified", "Result verified"),
                        ("payment_verified", "Payment verified"),
                        ("checkin_open", "Check-in window open"),
                    ],
                    db_index=True,
                    max_length=40
                )),
                ("title", models.CharField(max_length=140)),
                ("body", models.TextField(blank=True)),
                ("url", models.CharField(blank=True, max_length=300)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
