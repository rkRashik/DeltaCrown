"""
Complete Form Builder Demo Seeder

Creates a full demo environment with:
- A demo tournament
- Registration form from template
- Sample registrations
- Ratings and reviews
- Webhook configuration
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed complete form builder demo environment'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing demo data first',
        )
    
    def handle(self, *args, **options):
        from apps.tournaments.models import (
            Game,
            Tournament,
            TournamentRegistrationForm,
            RegistrationFormTemplate,
            FormResponse,
            TemplateRating,
            FormWebhook,
        )
        
        self.stdout.write(self.style.SUCCESS('🚀 Starting Form Builder Demo Seeding...'))
        
        # 1. Get or create superuser/organizer
        self.stdout.write('📝 Setting up users...')
        try:
            organizer = User.objects.get(username='admin')
        except User.DoesNotExist:
            organizer = User.objects.create_superuser(
                username='admin',
                email='admin@deltacrown.com',
                password='admin123'
            )
            self.stdout.write(self.style.SUCCESS(f'  ✅ Created admin user (username: admin, password: admin123)'))
        
        # Create sample participants
        participants = []
        for i in range(1, 6):
            username = f'player{i}'
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=username,
                    email=f'{username}@example.com',
                    password='password123'
                )
            participants.append(user)
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {len(participants)} participant accounts'))
        
        # 2. Get or create game
        self.stdout.write('🎮 Setting up game...')
        game, created = Game.objects.get_or_create(
            slug='valorant',
            defaults={
                'name': 'VALORANT',
                'is_active': True,
                'description': 'Tactical 5v5 FPS',
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('  ✅ Created VALORANT game'))
        else:
            self.stdout.write('  ℹ️ VALORANT game already exists')
        
        # 3. Get existing tournament (simpler than creating)
        self.stdout.write('🏆 Finding existing tournament...')
        tournament = Tournament.objects.first()
        
        if not tournament:
            self.stdout.write(self.style.ERROR('  ❌ No tournaments found in database'))
            self.stdout.write('  Please create a tournament first or import sample data')
            return
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Using tournament: {tournament.name}'))
        
        # 4. Create registration form from template
        self.stdout.write('📋 Setting up registration form...')
        
        # Get a template (from seed_form_templates)
        try:
            template = RegistrationFormTemplate.objects.filter(
                participation_type='team',
                is_active=True
            ).first()
            
            if not template:
                self.stdout.write(self.style.WARNING('  ⚠️ No templates found. Run: python manage.py seed_form_templates'))
                return
            
            # Create or get tournament form
            tournament_form, created = TournamentRegistrationForm.objects.get_or_create(
                tournament=tournament,
                defaults={
                    'based_on_template': template,
                    'form_schema': template.form_schema,
                    'enable_multi_step': True,
                    'enable_autosave': True,
                    'enable_progress_bar': True,
                    'allow_edits_after_submit': False,
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✅ Created registration form from template: {template.name}'))
            else:
                self.stdout.write(f'  ℹ️ Registration form already exists')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Error creating form: {e}'))
            return
        
        # 5. Create sample registrations
        self.stdout.write('👥 Creating sample registrations...')
        statuses = ['draft', 'submitted', 'approved', 'rejected']
        status_weights = [2, 5, 8, 1]  # More approved than others
        
        created_count = 0
        for i, participant in enumerate(participants * 4):  # 20 total registrations
            status = random.choices(statuses, weights=status_weights)[0]
            has_paid = status in ['approved', 'rejected'] and random.random() > 0.3
            payment_verified = has_paid and random.random() > 0.4
            
            # Generate realistic form data based on schema
            form_data = {
                'team_name': f'Team {random.choice(["Alpha", "Bravo", "Charlie", "Delta", "Echo"])} {i}',
                'captain_ign': f'{participant.username}_captain',
                'captain_discord': f'{participant.username}#1234',
                'captain_email': participant.email,
                'team_size': random.randint(5, 7),
                'experience_level': random.choice(['beginner', 'intermediate', 'advanced', 'professional']),
                'previous_tournaments': random.randint(0, 10),
                'agree_to_rules': True,
            }
            
            response, created = FormResponse.objects.get_or_create(
                tournament=tournament,
                user=participant,
                defaults={
                    'registration_form': tournament_form,
                    'response_data': form_data,
                    'status': status,
                    'has_paid': has_paid,
                    'payment_verified': payment_verified,
                    'payment_amount': tournament.entry_fee_amount if has_paid else None,
                    'submitted_at': timezone.now() - timedelta(days=random.randint(1, 20)) if status != 'draft' else None,
                }
            )
            
            if created:
                created_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {created_count} sample registrations'))
        
        # Get stats
        total = FormResponse.objects.filter(registration_form=tournament_form).count()
        stats = {
            'draft': FormResponse.objects.filter(registration_form=tournament_form, status='draft').count(),
            'submitted': FormResponse.objects.filter(registration_form=tournament_form, status='submitted').count(),
            'approved': FormResponse.objects.filter(registration_form=tournament_form, status='approved').count(),
            'rejected': FormResponse.objects.filter(registration_form=tournament_form, status='rejected').count(),
        }
        
        self.stdout.write(f'     Total: {total} | Draft: {stats["draft"]} | Submitted: {stats["submitted"]} | Approved: {stats["approved"]} | Rejected: {stats["rejected"]}')
        
        # 6. Create template ratings
        self.stdout.write('⭐ Creating template ratings...')
        rating_count = 0
        for participant in participants:
            if random.random() > 0.3:  # 70% chance to rate
                rating, created = TemplateRating.objects.get_or_create(
                    template=template,
                    user=participant,
                    defaults={
                        'rating': random.randint(3, 5),
                        'ease_of_use': random.randint(3, 5),
                        'participant_experience': random.randint(3, 5),
                        'data_quality': random.randint(3, 5),
                        'review': random.choice([
                            'Great template! Very easy to use.',
                            'Perfect for team tournaments.',
                            'Love the multi-step layout.',
                            'Could use more customization options.',
                            '',  # Some ratings without review
                        ]),
                        'verified_usage': random.random() > 0.5,
                        'would_recommend': True,
                    }
                )
                if created:
                    rating_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {rating_count} template ratings'))
        
        # 7. Create sample webhook
        self.stdout.write('🔔 Creating sample webhook...')
        webhook, created = FormWebhook.objects.get_or_create(
            tournament_form=tournament_form,
            url='https://webhook.site/unique-id-here',
            defaults={
                'secret': 'demo-secret-key-123',
                'events': [
                    'response.submitted',
                    'response.approved',
                    'payment.verified',
                ],
                'is_active': True,
                'retry_count': 3,
                'timeout': 30,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Created webhook configuration'))
        else:
            self.stdout.write(f'  ℹ️ Webhook already exists')
        
        # 8. Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('✅ DEMO ENVIRONMENT READY!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🔗 Access URLs:'))
        self.stdout.write(f'   Template Library: http://127.0.0.1:8000/tournaments/marketplace/')
        self.stdout.write(f'   Tournament: http://127.0.0.1:8000/tournaments/{tournament.slug}/')
        self.stdout.write(f'   Dashboard: http://127.0.0.1:8000/tournaments/{tournament.slug}/manage/')
        self.stdout.write(f'   Analytics: http://127.0.0.1:8000/tournaments/{tournament.slug}/analytics/')
        self.stdout.write(f'   Export: http://127.0.0.1:8000/tournaments/{tournament.slug}/export/')
        self.stdout.write(f'   Webhooks: http://127.0.0.1:8000/tournaments/{tournament.slug}/webhooks/')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('👤 Login Credentials:'))
        self.stdout.write(f'   Username: admin')
        self.stdout.write(f'   Password: admin123')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('📊 Demo Data:'))
        self.stdout.write(f'   Tournament: {tournament.name}')
        self.stdout.write(f'   Slug: {tournament.slug}')
        self.stdout.write(f'   Total Registrations: {total}')
        self.stdout.write(f'   Template Ratings: {TemplateRating.objects.filter(template=template).count()}')
        self.stdout.write('')
