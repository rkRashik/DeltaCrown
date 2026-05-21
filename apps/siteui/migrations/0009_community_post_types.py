"""
Add post_type, poll_data, lft_data, tournament FK to CommunityPost.
Add CommunityPollVote model.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('siteui', '0008_arena_media_schema_refactor'),
        ('tournaments', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='communitypost',
            name='post_type',
            field=models.CharField(
                choices=[
                    ('text', 'Discussion'), ('image', 'Image / Photo'),
                    ('clip', 'Video Clip'), ('poll', 'Poll'),
                    ('lft', 'Looking for Team'), ('recruit', 'Recruiting'),
                    ('event', 'Event'),
                ],
                default='text', db_index=True, max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='communitypost',
            name='content',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='communitypost',
            name='poll_data',
            field=models.JSONField(
                blank=True, null=True,
                help_text='Poll: {options:[{id,label,votes}], total, ends_at}',
            ),
        ),
        migrations.AddField(
            model_name='communitypost',
            name='lft_data',
            field=models.JSONField(
                blank=True, null=True,
                help_text='LFT: {roles, rank, region, hours, availability, looking_for}',
            ),
        ),
        migrations.AddField(
            model_name='communitypost',
            name='tournament',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='community_posts',
                to='tournaments.tournament',
                help_text='Tournament this post is associated with (organizers only)',
            ),
        ),
        migrations.AddIndex(
            model_name='communitypost',
            index=models.Index(fields=['post_type', '-created_at'], name='siteui_comm_post_ty_idx'),
        ),
        migrations.CreateModel(
            name='CommunityPollVote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('option_id', models.CharField(max_length=40)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('post', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='poll_votes', to='siteui.communitypost',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='community_poll_votes', to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'indexes': [models.Index(fields=['post'], name='siteui_comm_pollvote_post_idx')],
            },
        ),
        migrations.AlterUniqueTogether(
            name='communitypollvote',
            unique_together={('post', 'user')},
        ),
    ]
