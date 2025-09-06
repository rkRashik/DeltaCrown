# apps/tournaments/migrations/0011_merge_0009_0010.py
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0009_alter_calendarfeedtoken_id_alter_pinnedtournament_id_and_more"),
        ("tournaments", "0010_attendance"),
    ]

    # This merge resolves the two heads; no schema changes.
    operations = []
