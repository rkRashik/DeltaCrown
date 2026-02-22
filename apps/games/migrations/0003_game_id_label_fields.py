# Generated migration — adds game_id_label and game_id_placeholder to Game model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='game_id_label',
            field=models.CharField(
                blank=True,
                default='',
                help_text=(
                    "Custom label for a player's in-game identifier "
                    "(e.g. 'Riot ID' for Valorant, 'Steam ID' for CS2, 'UID' for PUBG Mobile). "
                    "Leave blank to use the default 'Game ID'."
                ),
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name='game',
            name='game_id_placeholder',
            field=models.CharField(
                blank=True,
                default='',
                help_text=(
                    "Placeholder text shown in the Game ID input field "
                    "(e.g. 'Username#TAG'). Leave blank for a generic placeholder."
                ),
                max_length=100,
            ),
        ),
    ]
