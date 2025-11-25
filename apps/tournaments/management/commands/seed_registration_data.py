"""
Seed Data for Form Builder System

Creates sample form templates, registrations, ratings, and webhooks for testing.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.tournaments.models import (
    Tournament,
    RegistrationFormTemplate,
    TournamentRegistrationForm,
    FormResponse,
)
from apps.tournaments.models.webhooks import FormWebhook
from apps.tournaments.models.template_rating import TemplateRating
from datetime import datetime, timedelta
from django.db import models
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed sample registrations, ratings, and webhooks for form builder testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tournament-slug',
            type=str,
            help='Tournament slug to seed data for',
        )
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of sample registrations to create',
        )
    
    def handle(self, *args, **options):
        tournament_slug = options.get('tournament_slug')
        count = options['count']
        
        if not tournament_slug:
            self.stdout.write(self.style.ERROR('Please provide --tournament-slug'))
            return
        
        try:
            tournament = Tournament.objects.get(slug=tournament_slug)
        except Tournament.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Tournament "{tournament_slug}" not found'))
            return
        
        # Get or create tournament registration form
        try:
            tournament_form = TournamentRegistrationForm.objects.get(tournament=tournament)
        except TournamentRegistrationForm.DoesNotExist:
            # Get a template
            try:
                template = RegistrationFormTemplate.objects.filter(
                    game=tournament.game,
                    is_active=True
                ).first()
                
                if not template:
                    self.stdout.write(self.style.ERROR('No active templates found. Run seed_form_templates first.'))
                    return
                
                tournament_form = TournamentRegistrationForm.objects.create(
                    tournament=tournament,
                    template=template,
                    is_active=True
                )
                self.stdout.write(self.style.SUCCESS(f'Created tournament form using template: {template.name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating tournament form: {str(e)}'))
                return
        
        template = tournament_form.template
        
        # Get all users
        users = list(User.objects.all()[:50])
        if len(users) < 5:
            self.stdout.write(self.style.WARNING('Not enough users. Creating sample users...'))
            for i in range(10):
                User.objects.get_or_create(
                    username=f'testuser{i}',
                    defaults={'email': f'testuser{i}@example.com'}
                )
            users = list(User.objects.all())
        
        # Create sample registrations
        self.stdout.write('Creating sample registrations...')
        
        statuses = ['draft', 'submitted', 'approved', 'rejected']
        status_weights = [0.1, 0.4, 0.4, 0.1]  # More submitted/approved
        
        created_count = 0
        for i in range(count):
            user = random.choice(users)
            
            # Generate random form data based on template schema
            form_data = {}
            for section in template.form_schema.get('sections', []):
                for field in section.get('fields', []):
                    if field.get('type') not in ['section_header', 'divider']:
                        field_id = field.get('id')
                        field_type = field.get('type')
                        
                        # Generate appropriate random data
                        if field_type == 'text':
                            form_data[field_id] = f"Sample text for {field.get('label', field_id)}"
                        elif field_type == 'email':
                            form_data[field_id] = f"{user.username}@example.com"
                        elif field_type == 'number':
                            form_data[field_id] = random.randint(1, 100)
                        elif field_type == 'tel':
                            form_data[field_id] = f"+880{random.randint(1000000000, 1999999999)}"
                        elif field_type == 'select':
                            options = field.get('options', [])
                            if options:
                                form_data[field_id] = random.choice(options).get('value', '')
                        elif field_type == 'checkbox':
                            options = field.get('options', [])
                            if options:
                                selected = random.sample(
                                    [opt.get('value') for opt in options],
                                    k=random.randint(1, min(3, len(options)))
                                )
                                form_data[field_id] = selected
                        elif field_type == 'radio':
                            options = field.get('options', [])
                            if options:
                                form_data[field_id] = random.choice(options).get('value', '')
                        elif field_type == 'textarea':
                            form_data[field_id] = f"This is a longer text response for {field.get('label', field_id)}. " * 3
                        elif field_type == 'date':
                            future_date = datetime.now() + timedelta(days=random.randint(1, 90))
                            form_data[field_id] = future_date.strftime('%Y-%m-%d')
            
            # Create response
            status = random.choices(statuses, weights=status_weights)[0]
            
            response = FormResponse.objects.create(
                tournament_form=tournament_form,
                user=user,
                status=status,
                response_data=form_data,
                has_paid=random.choice([True, False]) if status in ['submitted', 'approved'] else False,
                payment_verified=False,
                metadata={'device_type': random.choice(['desktop', 'mobile', 'tablet'])}
            )
            
            # Set submitted_at for non-drafts
            if status != 'draft':
                response.submitted_at = datetime.now() - timedelta(days=random.randint(1, 30))
                response.save()
            
            # Randomly verify some payments
            if response.has_paid and random.random() < 0.7:
                response.payment_verified = True
                response.save()
            
            created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_count} sample registrations'))
        
        # Create sample ratings for the template
        self.stdout.write('Creating sample ratings...')
        
        # Get random users who have used this template
        raters = random.sample(users, min(10, len(users)))
        rating_count = 0
        
        for user in raters:
            # Skip if already rated
            if TemplateRating.objects.filter(template=template, user=user).exists():
                continue
            
            rating = TemplateRating.objects.create(
                template=template,
                user=user,
                tournament=tournament,
                rating=random.randint(3, 5),  # Mostly good ratings
                title=random.choice([
                    "Great template!",
                    "Very comprehensive",
                    "Easy to use",
                    "Could be better",
                    "Perfect for our tournament",
                    "Highly recommended"
                ]),
                review=random.choice([
                    "This template made registration super easy. All the fields we needed were there.",
                    "Well organized and easy to fill out. Participants had no issues.",
                    "Good template but could use more customization options.",
                    "Perfect for our PUBG Mobile tournament. Saved us lots of time.",
                    "The multi-step layout is great. Made the process less overwhelming.",
                ]),
                ease_of_use=random.randint(3, 5),
                participant_experience=random.randint(3, 5),
                data_quality=random.randint(3, 5),
                would_recommend=random.choice([True, True, True, False]),  # 75% would recommend
                verified_usage=random.choice([True, False])
            )
            
            # Add random helpful votes
            if rating_count > 0:
                helpful_voters = random.sample(users, random.randint(0, 5))
                for voter in helpful_voters:
                    rating.mark_helpful(voter)
            
            rating_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Created {rating_count} sample ratings'))
        
        # Create sample webhook (optional)
        self.stdout.write('Creating sample webhook...')
        
        webhook, created = FormWebhook.objects.get_or_create(
            tournament_form=tournament_form,
            url='https://webhook.site/unique-uuid-here',
            defaults={
                'events': ['response.submitted', 'response.approved', 'payment.verified'],
                'secret': 'test_secret_key_123',
                'is_active': True,
                'retry_count': 3,
                'timeout': 10,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created sample webhook'))
        else:
            self.stdout.write(self.style.WARNING('Webhook already exists'))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Complete ==='))
        self.stdout.write(f'Tournament: {tournament.name}')
        self.stdout.write(f'Template: {template.name}')
        self.stdout.write(f'Registrations: {created_count}')
        self.stdout.write(f'Ratings: {rating_count}')
        self.stdout.write(f'Webhook: {"Created" if created else "Already exists"}')
        
        # Show stats
        stats = FormResponse.objects.filter(tournament_form=tournament_form).values('status').annotate(count=models.Count('id'))
        self.stdout.write('\nRegistration Status Breakdown:')
        for stat in stats:
            self.stdout.write(f"  {stat['status']}: {stat['count']}")
