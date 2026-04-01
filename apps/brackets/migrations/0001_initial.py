"""
Phase 6 — Migrate Bracket and BracketNode from tournaments app to brackets.

Uses SeparateDatabaseAndState: the database tables already exist and keep
their names.  Only Django's internal state changes.
"""

import django.contrib.postgres.indexes
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tournaments", "0047_matchmapplayerstat_damage_dealt_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="Bracket",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("created_at", models.DateTimeField(auto_now_add=True, help_text="Timestamp when this record was created")),
                        ("format", models.CharField(choices=[("single-elimination", "Single Elimination"), ("double-elimination", "Double Elimination"), ("round-robin", "Round Robin"), ("swiss", "Swiss System"), ("group-stage", "Group Stage")], default="single-elimination", help_text="Type of bracket structure", max_length=50, verbose_name="Bracket Format")),
                        ("total_rounds", models.PositiveIntegerField(default=0, help_text="Total number of rounds in bracket", verbose_name="Total Rounds")),
                        ("total_matches", models.PositiveIntegerField(default=0, help_text="Total number of matches in bracket", verbose_name="Total Matches")),
                        ("bracket_structure", models.JSONField(blank=True, default=dict, help_text="JSONB tree structure metadata for bracket visualization", verbose_name="Bracket Structure")),
                        ("seeding_method", models.CharField(choices=[("slot-order", "Slot Order (First-Come-First-Served)"), ("random", "Random Seeding"), ("ranked", "Ranked Seeding"), ("manual", "Manual Seeding")], default="slot-order", help_text="How participants are seeded into bracket", max_length=30, verbose_name="Seeding Method")),
                        ("is_finalized", models.BooleanField(default=False, help_text="Whether bracket is locked and cannot be regenerated", verbose_name="Is Finalized")),
                        ("generated_at", models.DateTimeField(auto_now_add=True, blank=True, help_text="When bracket was initially generated", null=True, verbose_name="Generated At")),
                        ("updated_at", models.DateTimeField(auto_now=True, help_text="Last update timestamp", verbose_name="Updated At")),
                        ("tournament", models.OneToOneField(help_text="Tournament this bracket belongs to", on_delete=django.db.models.deletion.CASCADE, related_name="bracket", to="tournaments.tournament", verbose_name="Tournament")),
                    ],
                    options={
                        "verbose_name": "Bracket",
                        "verbose_name_plural": "Brackets",
                        "db_table": "tournament_engine_bracket_bracket",
                        "indexes": [
                            models.Index(fields=["tournament"], name="idx_bracket_tournament"),
                            models.Index(fields=["format"], name="idx_bracket_format"),
                            django.contrib.postgres.indexes.GinIndex(fields=["bracket_structure"], name="idx_bracket_structure_gin"),
                        ],
                    },
                ),
                migrations.CreateModel(
                    name="BracketNode",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("is_deleted", models.BooleanField(db_index=True, default=False, help_text="Flag indicating if this record has been soft-deleted")),
                        ("deleted_at", models.DateTimeField(blank=True, help_text="Timestamp when this record was deleted", null=True)),
                        ("deleted_by", models.ForeignKey(blank=True, help_text="User who deleted this record", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="%(class)s_deletions", to=settings.AUTH_USER_MODEL)),
                        ("position", models.PositiveIntegerField(help_text="Sequential position in bracket (1-indexed)", verbose_name="Position")),
                        ("round_number", models.PositiveIntegerField(help_text="Round number (1 = first round)", verbose_name="Round Number")),
                        ("match_number_in_round", models.PositiveIntegerField(help_text="Match number within this round (1-indexed)", verbose_name="Match Number in Round")),
                        ("participant1_id", models.IntegerField(blank=True, null=True, verbose_name="Participant 1 ID")),
                        ("participant1_name", models.CharField(blank=True, max_length=100, verbose_name="Participant 1 Name")),
                        ("participant2_id", models.IntegerField(blank=True, null=True, verbose_name="Participant 2 ID")),
                        ("participant2_name", models.CharField(blank=True, max_length=100, verbose_name="Participant 2 Name")),
                        ("winner_id", models.IntegerField(blank=True, null=True, verbose_name="Winner ID")),
                        ("parent_slot", models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Parent Slot")),
                        ("is_bye", models.BooleanField(default=False, verbose_name="Is Bye")),
                        ("bracket_type", models.CharField(default="main", max_length=50, verbose_name="Bracket Type")),
                        ("bracket", models.ForeignKey(help_text="Bracket this node belongs to", on_delete=django.db.models.deletion.CASCADE, related_name="nodes", to="brackets.bracket", verbose_name="Bracket")),
                        ("child1_node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="brackets.bracketnode", verbose_name="Child 1 Node")),
                        ("child2_node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="brackets.bracketnode", verbose_name="Child 2 Node")),
                        ("match", models.OneToOneField(blank=True, help_text="Associated match for this bracket position", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="bracket_node", to="tournaments.match", verbose_name="Match")),
                        ("parent_node", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="children", to="brackets.bracketnode", verbose_name="Parent Node")),
                    ],
                    options={
                        "verbose_name": "Bracket Node",
                        "verbose_name_plural": "Bracket Nodes",
                        "db_table": "tournament_engine_bracket_bracketnode",
                        "indexes": [
                            models.Index(fields=["bracket"], name="idx_bracketnode_bracket"),
                            models.Index(fields=["bracket", "round_number"], name="idx_bracketnode_round"),
                            models.Index(fields=["position"], name="idx_bracketnode_position"),
                            models.Index(fields=["match"], name="idx_bracketnode_match"),
                            models.Index(fields=["parent_node"], name="idx_bracketnode_parent"),
                            models.Index(fields=["bracket", "child1_node", "child2_node"], name="idx_bracketnode_children"),
                            models.Index(fields=["participant1_id", "participant2_id"], name="idx_bracketnode_participants"),
                        ],
                        "constraints": [
                            models.UniqueConstraint(fields=["bracket", "position"], name="uq_bracketnode_bracket_position"),
                            models.CheckConstraint(condition=models.Q(round_number__gt=0), name="chk_bracketnode_round_positive"),
                            models.CheckConstraint(condition=models.Q(match_number_in_round__gt=0), name="chk_bracketnode_match_number_positive"),
                            models.CheckConstraint(condition=models.Q(parent_slot__isnull=True) | models.Q(parent_slot__in=[1, 2]), name="chk_bracketnode_parent_slot"),
                        ],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
