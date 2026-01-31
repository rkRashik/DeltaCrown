# Generated migration to add social media fields to Team
# Gate 5: Schema Cleanup - Add twitter/instagram/youtube/twitch URLs

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0007_add_team_visibility'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='twitter_url',
            field=models.URLField(
                blank=True,
                max_length=200,
                help_text='Team Twitter/X profile URL'
            ),
        ),
        migrations.AddField(
            model_name='team',
            name='instagram_url',
            field=models.URLField(
                blank=True,
                max_length=200,
                help_text='Team Instagram profile URL'
            ),
        ),
        migrations.AddField(
            model_name='team',
            name='youtube_url',
            field=models.URLField(
                blank=True,
                max_length=200,
                help_text='Team YouTube channel URL'
            ),
        ),
        migrations.AddField(
            model_name='team',
            name='twitch_url',
            field=models.URLField(
                blank=True,
                max_length=200,
                help_text='Team Twitch channel URL'
            ),
        ),
    ]
