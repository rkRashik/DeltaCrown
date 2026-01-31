# Generated migration to fix TeamInvite FK reference
# Gate 5: Schema Cleanup - Ensure TeamInvite.team explicitly points to organizations.Team

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0008_add_team_social_fields'),
    ]

    operations = [
        # Make TeamInvite.team FK reference explicit
        migrations.AlterField(
            model_name='teaminvite',
            name='team',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='invites',
                to='organizations.team',
                help_text='Team extending the invitation (organizations.Team)'
            ),
        ),
    ]
