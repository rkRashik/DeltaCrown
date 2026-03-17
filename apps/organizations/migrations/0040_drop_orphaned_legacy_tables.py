"""
DDL Migration: Drop six orphaned legacy tables that were left behind when
apps/teams/ was deleted.  No Django models reference these tables.

Order matters:
  1. Drop FK constraints on the orphaned tables first (they reference teams_team)
  2. Drop the orphaned tables themselves
  3. Drop teams_team (now safe — no remaining FK constraints reference it)

After this migration, teams_team no longer exists in the database.

Rollback note: reverse_sql re-creates the bare table shells and FK constraints
so the DB is at least structurally consistent after a failed forward migration.
It does NOT restore data (the data in these tables was legacy/dead anyway).

Part of TASK-015: Remove legacy teams app.
"""
from django.db import migrations

# Orphaned tables in order: dependents before parent (teams_team)
ORPHANED = [
    # (table, fk_constraint_to_drop)
    ("teams_teaminvite",       "teams_teaminvite_team_id_90e95e62_fk_teams_team_id"),
    ("teams_teamjoinrequest",  "teams_teamjoinrequest_team_id_46894ca3_fk_teams_team_id"),
    ("teams_teammembership",   "teams_teammembership_team_id_2ee7a456_fk_teams_team_id"),
    ("teams_ranking_breakdown","teams_ranking_breakdown_team_id_b69a1d1e_fk_teams_team_id"),
    ("teams_ranking_history",  "teams_ranking_history_team_id_29fdcebb_fk_teams_team_id"),
    ("teams_teamgameranking",  "teams_teamgameranking_team_id_1e516a10_fk_teams_team_id"),
]

FORWARD_SQL = (
    # DROP TABLE IF EXISTS ... CASCADE handles both:
    # - dropping the orphaned table itself
    # - dropping any FK constraints on that table (including the ones to teams_team)
    # Safe on fresh DBs (tables may never have existed) and on production DB alike.
    "\n".join(
        f"DROP TABLE IF EXISTS {t} CASCADE;"
        for t, _ in ORPHANED
    )
    + "\n\n"
    # Drop teams_team last — by now all tables with FKs referencing it have been
    # dropped above, and migrations 0039/0005/0036 retargeted the remaining FKs
    # to organizations_team.
    + "DROP TABLE IF EXISTS teams_team CASCADE;\n"
)

# Minimal reverse: re-create empty table shells without data.
# teams_team needs enough columns to satisfy FK re-creation.
REVERSE_SQL = """
-- Restore teams_team skeleton (no data)
CREATE TABLE IF NOT EXISTS teams_team (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Restore orphaned table skeletons (no data)
CREATE TABLE IF NOT EXISTS teams_teaminvite (
    id      SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams_team (id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS teams_teamjoinrequest (
    id      SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams_team (id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS teams_teammembership (
    id      SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams_team (id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS teams_ranking_breakdown (
    id      SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams_team (id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS teams_ranking_history (
    id      SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams_team (id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TABLE IF NOT EXISTS teams_teamgameranking (
    id      SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams_team (id) DEFERRABLE INITIALLY DEFERRED
);
"""


class Migration(migrations.Migration):

    dependencies = [
        # Ranking FK must already point to organizations_team before teams_team drop
        ("organizations", "0039_ddl_retarget_ranking_fk"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
