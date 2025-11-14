# Module 2.3: Tournament Templates System
# Generated manually on 2025-11-14

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0013_add_leaderboard_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TournamentTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this record was last updated')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='Soft delete flag')),
                ('deleted_at', models.DateTimeField(blank=True, help_text='When this record was soft deleted', null=True)),
                ('name', models.CharField(help_text='Template name (e.g., "5v5 Valorant Tournament")', max_length=200)),
                ('slug', models.SlugField(db_index=True, help_text='URL-friendly slug (auto-generated from name)', max_length=250, unique=True)),
                ('description', models.TextField(blank=True, help_text='Template description and notes')),
                ('visibility', models.CharField(choices=[('private', 'Private (Creator Only)'), ('org', 'Organization'), ('global', 'Global (Public)')], db_index=True, default='private', help_text='Who can see and use this template', max_length=20)),
                ('organization_id', models.PositiveIntegerField(blank=True, db_index=True, help_text='Organization ID from DeltaCrown organizations app (no ForeignKey)', null=True)),
                ('template_config', models.JSONField(default=dict, help_text='Tournament configuration template (JSONB).')),
                ('usage_count', models.PositiveIntegerField(default=0, help_text='Number of times this template has been applied')),
                ('last_used_at', models.DateTimeField(blank=True, help_text='When this template was last used', null=True)),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Whether this template is active (can be used)')),
                ('created_by', models.ForeignKey(help_text='User who created this template', on_delete=django.db.models.deletion.CASCADE, related_name='tournament_templates', to=settings.AUTH_USER_MODEL)),
                ('deleted_by', models.ForeignKey(blank=True, help_text='User who soft deleted this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('game', models.ForeignKey(blank=True, help_text='Game for this template (null = multi-game)', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='templates', to='tournaments.game')),
            ],
            options={
                'verbose_name': 'Tournament Template',
                'verbose_name_plural': 'Tournament Templates',
                'db_table': 'tournaments_tournamenttemplate',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='tournamenttemplate',
            index=models.Index(fields=['created_by', 'is_active'], name='template_creator_active_idx'),
        ),
        migrations.AddIndex(
            model_name='tournamenttemplate',
            index=models.Index(fields=['game', 'visibility'], name='template_game_visibility_idx'),
        ),
        migrations.AddIndex(
            model_name='tournamenttemplate',
            index=models.Index(fields=['visibility', 'is_active'], name='template_visibility_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='tournamenttemplate',
            constraint=models.UniqueConstraint(condition=models.Q(('is_deleted', False)), fields=('created_by', 'game', 'name'), name='unique_template_per_creator_game_name'),
        ),
    ]
