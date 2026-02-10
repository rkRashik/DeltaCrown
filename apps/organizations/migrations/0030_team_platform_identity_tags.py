"""
Migration: Add platform and identity tag fields to Team model.

Fields added:
  - platform: Primary gaming platform (PC/Console/Mobile/Cross-Platform)
  - playstyle: Team play style tag (e.g., 'Aggressive', 'Methodical')
  - playpace: Team pace tag (e.g., 'Fast Execute', 'Slow Default')
  - playfocus: Team focus tag (e.g., 'Aim-Heavy', 'Strategy-First')
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0029_team_recruiting_join_requests"),
    ]

    operations = [
        migrations.AddField(
            model_name="team",
            name="platform",
            field=models.CharField(
                blank=True,
                default="PC",
                help_text="Primary platform: PC, Console, Mobile, Cross-Platform",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="playstyle",
            field=models.CharField(
                blank=True,
                help_text="Team play style tag (e.g., 'Aggressive', 'Methodical', 'Adaptive')",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="playpace",
            field=models.CharField(
                blank=True,
                help_text="Team pace tag (e.g., 'Fast Execute', 'Slow Default', 'Mixed')",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="team",
            name="playfocus",
            field=models.CharField(
                blank=True,
                help_text="Team focus tag (e.g., 'Aim-Heavy', 'Strategy-First', 'Utility-Rich')",
                max_length=50,
            ),
        ),
    ]
