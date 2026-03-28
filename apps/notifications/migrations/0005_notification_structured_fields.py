from django.db import migrations, models


def copy_category_to_notification_type(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    Notification.objects.all().update(notification_type=models.F("category"))


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0004_rename_notifications_recipient_category_created_idx_notificatio_recipie_5a7f6a_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="action_data",
            field=models.JSONField(blank=True, default=dict, help_text="Structured CTA payload for Accept/Decline or other actions"),
        ),
        migrations.AddField(
            model_name="notification",
            name="avatar_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="notification",
            name="html_text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="notification",
            name="image_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="notification",
            name="notification_type",
            field=models.CharField(blank=True, choices=[("TOURNAMENT", "Tournament"), ("TEAM", "Team"), ("ECONOMY", "Economy"), ("SOCIAL", "Social"), ("SYSTEM", "System"), ("WARNING", "Warning")], db_index=True, default="SYSTEM", help_text="Structured frontend notification category for smart rendering", max_length=20),
        ),
        migrations.RunPython(copy_category_to_notification_type, migrations.RunPython.noop),
    ]
