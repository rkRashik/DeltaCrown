"""
DDL Migration: Retarget 6 leaderboard FK constraints from teams_team → organizations_team.

All six constraints are DEFERRABLE INITIALLY DEFERRED and convalidated=True,
so no data scan is needed. The NOT VALID / VALIDATE pattern is used to avoid
an ACCESS EXCLUSIVE lock on large tables:
  1. ADD CONSTRAINT ... NOT VALID  — instant, acquires only SHARE ROW EXCLUSIVE
  2. VALIDATE CONSTRAINT           — scans existing rows with a weaker lock
  3. DROP old constraint           — removes the stale reference to teams_team

Rollback (reverse_sql) restores the original constraints so a failed deploy can be
safely reverted with migrate --reverse.

Part of TASK-015: Remove legacy teams app.
"""
from django.db import migrations


# ---------------------------------------------------------------------------
# Helpers: table / old constraint / new constraint / column / on_delete
# ---------------------------------------------------------------------------
LEADERBOARD_TABLES = [
    # (table, old_constraint, new_constraint, column, on_delete_clause)
    (
        "leaderboards_leaderboardentry",
        "leaderboards_leaderboardentry_team_id_b8ddce8e_fk_teams_team_id",
        "leaderboards_leaderboardentry_team_id_fk_org_team",
        "team_id",
        "CASCADE",
    ),
    (
        "leaderboards_leaderboardsnapshot",
        "leaderboards_leaderb_team_id_1a63695c_fk_teams_tea",
        "leaderboards_leaderboardsnapshot_team_id_fk_org_team",
        "team_id",
        "CASCADE",
    ),
    (
        "leaderboards_teamanalyticssnapshot",
        "leaderboards_teamana_team_id_2ba1ed75_fk_teams_tea",
        "leaderboards_teamanalyticssnapshot_team_id_fk_org_team",
        "team_id",
        "CASCADE",
    ),
    (
        "leaderboards_teammatchhistory",
        "leaderboards_teammatchhistory_team_id_d44e42b0_fk_teams_team_id",
        "leaderboards_teammatchhistory_team_id_fk_org_team",
        "team_id",
        "CASCADE",
    ),
    (
        "leaderboards_teamranking",
        "leaderboards_teamranking_team_id_bae42cd1_fk_teams_team_id",
        "leaderboards_teamranking_team_id_fk_org_team",
        "team_id",
        "CASCADE",
    ),
    (
        "leaderboards_teamstats",
        "leaderboards_teamstats_team_id_0432e2c6_fk_teams_team_id",
        "leaderboards_teamstats_team_id_fk_org_team",
        "team_id",
        "CASCADE",
    ),
]


def _forward_sql():
    stmts = []
    for table, old_con, new_con, col, on_delete in LEADERBOARD_TABLES:
        # Step 1: Add new constraint without scanning existing rows (no long lock)
        stmts.append(
            f"ALTER TABLE {table}"
            f" ADD CONSTRAINT {new_con}"
            f" FOREIGN KEY ({col}) REFERENCES organizations_team (id)"
            f" ON DELETE {on_delete}"
            f" DEFERRABLE INITIALLY DEFERRED"
            f" NOT VALID;"
        )
        # Step 2: Validate existing rows (uses lighter lock than EXCLUSIVE)
        stmts.append(
            f"ALTER TABLE {table} VALIDATE CONSTRAINT {new_con};"
        )
        # Step 3: Drop the old stale constraint
        stmts.append(
            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {old_con};"
        )
    return "\n".join(stmts)


def _reverse_sql():
    """Restore original teams_team FK constraints so rollback is safe."""
    stmts = []
    for table, old_con, new_con, col, on_delete in LEADERBOARD_TABLES:
        # Drop the new constraint first
        stmts.append(
            f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {new_con};"
        )
        # Re-add the original constraint pointing back to teams_team
        stmts.append(
            f"ALTER TABLE {table}"
            f" ADD CONSTRAINT {old_con}"
            f" FOREIGN KEY ({col}) REFERENCES teams_team (id)"
            f" ON DELETE {on_delete}"
            f" DEFERRABLE INITIALLY DEFERRED"
            f" NOT VALID;"
        )
    return "\n".join(stmts)


class Migration(migrations.Migration):

    dependencies = [
        # State-only retarget already applied; this adds the DDL layer
        ("leaderboards", "0004_retarget_team_fks_to_organizations"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_forward_sql(),
            reverse_sql=_reverse_sql(),
        ),
    ]
