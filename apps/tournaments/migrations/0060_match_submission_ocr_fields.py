"""
Additive migration — add OCR status fields to MatchResultSubmission so
participant-uploaded screenshots can be auto-processed and the extraction
results stored alongside the original submission.

Fields added:
  ocr_status        — pipeline state (none / pending / running / completed / failed / skipped)
  ocr_extracted     — JSON of extracted data (game-specific structure)
  ocr_confidence    — float 0..1 (overall confidence; null when not run)
  ocr_error         — short error message when status=failed
  ocr_processed_at  — timestamp of last OCR run (success or failure)

All fields are nullable / have safe defaults so existing rows are unaffected.
"""

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0059_prize_claim_playbook_compliance_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="matchresultsubmission",
            name="ocr_status",
            field=models.CharField(
                max_length=20,
                blank=True,
                default="",
                db_index=True,
                help_text=(
                    "OCR pipeline state: '' (not attempted), 'pending', "
                    "'running', 'completed', 'failed', 'skipped'."
                ),
            ),
        ),
        migrations.AddField(
            model_name="matchresultsubmission",
            name="ocr_extracted",
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text=(
                    "Game-specific extracted data (score / KDA / agents / etc.). "
                    "Empty dict when no extraction has been run."
                ),
            ),
        ),
        migrations.AddField(
            model_name="matchresultsubmission",
            name="ocr_confidence",
            field=models.FloatField(
                null=True,
                blank=True,
                help_text=(
                    "Overall extraction confidence 0..1. Null when not run "
                    "or when the OCR provider doesn't report confidence."
                ),
            ),
        ),
        migrations.AddField(
            model_name="matchresultsubmission",
            name="ocr_error",
            field=models.CharField(
                max_length=500,
                blank=True,
                default="",
                help_text="Short error message when ocr_status='failed'.",
            ),
        ),
        migrations.AddField(
            model_name="matchresultsubmission",
            name="ocr_processed_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Timestamp of the most recent OCR pipeline run.",
            ),
        ),
    ]
