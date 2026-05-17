"""Add MediaCleanupCandidate table for deferred Cloudinary orphan cleanup."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0011_reorder_valorant_server_regions'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaCleanupCandidate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file_name', models.CharField(
                    db_index=True,
                    help_text='Cloudinary public_id or local file path stored in the DB field.',
                    max_length=500,
                )),
                ('storage_type', models.CharField(
                    choices=[('cloudinary', 'Cloudinary'), ('local', 'Local filesystem')],
                    default='cloudinary',
                    max_length=20,
                )),
                ('source_model', models.CharField(
                    help_text="e.g. 'games.Game' or 'games.GameMapPool'",
                    max_length=100,
                )),
                ('source_object_id', models.PositiveIntegerField(
                    blank=True,
                    help_text='PK of the source model row.',
                    null=True,
                )),
                ('source_field', models.CharField(
                    help_text="ImageField name, e.g. 'icon', 'card_image'.",
                    max_length=100,
                )),
                ('reason', models.CharField(
                    choices=[('replaced', 'Field replaced with new file'), ('cleared', 'Field cleared (set to empty)')],
                    max_length=20,
                )),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending — awaiting retention period'),
                        ('deleted', 'Deleted from storage'),
                        ('skipped', 'Skipped (still referenced or protected)'),
                        ('failed', 'Deletion failed'),
                    ],
                    db_index=True,
                    default='pending',
                    max_length=20,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('eligible_after', models.DateTimeField(
                    db_index=True,
                    help_text='Deletion not attempted before this timestamp.',
                )),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True)),
                ('metadata', models.JSONField(
                    blank=True,
                    default=dict,
                    help_text='Extra context: old/new public_id, game name, etc.',
                )),
            ],
            options={
                'verbose_name': 'Media Cleanup Candidate',
                'verbose_name_plural': 'Media Cleanup Candidates',
                'db_table': 'games_mediacleanupcandidate',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='mediacleanupcandidate',
            index=models.Index(fields=['status', 'eligible_after'], name='games_media_status_elig_idx'),
        ),
        migrations.AddIndex(
            model_name='mediacleanupcandidate',
            index=models.Index(fields=['file_name'], name='games_media_file_name_idx'),
        ),
    ]
