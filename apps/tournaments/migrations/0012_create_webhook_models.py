"""
Create webhook models and registration UX enhancements
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0011_create_template_rating_models'),
    ]

    operations = [
        # Create FormWebhook model
        migrations.CreateModel(
            name='FormWebhook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField(help_text='External URL to send webhook POST requests')),
                ('secret', models.CharField(blank=True, help_text='Secret key for HMAC signature verification', max_length=255)),
                ('events', models.JSONField(default=list, help_text='List of events to trigger this webhook')),
                ('is_active', models.BooleanField(default=True)),
                ('custom_headers', models.JSONField(blank=True, default=dict, help_text='Custom HTTP headers to send with requests')),
                ('retry_count', models.IntegerField(default=3, help_text='Number of retry attempts for failed deliveries')),
                ('timeout', models.IntegerField(default=10, help_text='Request timeout in seconds')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tournament_form', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='webhooks', to='tournaments.tournamentregistrationform')),
            ],
            options={
                'db_table': 'tournaments_form_webhook',
                'ordering': ['-created_at'],
            },
        ),
        
        # Create WebhookDelivery model
        migrations.CreateModel(
            name='WebhookDelivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('event', models.CharField(max_length=50)),
                ('payload', models.JSONField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')], default='pending', max_length=20)),
                ('status_code', models.IntegerField(blank=True, null=True)),
                ('response_body', models.TextField(blank=True)),
                ('error_message', models.TextField(blank=True)),
                ('attempts', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('delivered_at', models.DateTimeField(blank=True, null=True)),
                ('webhook', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deliveries', to='tournaments.formwebhook')),
            ],
            options={
                'db_table': 'tournaments_webhook_delivery',
                'ordering': ['-created_at'],
            },
        ),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='formwebhook',
            index=models.Index(fields=['tournament_form', 'is_active'], name='webhook_form_active_idx'),
        ),
        
        migrations.AddIndex(
            model_name='webhookdelivery',
            index=models.Index(fields=['webhook', 'status'], name='delivery_webhook_status_idx'),
        ),
        
        migrations.AddIndex(
            model_name='webhookdelivery',
            index=models.Index(fields=['created_at'], name='delivery_created_idx'),
        ),
    ]
