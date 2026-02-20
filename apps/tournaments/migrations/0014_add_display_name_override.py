from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0013_add_guest_team_and_waitlist_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='allow_display_name_override',
            field=models.BooleanField(
                default=False,
                help_text='Allow participants to set a custom display name for brackets and match rooms',
            ),
        ),
    ]
