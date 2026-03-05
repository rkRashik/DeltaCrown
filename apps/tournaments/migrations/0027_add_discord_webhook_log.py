"""
Migration: Add DiscordWebhookLog model.

Stores rolling delivery receipts (max 50 per tournament) for Discord webhooks.
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0026_add_discord_webhook_url'),
    ]

    operations = [
        migrations.CreateModel(
            name='DiscordWebhookLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(db_index=True, help_text="Event name (e.g. 'bracket_generated', 'match_ready')", max_length=64)),
                ('webhook_url_preview', models.CharField(blank=True, help_text='First 80 characters of the webhook URL (for debugging; never the full secret)', max_length=80)),
                ('success', models.BooleanField(db_index=True, default=False)),
                ('response_code', models.PositiveSmallIntegerField(blank=True, help_text='HTTP response status code from Discord (204 = success)', null=True)),
                ('error_message', models.TextField(blank=True, help_text='Exception message or Discord error body when success=False')),
                ('sent_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='discord_webhook_logs', to='tournaments.tournament')),
            ],
            options={
                'verbose_name': 'Discord Webhook Log',
                'verbose_name_plural': 'Discord Webhook Logs',
                'ordering': ['-sent_at'],
            },
        ),
        migrations.AddIndex(
            model_name='discordwebhooklog',
            index=models.Index(fields=['tournament', '-sent_at'], name='idx_discord_log_tournament'),
        ),
    ]
