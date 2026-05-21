from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MobileDeviceToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(db_index=True, max_length=512, unique=True)),
                (
                    "platform",
                    models.CharField(choices=[("android", "Android"), ("ios", "iOS")], max_length=16),
                ),
                ("device_id", models.CharField(blank=True, db_index=True, max_length=128)),
                ("app_version", models.CharField(blank=True, max_length=40)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mobile_device_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="mobiledevicetoken",
            index=models.Index(fields=["user", "is_active"], name="mobile_api_user_id_e17912_idx"),
        ),
        migrations.AddIndex(
            model_name="mobiledevicetoken",
            index=models.Index(fields=["platform", "is_active"], name="mobile_api_platfor_d82248_idx"),
        ),
    ]
