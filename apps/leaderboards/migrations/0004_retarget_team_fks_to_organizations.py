"""
Re-target all team ForeignKey fields from teams.Team to organizations.Team.

Part of TASK-015: Remove legacy teams app.

This uses SeparateDatabaseAndState so that Django's migration framework
updates its internal FK tracking WITHOUT running ALTER TABLE (the integer
columns already contain valid organization team IDs via TeamMigrationMap
dual-write, and both tables use integer PKs).

Removes the migration dependency on the teams app.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("leaderboards", "0003_initial"),
        ("organizations", "0037_add_team_follower"),
    ]

    operations = [
        # -- LeaderboardEntry.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="leaderboardentry",
                    name="team",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leaderboard_entries",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- LeaderboardSnapshot.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="leaderboardsnapshot",
                    name="team",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="leaderboard_snapshots",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamStats.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teamstats",
                    name="team",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="team_stats",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamRanking.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teamranking",
                    name="team",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="team_rankings",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamMatchHistory.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teammatchhistory",
                    name="team",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="match_history",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # -- TeamAnalyticsSnapshot.team --
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="teamanalyticssnapshot",
                    name="team",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analytics_snapshots",
                        to="organizations.team",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
