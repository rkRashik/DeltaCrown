from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0055_add_organizer_access_expires_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="prizeclaim",
            name="claim_details",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="Structured payout and courier details submitted by the claimant",
            ),
        ),
        migrations.AlterField(
            model_name="prizeclaim",
            name="payout_method",
            field=models.CharField(
                choices=[
                    ("deltacoin", "DeltaCoin Wallet"),
                    ("bkash", "bKash"),
                    ("nagad", "Nagad"),
                    ("rocket", "Rocket"),
                    ("bank", "Bank Transfer"),
                    ("other", "Other"),
                ],
                default="deltacoin",
                help_text="Chosen payout method",
                max_length=20,
            ),
        ),
    ]
