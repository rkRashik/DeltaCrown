"""
DDL Migration: Two operations for the tournaments app:

  A) Retarget tournaments_freeagentregistration.assigned_to_team_id
     from teams_team → organizations_team (active FK field).

  B) Drop stale FK constraints on five tables whose columns were
     converted to plain IntegerField by migration 0008_decouple_cross_app_fks.
     These constraints exist only at the DB level; Django state already has
     no FK for them. There is intentionally no reverse ADD CONSTRAINT for
     these five because the Django model has no FK—restoring the constraint
     on rollback would put Django's state and the DB out of sync.

Part of TASK-015: Remove legacy teams app.
"""
from django.db import migrations

# --- A: retarget ---
FREE_AGENT_TABLE = "tournaments_freeagentregistration"
FREE_AGENT_OLD = "tournaments_freeagen_assigned_to_team_id_f7325c62_fk_teams_tea"
FREE_AGENT_NEW = "tournaments_freeagentregistration_assigned_to_team_id_fk_org"
FREE_AGENT_COL = "assigned_to_team_id"

# --- B: drop-only (IntegerField columns, constraint is a relic) ---
DROP_ONLY = [
    ("tournament_check_ins",               "team_id",              "tournament_check_ins_team_id_4a4267ee_fk_teams_team_id"),
    ("tournaments_dispute_record",         "opened_by_team_id",    "tournaments_dispute__opened_by_team_id_68cd8587_fk_teams_tea"),
    ("tournaments_form_response",          "team_id",              "tournaments_form_response_team_id_d70837c6_fk_teams_team_id"),
    ("tournaments_match_result_submission","submitted_by_team_id", "tournaments_match_re_submitted_by_team_id_6ea8b98a_fk_teams_tea"),
    ("tournaments_tournamentteaminvitation","team_id",             "tournaments_tourname_team_id_3b73aa98_fk_teams_tea"),
]


def _forward():
    lines = []

    # A: retarget freeagentregistration
    lines += [
        f"ALTER TABLE {FREE_AGENT_TABLE}",
        f"    ADD CONSTRAINT {FREE_AGENT_NEW}",
        f"    FOREIGN KEY ({FREE_AGENT_COL}) REFERENCES organizations_team (id)",
        f"    ON DELETE SET NULL",
        f"    DEFERRABLE INITIALLY DEFERRED",
        f"    NOT VALID;",
        "",
        f"ALTER TABLE {FREE_AGENT_TABLE} VALIDATE CONSTRAINT {FREE_AGENT_NEW};",
        "",
        f"ALTER TABLE {FREE_AGENT_TABLE} DROP CONSTRAINT IF EXISTS {FREE_AGENT_OLD};",
        "",
    ]

    # B: drop stale IntegerField ghost constraints
    for table, _col, old_con in DROP_ONLY:
        lines.append(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {old_con};")

    return "\n".join(lines)


def _reverse():
    """
    Reverse only the freeagentregistration retarget (A).
    The five drop-only constraints (B) are NOT restored: those columns are
    IntegerField in Django, so re-adding a FK constraint would conflict with
    the Python model definition.
    """
    lines = [
        f"ALTER TABLE {FREE_AGENT_TABLE} DROP CONSTRAINT IF EXISTS {FREE_AGENT_NEW};",
        "",
        f"ALTER TABLE {FREE_AGENT_TABLE}",
        f"    ADD CONSTRAINT {FREE_AGENT_OLD}",
        f"    FOREIGN KEY ({FREE_AGENT_COL}) REFERENCES teams_team (id)",
        f"    ON DELETE SET NULL",
        f"    DEFERRABLE INITIALLY DEFERRED",
        f"    NOT VALID;",
    ]
    return "\n".join(lines)


class Migration(migrations.Migration):

    dependencies = [
        # State-only retarget for freeagentregistration
        ("tournaments", "0035_retarget_free_agent_team_fk"),
    ]

    operations = [
        migrations.RunSQL(
            sql=_forward(),
            reverse_sql=_reverse(),
        ),
    ]
