"""
Add fourth_place ForeignKey and final_standings JSONField to TournamentResult.

Used by the placement engine to record up to 4th-place plus a full ordered
standings list for prize distribution and public display.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0053_matchcenterconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournamentresult',
            name='fourth_place',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='fourth_place_tournaments',
                to='tournaments.registration',
                help_text='Fourth place participant (if derivable from bracket)',
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='final_standings',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    'Ordered list of all derivable placements (1..N). '
                    'Each entry includes placement, registration_id, derivation source, '
                    'optional team_name snapshot, and tie metadata.'
                ),
            ),
        ),
    ]
