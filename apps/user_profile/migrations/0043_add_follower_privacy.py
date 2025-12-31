"""
Add follower/following privacy controls to PrivacySettings model.

Phase 2F - Instagram-style follower privacy controls:
- Show/hide follower count
- Show/hide following count  
- Control who can see follower list (PUBLIC / FOLLOWERS_ONLY / PRIVATE)
- Control who can see following list (PUBLIC / FOLLOWERS_ONLY / PRIVATE)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0042_add_bounty_endorsements'),
    ]

    operations = [
        migrations.AddField(
            model_name='privacysettings',
            name='show_followers_count',
            field=models.BooleanField(
                default=True,
                help_text='Show follower count on public profile'
            ),
        ),
        migrations.AddField(
            model_name='privacysettings',
            name='show_following_count',
            field=models.BooleanField(
                default=True,
                help_text='Show following count on public profile'
            ),
        ),
        migrations.AddField(
            model_name='privacysettings',
            name='followers_list_visibility',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('PUBLIC', 'Public - Anyone can see'),
                    ('FOLLOWERS_ONLY', 'Followers Only'),
                    ('PRIVATE', 'Private - Only me'),
                ],
                default='PUBLIC',
                help_text='Who can view the list of followers'
            ),
        ),
        migrations.AddField(
            model_name='privacysettings',
            name='following_list_visibility',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('PUBLIC', 'Public - Anyone can see'),
                    ('FOLLOWERS_ONLY', 'Followers Only'),
                    ('PRIVATE', 'Private - Only me'),
                ],
                default='PUBLIC',
                help_text='Who can view the list of accounts being followed'
            ),
        ),
    ]
