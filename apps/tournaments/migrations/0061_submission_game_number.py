"""
Additive migration — game_number on MatchResultSubmission.

Allows per-game evidence tracking in BO3/BO5 series. Null for BO1 matches.
When a participant submits result evidence in a BO3+ workflow the handler
sets this field to the current game being played (len(game_scores) + 1
before the game is recorded). Existing rows default to null and continue
to work without change (BO1 behaviour preserved).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0060_match_submission_ocr_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="matchresultsubmission",
            name="game_number",
            field=models.PositiveSmallIntegerField(
                null=True,
                blank=True,
                db_index=True,
                help_text=(
                    "1-indexed game in a BO3/BO5 series (null for BO1). "
                    "Used to group per-game evidence in the Evidence tab."
                ),
            ),
        ),
    ]
