"""Add change tracking timestamps to Team for name/tag/region change restrictions."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0022_add_team_whatsapp_messenger"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="name_changed_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Last time team name was changed (30-day cooldown)",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="tag_changed_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Last time team tag was changed (30-day cooldown)",
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="region_changed_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Last time team region was changed (30-day cooldown)",
            ),
        ),
    ]
