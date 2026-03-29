from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0040_registration_participants_perf_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='reschedulerequest',
            name='expires_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='reschedulerequest',
            name='proposer_side',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Participant 1'), (2, 'Participant 2')], help_text='Which side (participant1/participant2) initiated the proposal', null=True),
        ),
        migrations.AddField(
            model_name='reschedulerequest',
            name='response_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='reschedulerequest',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
