"""
Phase 6 — Remove GameMatchPipeline from games app state.

The model now lives in apps.match_engine.  The underlying database table
(games_match_pipeline) is untouched — only Django's state is updated.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("games", "0005_gamematchpipeline_archetype_vetoconfiguration"),
        ("match_engine", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name="GameMatchPipeline"),
            ],
            database_operations=[],
        ),
    ]
