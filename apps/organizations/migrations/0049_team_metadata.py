from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0048_phase1_team_security'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='metadata',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Flexible key-value store (trophy visibility/layout prefs, merch, etc.)',
            ),
        ),
    ]
