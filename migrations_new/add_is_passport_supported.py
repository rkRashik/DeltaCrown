# apps/games/migrations/XXXX_add_is_passport_supported.py
"""
Add is_passport_supported flag to Game model to explicitly mark
which games support Game Passport functionality.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0XXX_previous_migration'),  # Update with actual previous migration
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='is_passport_supported',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Does this game support Game Passport functionality?'
            ),
        ),
    ]
