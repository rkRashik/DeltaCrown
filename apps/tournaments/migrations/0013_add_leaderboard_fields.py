# Milestone E: Leaderboard Fields Migration
# Generated manually on 2025-11-13

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0012_payments_api_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Staff Override Support
        migrations.AddField(
            model_name='tournamentresult',
            name='is_override',
            field=models.BooleanField(
                default=False,
                help_text='Whether this placement was manually overridden by staff'
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='override_reason',
            field=models.TextField(
                blank=True,
                help_text='Reason for manual override (required if is_override=True)'
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='override_actor',
            field=models.ForeignKey(
                blank=True,
                help_text='Staff member who performed the override',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tournament_result_overrides',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='override_timestamp',
            field=models.DateTimeField(
                blank=True,
                help_text='When the override was applied',
                null=True
            ),
        ),
        
        # BR-specific metadata
        migrations.AddField(
            model_name='tournamentresult',
            name='total_kills',
            field=models.IntegerField(
                default=0,
                help_text='Total kills across all matches (BR games)'
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='best_placement',
            field=models.IntegerField(
                blank=True,
                help_text='Best placement achieved (BR games, 1=1st place)',
                null=True
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='avg_placement',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Average placement (BR games)',
                max_digits=5,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='matches_played',
            field=models.IntegerField(
                default=0,
                help_text='Number of matches played'
            ),
        ),
        
        # Series metadata
        migrations.AddField(
            model_name='tournamentresult',
            name='series_score',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Series score breakdown. Example: {"team-123": 2, "team-456": 1} for Best-of-3'
            ),
        ),
        migrations.AddField(
            model_name='tournamentresult',
            name='game_results',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Individual game results in series. Example: [{"match_id": 1, "winner_id": "team-123", "score": {...}}, ...]'
            ),
        ),
    ]
