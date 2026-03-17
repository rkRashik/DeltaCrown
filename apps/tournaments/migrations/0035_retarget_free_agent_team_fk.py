"""
Re-target FreeAgentDraftPick.assigned_to_team from teams.Team to organizations.Team.

Part of TASK-015: Remove legacy teams app.

Uses SeparateDatabaseAndState — the integer column already stores valid
organization team IDs; no ALTER TABLE needed.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0034_matchresultsubmission_ingested_at_and_more"),
        ("organizations", "0037_add_team_follower"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="freeagentregistration",
                    name="assigned_to_team",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="free_agent_assignments",
                        to="organizations.team",
                        help_text="Team the FA was assigned to.",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
