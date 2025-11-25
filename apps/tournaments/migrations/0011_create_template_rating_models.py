"""
Migration for template rating and review system.

Creates:
- TemplateRating model
- RatingHelpful model
"""

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tournaments', '0010_create_form_builder_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='TemplateRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(5)
                    ],
                    help_text='Rating from 1 to 5 stars'
                )),
                ('title', models.CharField(max_length=200, blank=True, help_text='Short review title')),
                ('review', models.TextField(blank=True, help_text='Detailed review of the template')),
                ('ease_of_use', models.IntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(5)
                    ],
                    null=True,
                    blank=True,
                    help_text='How easy was it to use this template?'
                )),
                ('participant_experience', models.IntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(5)
                    ],
                    null=True,
                    blank=True,
                    help_text='How was the participant experience?'
                )),
                ('data_quality', models.IntegerField(
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(5)
                    ],
                    null=True,
                    blank=True,
                    help_text='Quality of data collected'
                )),
                ('would_recommend', models.BooleanField(
                    default=True,
                    help_text='Would you recommend this template to others?'
                )),
                ('helpful_count', models.IntegerField(
                    default=0,
                    help_text='Number of users who found this review helpful'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('verified_usage', models.BooleanField(
                    default=False,
                    help_text='Verified that user actually used this template'
                )),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ratings',
                    to='tournaments.registrationformtemplate'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='template_ratings',
                    to=settings.AUTH_USER_MODEL
                )),
                ('tournament', models.ForeignKey(
                    on_delete=django.db.models.deletion.SET_NULL,
                    null=True,
                    blank=True,
                    related_name='template_ratings',
                    to='tournaments.tournament',
                    help_text='Tournament where this template was used (optional)'
                )),
            ],
            options={
                'db_table': 'tournaments_template_rating',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RatingHelpful',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('rating', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='helpful_votes',
                    to='tournaments.templaterating'
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='helpful_rating_votes',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={
                'db_table': 'tournaments_rating_helpful',
            },
        ),
        migrations.AddConstraint(
            model_name='templaterating',
            constraint=models.UniqueConstraint(
                fields=['template', 'user', 'tournament'],
                name='unique_template_user_tournament_rating'
            ),
        ),
        migrations.AddIndex(
            model_name='templaterating',
            index=models.Index(fields=['template', '-rating'], name='template_rating_idx'),
        ),
        migrations.AddIndex(
            model_name='templaterating',
            index=models.Index(fields=['template', '-helpful_count'], name='template_helpful_idx'),
        ),
        migrations.AddIndex(
            model_name='templaterating',
            index=models.Index(fields=['user', '-created_at'], name='user_ratings_idx'),
        ),
        migrations.AddIndex(
            model_name='templaterating',
            index=models.Index(fields=['-created_at'], name='recent_ratings_idx'),
        ),
        migrations.AddConstraint(
            model_name='ratinghelpful',
            constraint=models.UniqueConstraint(
                fields=['rating', 'user'],
                name='unique_rating_user_helpful'
            ),
        ),
        migrations.AddIndex(
            model_name='ratinghelpful',
            index=models.Index(fields=['rating', 'user'], name='rating_helpful_idx'),
        ),
        migrations.AddIndex(
            model_name='ratinghelpful',
            index=models.Index(fields=['user', '-created_at'], name='user_helpful_idx'),
        ),
    ]
