"""
Add CommunityPreferences model for per-user Community tweaks.
The `tweaks` JSON field stores the React design's TWEAK_DEFAULTS shape
plus future feed defaults (default sort, muted games, etc.).
"""
from django.db import migrations, models
import django.db.models.deletion

from apps.user_profile.models.settings import _community_tweaks_default


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0046_pro_loadout_and_achievement_preference'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityPreferences',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tweaks', models.JSONField(
                    blank=True,
                    default=_community_tweaks_default,
                    help_text=(
                        "Community appearance + feed settings. Keys: accent, background, "
                        "density, layout, showHero, showGameRail, animations, "
                        "defaultSort, defaultIdentity, mutedGames."
                    ),
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user_profile', models.OneToOneField(
                    help_text='User profile these community preferences belong to',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='community_prefs',
                    to='user_profile.userprofile',
                )),
            ],
            options={
                'verbose_name': 'Community Preferences',
                'verbose_name_plural': 'Community Preferences',
                'db_table': 'user_profile_community_preferences',
            },
        ),
    ]
