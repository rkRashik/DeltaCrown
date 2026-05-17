"""Add MaintenanceRunLog table and can_run_maintenance_tasks permission."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0012_mediacleanupcandidate'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MaintenanceRunLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='maintenance_runs',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('task_name', models.CharField(max_length=100)),
                ('status', models.CharField(
                    choices=[('success', 'Success'), ('partial', 'Partial'), ('failed', 'Failed')],
                    default='success',
                    max_length=20,
                )),
                ('started_at', models.DateTimeField()),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('duration_ms', models.PositiveIntegerField(blank=True, null=True)),
                ('summary', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Maintenance Run Log',
                'verbose_name_plural': 'Maintenance Run Logs',
                'db_table': 'games_maintenancerunlog',
                'ordering': ['-created_at'],
                'permissions': [('can_run_maintenance_tasks', 'Can run system maintenance tasks')],
            },
        ),
    ]
