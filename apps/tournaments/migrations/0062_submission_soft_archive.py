"""
Additive migration — soft-archive fields on MatchResultSubmission.

Replaces hard-delete on match reset with a non-destructive archive. Archived
submissions are excluded from active result/OCR/comparison queries but remain
visible to admins under "Previous Attempt Evidence" in the Evidence tab. This
satisfies the product rule: participant-uploaded evidence must remain available
until tournament completion.

Fields added:
  is_archived    — False (active) or True (archived by reset/admin action).
  archived_at    — Timestamp when the submission was archived; null when active.
  archived_reason — Human-readable reason (e.g. "Match reset by admin (user_id=5)").

All fields are safe defaults so existing rows are unaffected.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0061_submission_game_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="matchresultsubmission",
            name="is_archived",
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text=(
                    "True when archived (e.g. by match reset). Excluded from active "
                    "queries; still visible in the Evidence tab audit section."
                ),
            ),
        ),
        migrations.AddField(
            model_name="matchresultsubmission",
            name="archived_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Timestamp when this submission was archived.",
            ),
        ),
        migrations.AddField(
            model_name="matchresultsubmission",
            name="archived_reason",
            field=models.CharField(
                max_length=300,
                blank=True,
                default="",
                help_text="Human-readable reason for archival.",
            ),
        ),
    ]
