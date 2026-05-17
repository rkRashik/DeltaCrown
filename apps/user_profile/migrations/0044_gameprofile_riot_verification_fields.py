"""
Add Riot API verification tracking fields to GameProfile.

New fields:
  - verification_error: short reason for failed/unavailable state
  - last_verification_attempt_at: timestamp of most recent API call
  - verification_attempt_count: total attempts (for retry throttling)

The new verification_status choices (FAILED, API_UNAVAILABLE, RATE_LIMITED)
are additive — Django does not enforce choices at the DB level, so no ALTER
TABLE is needed for them. The field already stores CharField(max_length=20).

PUUID is stored in provider_data['riot']['puuid'] (existing JSON field) to
avoid an extra column.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0043_bounty_deleted_at_bounty_deleted_by_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="gameprofile",
            name="verification_error",
            field=models.CharField(
                max_length=300,
                blank=True,
                default="",
                help_text=(
                    "Short error reason for failed/unavailable verification. "
                    "Never expose raw API errors here; store user-safe copy."
                ),
            ),
        ),
        migrations.AddField(
            model_name="gameprofile",
            name="last_verification_attempt_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text="Timestamp of the most recent Riot API verification attempt.",
            ),
        ),
        migrations.AddField(
            model_name="gameprofile",
            name="verification_attempt_count",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Cumulative verification attempts (for retry throttling and admin triage).",
            ),
        ),
    ]
