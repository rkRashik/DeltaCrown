# Generated manually on 2025-11-08 to fix circular dependency in 0001_initial
# This is a STATE-ONLY migration (no database changes)
# Purpose: Reorder model creation so Tournament is created before Bracket
# Issue: 0001_initial created Bracket before Tournament, then added Bracket.tournament FK via AddField
# Fix: State operations recreate models in correct order (Game → Tournament → Bracket)

from django.conf import settings
from django.db import migrations, models
import django.contrib.postgres.fields
import django.contrib.postgres.indexes
import django.core.validators
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):
    """
    State-only migration to fix model creation order.
    
    This migration does NOT modify the database schema (database_operations=[]).
    It only updates Django's migration state so test database creation works correctly.
    
    Background:
    - 0001_initial.py created Bracket before Tournament, then added Bracket.tournament FK via AddField
    - This creates circular dependency: Bracket references Tournament, but Tournament doesn't exist yet
    - pytest cannot build test database due to this ordering issue
    
    Solution:
    - state_operations: Recreate models in correct order (Game, Tournament, Bracket)
    - database_operations: Empty (no schema changes, production DB unchanged)
    - Migration graph now reflects correct dependency: Tournament must exist before Bracket
    """

    dependencies = [
        ('tournaments', '0002_add_payment_proof_file_upload'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    # State operations: Tell Django the "correct" order models were created
    state_operations = [
        # 1. Game (no dependencies except AUTH_USER_MODEL, already in dependencies)
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('icon', models.ImageField(help_text='Game icon/logo image', upload_to='games/icons/')),
                ('default_team_size', models.PositiveIntegerField(choices=[(1, '1v1'), (2, '2v2'), (3, '3v3'), (4, '4v4'), (5, '5v5'), (0, 'Variable')], default=5, help_text='Default team size for this game')),
                ('profile_id_field', models.CharField(help_text="Field name in UserProfile (e.g., 'riot_id', 'steam_id')", max_length=50)),
                ('default_result_type', models.CharField(choices=[('map_score', 'Map Score (e.g., 13-11)'), ('best_of', 'Best of X'), ('point_based', 'Point Based')], default='map_score', help_text='How match results are recorded', max_length=20)),
                ('is_active', models.BooleanField(db_index=True, default=True, help_text='Whether this game is actively supported')),
                ('description', models.TextField(blank=True, help_text='Game description and notes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Game',
                'verbose_name_plural': 'Games',
                'ordering': ['name'],
                'indexes': [models.Index(fields=['slug'], name='tournaments_slug_d1de23_idx'), models.Index(fields=['is_active', 'name'], name='tournaments_is_acti_b1f275_idx')],
            },
        ),
        
        # 2. Tournament (depends on Game, created BEFORE Bracket)
        migrations.CreateModel(
            name='Tournament',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='Flag indicating if this record has been soft-deleted')),
                ('deleted_at', models.DateTimeField(blank=True, help_text='Timestamp when this record was deleted', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when this record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Timestamp when this record was last updated')),
                ('name', models.CharField(help_text='Tournament name', max_length=200)),
                ('slug', models.SlugField(max_length=250, unique=True)),
                ('description', models.TextField(help_text='Tournament description and overview')),
                ('is_official', models.BooleanField(db_index=True, default=False, help_text='Whether this is an official DeltaCrown tournament')),
                ('format', models.CharField(choices=[('single_elimination', 'Single Elimination'), ('double_elimination', 'Double Elimination'), ('round_robin', 'Round Robin'), ('swiss', 'Swiss'), ('group_playoff', 'Group Stage + Playoff')], default='single_elimination', help_text='Bracket format for the tournament', max_length=50)),
                ('participation_type', models.CharField(choices=[('team', 'Team'), ('solo', 'Solo/Individual')], default='team', help_text='Whether teams or individuals participate', max_length=20)),
                ('max_participants', models.PositiveIntegerField(help_text='Maximum number of participants/teams', validators=[django.core.validators.MinValueValidator(2), django.core.validators.MaxValueValidator(256)])),
                ('min_participants', models.PositiveIntegerField(default=2, help_text='Minimum participants needed to start', validators=[django.core.validators.MinValueValidator(2)])),
                ('registration_start', models.DateTimeField(help_text='When registration opens')),
                ('registration_end', models.DateTimeField(help_text='When registration closes')),
                ('tournament_start', models.DateTimeField(help_text='When tournament begins')),
                ('tournament_end', models.DateTimeField(blank=True, help_text='When tournament ends (set automatically)', null=True)),
                ('prize_pool', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total prize pool amount', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('prize_currency', models.CharField(default='BDT', help_text='Currency for prize pool (BDT, USD, etc.)', max_length=10)),
                ('prize_deltacoin', models.PositiveIntegerField(default=0, help_text='Prize pool in DeltaCoins')),
                ('prize_distribution', models.JSONField(blank=True, default=dict, help_text='Prize distribution by placement (JSONB): {"1": "50%", "2": "30%", "3": "20%"}')),
                ('has_entry_fee', models.BooleanField(default=False, help_text='Whether tournament has an entry fee')),
                ('entry_fee_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Entry fee amount', max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('entry_fee_currency', models.CharField(default='BDT', help_text='Currency for entry fee', max_length=10)),
                ('entry_fee_deltacoin', models.PositiveIntegerField(default=0, help_text='Entry fee in DeltaCoins')),
                ('payment_methods', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(choices=[('deltacoin', 'DeltaCoin'), ('bkash', 'bKash'), ('nagad', 'Nagad'), ('rocket', 'Rocket'), ('bank_transfer', 'Bank Transfer')], max_length=20), blank=True, default=list, help_text='Accepted payment methods', size=None)),
                ('enable_fee_waiver', models.BooleanField(default=False, help_text='Enable automatic fee waiver for top teams')),
                ('fee_waiver_top_n_teams', models.PositiveIntegerField(default=0, help_text='Number of top teams eligible for fee waiver')),
                ('banner_image', models.ImageField(blank=True, help_text='Tournament banner image', null=True, upload_to='tournaments/banners/')),
                ('thumbnail_image', models.ImageField(blank=True, help_text='Tournament thumbnail for listings', null=True, upload_to='tournaments/thumbnails/')),
                ('rules_pdf', models.FileField(blank=True, help_text='Tournament rules PDF file', null=True, upload_to='tournaments/rules/')),
                ('promo_video_url', models.URLField(blank=True, help_text='YouTube/Vimeo promo video URL')),
                ('stream_youtube_url', models.URLField(blank=True, help_text='Official YouTube stream URL')),
                ('stream_twitch_url', models.URLField(blank=True, help_text='Official Twitch stream URL')),
                ('enable_check_in', models.BooleanField(default=True, help_text='Require participants to check in before matches')),
                ('check_in_minutes_before', models.PositiveIntegerField(default=15, help_text='Check-in window duration in minutes')),
                ('enable_dynamic_seeding', models.BooleanField(default=False, help_text='Use team rankings for seeding instead of registration order')),
                ('enable_live_updates', models.BooleanField(default=True, help_text='Enable WebSocket live updates for spectators')),
                ('enable_certificates', models.BooleanField(default=True, help_text='Generate certificates for winners')),
                ('enable_challenges', models.BooleanField(default=False, help_text='Enable bonus challenges during tournament')),
                ('enable_fan_voting', models.BooleanField(default=False, help_text='Enable spectator voting/predictions')),
                ('rules_text', models.TextField(blank=True, help_text='Tournament rules in text format')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('pending_approval', 'Pending Approval'), ('published', 'Published'), ('registration_open', 'Registration Open'), ('registration_closed', 'Registration Closed'), ('live', 'Live'), ('completed', 'Completed'), ('cancelled', 'Cancelled'), ('archived', 'Archived')], db_index=True, default='draft', help_text='Current tournament status', max_length=30)),
                ('published_at', models.DateTimeField(blank=True, help_text='When tournament was published', null=True)),
                ('total_registrations', models.PositiveIntegerField(default=0, help_text='Total number of registrations')),
                ('total_matches', models.PositiveIntegerField(default=0, help_text='Total number of matches')),
                ('completed_matches', models.PositiveIntegerField(default=0, help_text='Number of completed matches')),
                ('meta_description', models.TextField(blank=True, help_text='Meta description for SEO')),
                ('meta_keywords', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=50), blank=True, default=list, help_text='SEO keywords', size=None)),
                # ForeignKeys
                ('deleted_by', models.ForeignKey(blank=True, help_text='User who deleted this record', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='%(class)s_deletions', to=settings.AUTH_USER_MODEL)),
                ('game', models.ForeignKey(help_text='Game being played in this tournament', on_delete=django.db.models.deletion.PROTECT, related_name='tournaments', to='tournaments.Game')),
                ('organizer', models.ForeignKey(help_text='User who created this tournament', on_delete=django.db.models.deletion.PROTECT, related_name='organized_tournaments', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Tournament',
                'verbose_name_plural': 'Tournaments',
                'ordering': ['-tournament_start'],
            },
        ),
        
        # 3. Bracket (depends on Tournament, now created AFTER Tournament)
        # KEY FIX: Bracket.tournament field is included here, NOT added via AddField
        migrations.CreateModel(
            name='Bracket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Timestamp when this record was created')),
                ('format', models.CharField(choices=[('single-elimination', 'Single Elimination'), ('double-elimination', 'Double Elimination'), ('round-robin', 'Round Robin'), ('swiss', 'Swiss System'), ('group-stage', 'Group Stage')], default='single-elimination', help_text='Type of bracket structure', max_length=50, verbose_name='Bracket Format')),
                ('total_rounds', models.PositiveIntegerField(default=0, help_text='Total number of rounds in bracket', verbose_name='Total Rounds')),
                ('total_matches', models.PositiveIntegerField(default=0, help_text='Total number of matches in bracket', verbose_name='Total Matches')),
                ('bracket_structure', models.JSONField(blank=True, default=dict, help_text='JSONB tree structure metadata for bracket visualization', verbose_name='Bracket Structure')),
                ('seeding_method', models.CharField(choices=[('slot-order', 'Slot Order (First-Come-First-Served)'), ('random', 'Random Seeding'), ('ranked', 'Ranked Seeding'), ('manual', 'Manual Seeding')], default='slot-order', help_text='How participants are seeded into bracket', max_length=30, verbose_name='Seeding Method')),
                ('is_finalized', models.BooleanField(default=False, help_text='Whether bracket is locked and cannot be regenerated', verbose_name='Is Finalized')),
                ('generated_at', models.DateTimeField(auto_now_add=True, help_text='When bracket was initially generated', null=True, verbose_name='Generated At')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='Last update timestamp', verbose_name='Updated At')),
                # CRITICAL: Include tournament FK here (not via AddField)
                ('tournament', models.OneToOneField(help_text='Tournament this bracket belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='bracket', to='tournaments.Tournament', verbose_name='Tournament')),
            ],
            options={
                'verbose_name': 'Bracket',
                'verbose_name_plural': 'Brackets',
                'db_table': 'tournament_engine_bracket_bracket',
            },
        ),
    ]

    # Database operations: Empty (no schema changes)
    # Production databases are unchanged; only migration state is updated
    database_operations = []

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations,
            database_operations=database_operations,
        )
    ]
