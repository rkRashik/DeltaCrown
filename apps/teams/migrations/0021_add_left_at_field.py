# Generated manually for Phase 4F
# Date: 2026-01-10
# Purpose: Add left_at field to TeamMembership for accurate career timeline tracking

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0020_teammembership_is_role_custom_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='teammembership',
            name='left_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When the member left or was removed from the team'
            ),
        ),
        # Add index for efficient timeline queries
        migrations.AddIndex(
            model_name='teammembership',
            index=models.Index(fields=['profile', 'left_at'], name='teams_member_left_at_idx'),
        ),
    ]
