from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_lowercase_type_values"),
        ("notifications", "0003_remove_notification_notificatio_recipie_95d1d9_idx_and_more"),
    ]

    operations = [
        # No-op merge. If you want, you can add a RunPython here to re-normalize
        # types again; it's idempotent. Not required.
    ]
