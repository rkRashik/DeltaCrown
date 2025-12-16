from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("user_profile", "0008_follow"),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='riot_id',
            field=models.CharField(max_length=100, blank=True, default='', help_text='Riot ID (Name#TAG) for Valorant'),
        ),
    ]
