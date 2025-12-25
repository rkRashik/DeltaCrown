# Generated manually for GP-0 Game Passport rebuild
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0019_alter_userauditevent_event_type'),
    ]

    operations = [
        # Step 1: Add new fields to GameProfile
        migrations.AddField(
            model_name='gameprofile',
            name='identity_key',
            field=models.CharField(
                max_length=255,
                db_index=True,
                help_text='Normalized identity for global uniqueness'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='visibility',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('PUBLIC', 'Public'),
                    ('PROTECTED', 'Protected (friends only)'),
                    ('PRIVATE', 'Private')
                ],
                default='PUBLIC',
                help_text='Privacy level for this passport'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='is_lft',
            field=models.BooleanField(
                default=False,
                help_text='Looking for team'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='region',
            field=models.CharField(
                max_length=50,
                blank=True,
                default='',
                help_text='Player region for team recruitment'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='is_pinned',
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text='Pinned to profile showcase'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='pinned_order',
            field=models.SmallIntegerField(
                null=True,
                blank=True,
                db_index=True,
                help_text='Order for pinned passports (1, 2, 3...)'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='sort_order',
            field=models.SmallIntegerField(
                default=0,
                help_text='Manual sort order'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='locked_until',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text='Identity locked until this time (cooldown)'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='status',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('ACTIVE', 'Active'),
                    ('SUSPENDED', 'Suspended')
                ],
                default='ACTIVE',
                help_text='Passport status'
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='metadata',
            field=models.JSONField(
                default=dict,
                blank=True,
                help_text='Per-game extras (e.g., MLBB zone_id, rank details)'
            ),
        ),
        
        # Step 2: Deprecate is_verified
        migrations.AlterField(
            model_name='gameprofile',
            name='is_verified',
            field=models.BooleanField(
                default=False,
                editable=False,
                help_text='DEPRECATED in GP-0. No verification system. Keep for data migration.'
            ),
        ),
        
        # Step 3: Create GameProfileAlias model
        migrations.CreateModel(
            name='GameProfileAlias',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('old_in_game_name', models.CharField(
                    max_length=255,
                    help_text='Previous in-game name before change'
                )),
                ('changed_at', models.DateTimeField(
                    auto_now_add=True,
                    help_text='When identity was changed'
                )),
                ('changed_by_user_id', models.IntegerField(
                    help_text='User ID who made the change'
                )),
                ('request_ip', models.GenericIPAddressField(
                    null=True,
                    blank=True,
                    help_text='IP address of change request'
                )),
                ('reason', models.CharField(
                    max_length=500,
                    blank=True,
                    default='',
                    help_text='Reason for identity change'
                )),
                ('game_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='aliases',
                    to='user_profile.gameprofile',
                    help_text='Game passport this alias belongs to'
                )),
            ],
            options={
                'verbose_name': 'Game Profile Alias',
                'verbose_name_plural': 'Game Profile Aliases',
                'ordering': ['-changed_at'],
                'indexes': [
                    models.Index(
                        fields=['game_profile', '-changed_at'],
                        name='user_profil_game_pr_idx'
                    ),
                ],
            },
        ),
        
        # Step 4: Create GameProfileConfig model
        migrations.CreateModel(
            name='GameProfileConfig',
            fields=[
                ('id', models.BigAutoField(
                    auto_created=True,
                    primary_key=True,
                    serialize=False,
                    verbose_name='ID'
                )),
                ('cooldown_days', models.IntegerField(
                    default=30,
                    help_text='Days before user can change identity again'
                )),
                ('allow_id_change', models.BooleanField(
                    default=True,
                    help_text='Global toggle for identity changes'
                )),
                ('max_pinned_games', models.IntegerField(
                    default=3,
                    help_text='Maximum pinned passports per user'
                )),
                ('require_region', models.BooleanField(
                    default=False,
                    help_text='Require region on passport creation'
                )),
                ('enable_ip_smurf_detection', models.BooleanField(
                    default=False,
                    help_text='Enable IP-based smurf detection (future)'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    help_text='When config was created'
                )),
                ('updated_at', models.DateTimeField(
                    auto_now=True,
                    help_text='When config was last updated'
                )),
            ],
            options={
                'verbose_name': 'Game Passport Configuration',
                'verbose_name_plural': 'Game Passport Configuration',
            },
        ),
        
        # Step 5: Add unique constraint
        migrations.AddConstraint(
            model_name='gameprofile',
            constraint=models.UniqueConstraint(
                fields=['game', 'identity_key'],
                name='unique_game_identity'
            ),
        ),
        
        # Step 6: Update ordering in Meta
        migrations.AlterModelOptions(
            name='gameprofile',
            options={
                'ordering': ['-is_pinned', '-pinned_order', 'sort_order', '-updated_at'],
                'verbose_name': 'Game Profile',
                'verbose_name_plural': 'Game Profiles',
            },
        ),
    ]
