# Generated migration for Phase 3 performance optimizations

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0047_add_performance_indices_proper'),
    ]

    operations = [
        # Add index on TeamDiscussionPost.created_at for sorting
        migrations.AddIndex(
            model_name='teamdiscussionpost',
            index=models.Index(fields=['-created_at'], name='teams_disc_created_idx'),
        ),
        
        # Add index on TeamDiscussionPost.post_type for filtering
        migrations.AddIndex(
            model_name='teamdiscussionpost',
            index=models.Index(fields=['post_type', '-created_at'], name='teams_disc_type_idx'),
        ),
        
        # Add index on TeamChatMessage.created_at for pagination
        migrations.AddIndex(
            model_name='teamchatmessage',
            index=models.Index(fields=['-created_at'], name='teams_chat_created_idx'),
        ),
        
        # Add index on TeamChatMessage.team for filtering
        migrations.AddIndex(
            model_name='teamchatmessage',
            index=models.Index(fields=['team', '-created_at'], name='teams_chat_team_idx'),
        ),
        
        # Add index on TeamSponsor.status for active sponsors query
        migrations.AddIndex(
            model_name='teamsponsor',
            index=models.Index(fields=['status', 'is_active'], name='teams_sponsor_active_idx'),
        ),
    ]
