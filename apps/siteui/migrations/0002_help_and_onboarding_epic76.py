# Generated migration for Phase 7, Epic 7.6: Guidance & Help Overlays

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('siteui', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tournaments', '0029_add_audit_log_epic75_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='HelpContent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text="Unique identifier (e.g., 'results_inbox_intro')", max_length=100, unique=True)),
                ('scope', models.CharField(db_index=True, help_text="Context/page where this help applies (e.g., 'organizer_results_inbox')", max_length=100)),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField(help_text='Markdown or plain text content')),
                ('html_body', models.TextField(blank=True, help_text='Pre-rendered HTML (optional, for performance)')),
                ('audience', models.CharField(choices=[('organizer', 'Organizer'), ('referee', 'Referee'), ('player', 'Player'), ('global', 'Global/All Users')], default='global', help_text='Who should see this help content', max_length=20)),
                ('is_active', models.BooleanField(default=True, help_text='Whether this content is currently shown')),
                ('display_order', models.IntegerField(default=0, help_text='Sort order when multiple help items exist for same scope')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Help Content',
                'verbose_name_plural': 'Help Content Items',
                'ordering': ['scope', 'display_order', 'title'],
            },
        ),
        migrations.CreateModel(
            name='HelpOverlay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('page_id', models.CharField(db_index=True, help_text="Page identifier (e.g., 'results_inbox', 'scheduling')", max_length=100)),
                ('placement', models.CharField(choices=[('top', 'Top'), ('top-right', 'Top Right'), ('right', 'Right'), ('bottom-right', 'Bottom Right'), ('bottom', 'Bottom'), ('bottom-left', 'Bottom Left'), ('left', 'Left'), ('top-left', 'Top Left'), ('center', 'Center')], default='top-right', help_text='Where the overlay should appear on screen', max_length=20)),
                ('config', models.JSONField(blank=True, default=dict, help_text='Advanced configuration (trigger, animation, etc.)')),
                ('is_active', models.BooleanField(default=True)),
                ('display_order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('help_content', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='overlays', to='siteui.helpcontent')),
            ],
            options={
                'verbose_name': 'Help Overlay',
                'verbose_name_plural': 'Help Overlays',
                'ordering': ['page_id', 'display_order'],
            },
        ),
        migrations.CreateModel(
            name='OrganizerOnboardingState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('step_key', models.CharField(help_text="Onboarding step identifier (e.g., 'results_inbox_intro')", max_length=100)),
                ('completed_at', models.DateTimeField(blank=True, help_text='When the user completed this step', null=True)),
                ('dismissed', models.BooleanField(default=False, help_text='Whether user dismissed/skipped this step')),
                ('dismissed_at', models.DateTimeField(blank=True, help_text='When the user dismissed this step', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tournament', models.ForeignKey(blank=True, help_text='If set, onboarding is tournament-specific', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='onboarding_states', to='tournaments.tournament')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='organizer_onboarding_states', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Organizer Onboarding State',
                'verbose_name_plural': 'Organizer Onboarding States',
            },
        ),
        migrations.AddIndex(
            model_name='helpcontent',
            index=models.Index(fields=['scope', 'is_active'], name='siteui_help_scope_active_idx'),
        ),
        migrations.AddIndex(
            model_name='helpcontent',
            index=models.Index(fields=['audience', 'is_active'], name='siteui_help_audience_active_idx'),
        ),
        migrations.AddIndex(
            model_name='helpoverlay',
            index=models.Index(fields=['page_id', 'is_active'], name='siteui_overlay_page_active_idx'),
        ),
        migrations.AddConstraint(
            model_name='organizeronboardingstate',
            constraint=models.UniqueConstraint(fields=('user', 'tournament', 'step_key'), name='unique_onboarding_state_per_user_tournament_step'),
        ),
        migrations.AddIndex(
            model_name='organizeronboardingstate',
            index=models.Index(fields=['user', 'tournament'], name='siteui_onboard_user_tourn_idx'),
        ),
        migrations.AddIndex(
            model_name='organizeronboardingstate',
            index=models.Index(fields=['user', 'step_key'], name='siteui_onboard_user_step_idx'),
        ),
    ]
