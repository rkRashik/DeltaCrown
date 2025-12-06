# Generated migration for Phase 2 - Remove captain ForeignKey
# Captain is now determined by OWNER role in TeamMembership

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0015_alter_team_game'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='team',
            name='captain',
        ),
    ]
