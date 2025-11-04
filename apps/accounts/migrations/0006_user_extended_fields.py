# Generated migration for BE-004: User Model Customization

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_update_staff_groups'),
    ]

    operations = [
        # Add UUID field (not as primary key yet to avoid data loss)
        migrations.AddField(
            model_name='user',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=True),
        ),
        
        # Add Role field
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('PLAYER', 'Player'),
                    ('ORGANIZER', 'Organizer'),
                    ('ADMIN', 'Admin')
                ],
                default='PLAYER',
                help_text="User's primary role in the system",
                max_length=20,
            ),
        ),
        
        # Add Extended Profile Fields
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=models.CharField(
                blank=True,
                help_text='Contact phone number',
                max_length=20,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='date_of_birth',
            field=models.DateField(
                blank=True,
                help_text="User's date of birth",
                null=True
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='country',
            field=models.CharField(
                blank=True,
                help_text='Country of residence',
                max_length=100,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(
                blank=True,
                help_text="User's profile picture",
                null=True,
                upload_to='avatars/%Y/%m/%d/'
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(
                blank=True,
                help_text='User biography (max 500 characters)',
                max_length=500,
                null=True
            ),
        ),
        
        # Update Meta options
        migrations.AlterModelOptions(
            name='user',
            options={
                'ordering': ['-date_joined'],
                'swappable': 'AUTH_USER_MODEL',
                'verbose_name': 'User',
                'verbose_name_plural': 'Users'
            },
        ),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='accounts_us_email_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['role'], name='accounts_us_role_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['is_verified'], name='accounts_us_is_veri_idx'),
        ),
    ]
