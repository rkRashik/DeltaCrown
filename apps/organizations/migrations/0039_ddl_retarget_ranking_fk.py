"""
DDL Migration: Retarget organizations_ranking FK constraint from
teams_team → organizations_team.

organizations_ranking.team_id is a OneToOneField acting as primary key.
ON DELETE CASCADE is correct (ranking row is deleted when team is deleted).

Part of TASK-015: Remove legacy teams app.
"""
from django.db import migrations

OLD_CONSTRAINT = "organizations_ranking_team_id_c5c6886e_fk_teams_team_id"
NEW_CONSTRAINT = "organizations_ranking_team_id_fk_org_team"
TABLE = "organizations_ranking"
COL = "team_id"


FORWARD_SQL = f"""
ALTER TABLE {TABLE}
    ADD CONSTRAINT {NEW_CONSTRAINT}
    FOREIGN KEY ({COL}) REFERENCES organizations_team (id)
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
    NOT VALID;

ALTER TABLE {TABLE} VALIDATE CONSTRAINT {NEW_CONSTRAINT};

ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS {OLD_CONSTRAINT};
"""

REVERSE_SQL = f"""
ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS {NEW_CONSTRAINT};

ALTER TABLE {TABLE}
    ADD CONSTRAINT {OLD_CONSTRAINT}
    FOREIGN KEY ({COL}) REFERENCES teams_team (id)
    ON DELETE CASCADE
    DEFERRABLE INITIALLY DEFERRED
    NOT VALID;
"""


class Migration(migrations.Migration):

    dependencies = [
        # State-only retarget (organizations/0038) must precede this DDL step
        ("organizations", "0038_retarget_team_fks_to_organizations"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
