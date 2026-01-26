"""
Management command to create a demo organization for testing.
Creates an organization with slug 'syntax' for immediate testing.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.organizations.models.organization import Organization

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates or updates a demo organization (slug: syntax) for testing'

    def handle(self, *args, **options):
        # Get or create CEO user
        ceo = User.objects.filter(is_superuser=True).first()
        if not ceo:
            ceo = User.objects.first()
        if not ceo:
            self.stdout.write(self.style.WARNING('No users found. Creating syntax_admin...'))
            ceo = User.objects.create_user(
                username='syntax_admin',
                email='admin@syntax.gg',
                password='demo123',
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Created user: {ceo.username}'))

        # Create or update organization
        org, created = Organization.objects.update_or_create(
            slug='syntax',
            defaults={
                'name': 'SYNTAX ESPORTS',
                'ceo': ceo,
                'description': 'Dominating the South Asian competitive scene. Home to champions in Valorant, CS2, and Mobile Legends. We build legacies, not just teams. #RunTheCode',
                'location': 'Dhaka, Bangladesh',
                'website': 'https://syntax.gg',
                'twitter_handle': 'syntaxesports',
                'is_verified': True,
                'verification_date': timezone.now(),
                'is_active': True,
                'enforce_brand': True,
                'founded_date': timezone.now().date(),
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'✓ Created organization: {org.name} (slug: {org.slug})'))
        else:
            self.stdout.write(self.style.SUCCESS(f'✓ Updated organization: {org.name} (slug: {org.slug})'))

        # Create OrganizationProfile if model exists
        try:
            from apps.organizations.models.profile import OrganizationProfile
            profile, profile_created = OrganizationProfile.objects.get_or_create(
                organization=org,
                defaults={
                    'manifesto': 'We are SYNTAX. We run the code.',
                }
            )
            if profile_created:
                self.stdout.write(self.style.SUCCESS('✓ Created OrganizationProfile'))
        except ImportError:
            pass  # Profile model doesn't exist yet

        # Create OrganizationRanking if model exists
        try:
            from apps.organizations.models.ranking import OrganizationRanking
            ranking, ranking_created = OrganizationRanking.objects.get_or_create(
                organization=org,
                defaults={
                    'empire_score': 1000,
                    'global_rank': 1,
                    'total_trophies': 42,
                }
            )
            if ranking_created:
                self.stdout.write(self.style.SUCCESS('✓ Created OrganizationRanking'))
        except (ImportError, Exception):
            pass  # Ranking model doesn't exist or error occurred

        self.stdout.write(self.style.SUCCESS('\n🚀 Demo organization ready!'))
        self.stdout.write(self.style.SUCCESS(f'   Visit: /orgs/{org.slug}/'))
        self.stdout.write(self.style.SUCCESS(f'   CEO: {ceo.username}'))
