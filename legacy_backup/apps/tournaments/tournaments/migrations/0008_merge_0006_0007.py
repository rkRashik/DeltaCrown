# Generated manually to resolve migration graph conflict between:
#   0006_merge_groups_published_conflict
#   0007_user_prefs
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0006_merge_groups_published_conflict"),
        ("tournaments", "0007_user_prefs"),
    ]

    # This merge just joins histories; no schema changes needed.
    operations = []
