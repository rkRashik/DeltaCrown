# apps/support/management/commands/populate_featured_faqs.py
"""
Management command to populate sample featured FAQs for homepage.

Run with:
    python manage.py populate_featured_faqs
"""
from django.core.management.base import BaseCommand
from apps.support.models import FAQ


class Command(BaseCommand):
    help = 'Populate sample featured FAQs for homepage display'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Populating featured FAQs...'))
        
        # Clear existing featured FAQs
        FAQ.objects.filter(is_featured=True).update(is_featured=False)
        
        featured_faqs = [
            {
                'category': 'TOURNAMENTS',
                'question': 'How quickly can I start competing after signing up?',
                'answer': 'Create your account in under 60 seconds, complete your profile, and you\'re ready to join tournaments immediately! Most registration-open tournaments accept entries until 1 hour before start time. Browse <a href="/tournaments/" class="text-dc-cyan hover:underline">active tournaments</a> and secure your spot today.',
                'order': 1,
                'is_featured': True,
            },
            {
                'category': 'PAYMENTS',
                'question': 'What makes DeltaCrown payment system unique for Bangladeshi players?',
                'answer': 'We accept <strong class="text-pink-400">bKash</strong>, <strong class="text-orange-400">Nagad</strong>, and <strong class="text-purple-400">Rocket</strong>—no international credit cards needed! Prize payouts are processed within <strong class="text-dc-cyan">12-24 hours</strong> directly to your mobile wallet. Zero currency conversion fees, zero barriers to entry.',
                'order': 2,
                'is_featured': True,
            },
            {
                'category': 'GENERAL',
                'question': 'Do I need a professional team to win tournaments?',
                'answer': 'Not at all! 40% of our tournament winners are <strong>solo players</strong> or newly formed teams. We offer beginner, intermediate, and pro-tier tournaments. Start small, prove your skills, and climb the leaderboards. Many DeltaCrown champions started with zero competitive experience.',
                'order': 3,
                'is_featured': True,
            },
            {
                'category': 'TECHNICAL',
                'question': 'What if I face technical issues during a match?',
                'answer': 'Every tournament has dedicated <strong class="text-dc-purple">24/7 live support</strong> via Discord and in-app chat. Technical issues are paused immediately, verified by admins, and resolved fairly. We also provide match recording requirements to prevent disputes. Your game integrity is our priority.',
                'order': 4,
                'is_featured': True,
            },
            {
                'category': 'TEAMS',
                'question': 'Can I switch teams between tournaments?',
                'answer': 'Yes! You can join multiple teams and compete in different tournaments with different rosters. However, once registered for a specific tournament, your roster is <strong>locked 24 hours before match start</strong> to ensure competitive fairness. Team loyalty badges reward consistent partnerships.',
                'order': 5,
                'is_featured': True,
            },
            {
                'category': 'RULES',
                'question': 'How does DeltaCrown ensure fair play and prevent cheating?',
                'answer': 'We use <strong class="text-dc-gold">3-layer anti-cheat system</strong>: (1) Mandatory match recordings, (2) AI-powered suspicious behavior detection, (3) Community reporting with admin verification. Cheaters are permanently banned with <strong>zero tolerance policy</strong>. Over 98% of our players maintain clean records.',
                'order': 6,
                'is_featured': True,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for faq_data in featured_faqs:
            faq, created = FAQ.objects.update_or_create(
                question=faq_data['question'],
                defaults=faq_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {faq.question[:60]}...'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'↻ Updated: {faq.question[:60]}...'))
        
        self.stdout.write(self.style.SUCCESS(
            f'\n🎉 Successfully populated {created_count} new FAQs and updated {updated_count} existing FAQs!'
        ))
        self.stdout.write(self.style.SUCCESS(
            f'All FAQs are marked as "featured" and will appear on homepage.'
        ))
        self.stdout.write(self.style.WARNING(
            f'\nTo manage FAQs, visit: /admin/support/faq/'
        ))
