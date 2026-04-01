"""
Phase 6 — Remove Bracket and BracketNode from tournaments app state.

Models now live in apps.brackets.  The underlying database tables are
untouched — only Django's internal state changes.

Also updates Match.bracket FK to point to brackets.Bracket.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0047_matchmapplayerstat_damage_dealt_and_more"),
        ("brackets", "0001_initial"),
    ]

    operations = [
        # 1) Update Match.bracket FK from tournaments.Bracket → brackets.Bracket
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name="match",
                    name="bracket",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="Bracket this match belongs to (null for group stage)",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="matches",
                        to="brackets.bracket",
                        verbose_name="Bracket",
                    ),
                ),
                migrations.AlterField(
                    model_name="tournamentresult",
                    name="final_bracket",
                    field=models.ForeignKey(
                        blank=True,
                        help_text="Bracket used for determination",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="brackets.bracket",
                    ),
                ),
            ],
            database_operations=[],
        ),
        # 2) Remove Bracket and BracketNode from tournaments state
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="BracketNode"),
                migrations.DeleteModel(name="Bracket"),
            ],
            database_operations=[],
        ),
    ]
