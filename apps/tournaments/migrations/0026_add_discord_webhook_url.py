# Generated manually for discord webhook integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0025_add_contact_social_support_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="tournament",
            name="discord_webhook_url",
            field=models.URLField(
                blank=True,
                default="",
                help_text="Discord webhook URL for automated tournament notifications",
            ),
        ),
    ]
