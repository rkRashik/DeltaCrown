"""
Drop stale FK constraint on GroupStanding.team_id.

The Django model defines team_id as IntegerField (not ForeignKey),
but the database still has a FK constraint from an older model version.
This migration drops the stale constraint so team_id can hold any integer value.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0022_fix_tournament_field_defaults'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE "tournament_group_standings" DROP CONSTRAINT IF EXISTS "tournament_group_standings_team_id_45cc0005_fk_teams_team_id";',
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
