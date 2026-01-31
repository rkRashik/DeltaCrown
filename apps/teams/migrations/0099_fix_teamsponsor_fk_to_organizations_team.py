# Generated migration to fix TeamSponsor FK reference
# Gate 5: Schema Cleanup - Fix FK mismatch (teams.Team → organizations.Team)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0002_initial'),  # Latest teams migration
        ('organizations', '0003_add_team_invite_model'),  # Ensure organizations.Team exists
    ]

    operations = [
        migrations.AlterField(
            model_name='teamsponsor',
            name='team',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='sponsors',
                to='organizations.team',
                help_text='Team receiving sponsorship (organizations.Team)'
            ),
        ),
    ]
