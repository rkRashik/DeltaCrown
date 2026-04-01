"""
Phase 6 — Migrate GameMatchPipeline from games app to match_engine.

Uses SeparateDatabaseAndState: the database table (games_match_pipeline)
already exists and keeps its name.  Only Django's internal state changes.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("games", "0005_gamematchpipeline_archetype_vetoconfiguration"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="GameMatchPipeline",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "archetype",
                            models.CharField(
                                blank=True,
                                choices=[
                                    ("tactical_fps", "Tactical FPS"),
                                    ("moba", "MOBA"),
                                    ("battle_royale", "Battle Royale"),
                                    ("sports", "Sports"),
                                    ("duel_1v1", "1v1 / Duel"),
                                ],
                                default="",
                                help_text="Game archetype \u2014 auto-resolved from game if blank.",
                                max_length=30,
                            ),
                        ),
                        (
                            "phases",
                            models.JSONField(
                                default=list,
                                help_text=(
                                    'Ordered list of phase keys the match room will execute. '
                                    'Example: ["direct_ready", "lobby_setup", "live", "results", "completed"]'
                                ),
                            ),
                        ),
                        (
                            "require_coin_toss",
                            models.BooleanField(
                                default=False,
                                help_text="Pre-pend coin_toss phase even if not in phases list.",
                            ),
                        ),
                        (
                            "require_map_veto",
                            models.BooleanField(
                                default=False,
                                help_text="Use map_veto instead of direct_ready for phase1.",
                            ),
                        ),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        (
                            "game",
                            models.OneToOneField(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="match_pipeline",
                                to="games.game",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "Game Match Pipeline",
                        "verbose_name_plural": "Game Match Pipelines",
                        "db_table": "games_match_pipeline",
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
