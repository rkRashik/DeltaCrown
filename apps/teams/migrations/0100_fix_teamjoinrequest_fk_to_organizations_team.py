# Generated migration to fix TeamJoinRequest FK reference
# Gate 5: Schema Cleanup - Fix FK mismatch (teams.Team → organizations.Team)

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0099_fix_teamsponsor_fk_to_organizations_team'),
        ('organizations', '0009_fix_teaminvite_fk_reference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='teamjoinrequest',
            name='team',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='join_requests',
                to='organizations.team',
                help_text='Team receiving join request (organizations.Team)'
            ),
        ),
    ]
