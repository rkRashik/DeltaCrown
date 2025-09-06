# Generated for Part A
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('teams', '0003_alter_team_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='game',
            field=models.CharField(
                choices=[('efootball', 'eFootball'), ('valorant', 'Valorant')],
                default='', blank=True, max_length=20,
                help_text='Which game this team competes in (blank for legacy teams).',
            ),
        ),
    ]
