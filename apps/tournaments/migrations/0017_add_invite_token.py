"""
Migration: Add invite_token field to Registration for guest-to-real team conversion.
P4-T04: Guest-to-Real Team Conversion
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0016_copy_verification_data_to_payment'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='invite_token',
            field=models.CharField(
                max_length=64,
                null=True,
                blank=True,
                unique=True,
                db_index=True,
                help_text='Unique token for guest team invite link (P4-T04)',
            ),
        ),
        migrations.AddField(
            model_name='registration',
            name='conversion_status',
            field=models.CharField(
                max_length=20,
                null=True,
                blank=True,
                choices=[
                    ('pending', 'Pending'),
                    ('partial', 'Partial'),
                    ('complete', 'Complete'),
                    ('approved', 'Approved'),
                ],
                help_text='Guest-to-real conversion progress status',
            ),
        ),
    ]
