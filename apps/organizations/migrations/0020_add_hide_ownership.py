"""
Migration: Add hide_ownership to TeamMembership

Allows team owners to hide their ownership status from the public team display.
Privacy feature requested for owner discretion.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0019_add_roster_image_display_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='teammembership',
            name='hide_ownership',
            field=models.BooleanField(
                default=False,
                help_text='Owner can hide ownership status from public team display',
            ),
        ),
    ]
