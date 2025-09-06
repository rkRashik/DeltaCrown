from django.db import migrations, models

def backfill_groups_published(apps, schema_editor):
    Tournament = apps.get_model('tournaments', 'Tournament')
    # Set False for any NULLs or missing values - safe and idempotent
    for t in Tournament.objects.all().only('pk'):
        pass  # Nothing to backfill explicitly since default applies on add

class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='groups_published',
            field=models.BooleanField(default=False, help_text='Show bracket groups on public page when enabled.'),
        ),
        migrations.RunPython(backfill_groups_published, migrations.RunPython.noop),
    ]
