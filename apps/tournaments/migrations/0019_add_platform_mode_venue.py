# Generated migration for Platform & Mode fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0018_alter_templaterating_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='platform',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('pc', 'PC'),
                    ('mobile', 'Mobile'),
                    ('ps5', 'PlayStation 5'),
                    ('xbox', 'Xbox Series X/S'),
                    ('switch', 'Nintendo Switch'),
                ],
                default='pc',
                help_text='Gaming platform for this tournament'
            ),
        ),
        migrations.AddField(
            model_name='tournament',
            name='mode',
            field=models.CharField(
                max_length=10,
                choices=[
                    ('online', 'Online'),
                    ('lan', 'LAN'),
                    ('hybrid', 'Hybrid (Online + LAN Finals)'),
                ],
                default='online',
                help_text='Tournament mode - affects location requirements'
            ),
        ),
        migrations.AddField(
            model_name='tournament',
            name='venue_name',
            field=models.CharField(
                max_length=200,
                blank=True,
                default='',
                help_text='Venue name for LAN tournaments'
            ),
        ),
        migrations.AddField(
            model_name='tournament',
            name='venue_address',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Complete venue address for LAN tournaments'
            ),
        ),
        migrations.AddField(
            model_name='tournament',
            name='venue_city',
            field=models.CharField(
                max_length=100,
                blank=True,
                default='',
                help_text='City where LAN event is held'
            ),
        ),
        migrations.AddField(
            model_name='tournament',
            name='venue_map_url',
            field=models.URLField(
                blank=True,
                default='',
                help_text='Google Maps link to venue'
            ),
        ),
    ]
