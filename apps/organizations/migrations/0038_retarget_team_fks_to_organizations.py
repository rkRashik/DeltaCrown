"""
Re-target team FK fields from teams.Team to organizations.Team in the
organizations app's migration state.

Part of TASK-015: Remove legacy teams app.

migrations/0010 left four AlterField operations and TeamAdminProxy still pointing
at teams.Team in the Django state. This uses SeparateDatabaseAndState to correct
the state — no ALTER TABLE is needed because the DB columns already hold valid
organizations.Team IDs.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0037_add_team_follower"),
    ]

    operations = [
        # -- TeamRanking.team (OneToOneField, primary_key) --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teamranking",
                    name="team",
                    field=models.OneToOneField(
                        help_text="Team this ranking belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        primary_key=True,
                        related_name="ranking",
                        serialize=False,
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamInvite.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teaminvite",
                    name="team",
                    field=models.ForeignKey(
                        help_text="Team extending invitation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vnext_invites",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamMembership.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teammembership",
                    name="team",
                    field=models.ForeignKey(
                        help_text="Team this membership belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="vnext_memberships",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamActivityLog.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teamactivitylog",
                    name="team",
                    field=models.ForeignKey(
                        help_text="Team this activity belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity_logs",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamAdminProxy bases --
        # Created in 0011 with bases=("teams.team",). Delete and recreate
        # state-only with the correct base. No DDL needed (proxy models
        # have no table).
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="TeamAdminProxy"),
                migrations.CreateModel(
                    name="TeamAdminProxy",
                    fields=[],
                    options={
                        "verbose_name": "Team",
                        "verbose_name_plural": "Teams",
                        "proxy": True,
                        "indexes": [],
                        "constraints": [],
                    },
                    bases=("organizations.team",),
                ),
            ],
            database_operations=[],
        ),
    ]
