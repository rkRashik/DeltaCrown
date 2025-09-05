# Django 4.2 migration
from django.db import migrations, models


def backfill_event_from_type(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    # copy current `type` values into `event` so old rows pass tests
    for n in Notification.objects.all().only("id", "type"):
        Notification.objects.filter(id=n.id).update(event=(n.type or "generic"))


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="event",
            field=models.CharField(default="generic", max_length=64, db_index=True),
        ),
        migrations.RunPython(backfill_event_from_type, reverse_code=migrations.RunPython.noop),
    ]
