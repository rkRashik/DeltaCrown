"""Add Discord role ID fields for automated role sync.

Teams can configure a Captain Role ID and Manager Role ID.
When a membership role changes, the corresponding Discord role
is assigned/removed via the platform bot API.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0027_discord_integration"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="discord_captain_role_id",
            field=models.CharField(
                blank=True,
                help_text="Discord role ID to assign/remove when a member becomes Captain (OWNER)",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="discord_manager_role_id",
            field=models.CharField(
                blank=True,
                help_text="Discord role ID to assign/remove when a member becomes Manager",
                max_length=20,
            ),
        ),
    ]
