"""Find active tournament and create test registration"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament, Registration
from apps.user_profile.models import UserProfile

User = get_user_model()

print('=== FINDING TOURNAMENTS ===')
tournaments = Tournament.objects.all()
for t in tournaments[:10]:
    reg_count = Registration.objects.filter(tournament=t).count()
    print(f'{t.name} (slug: {t.slug}) - Status: {t.status} - Registrations: {reg_count}')

print('\n=== FINDING EFOOTBALL TOURNAMENT ===')
efootball = Tournament.objects.filter(slug='efootball-champions').first()
if efootball:
    print(f'Found: {efootball.name}')
    print(f'Status: {efootball.status}')
    print(f'Format: {efootball.format}')
    print(f'Tournament Type: {efootball.tournament_type}')
    
    regs = Registration.objects.filter(tournament=efootball)
    print(f'Registrations: {regs.count()}')
    
    # Check if player02 has registration
    player02 = User.objects.filter(username='player02').first()
    if player02 and hasattr(player02, 'profile'):
        print(f'\nChecking player02 (Profile ID: {player02.profile.id})')
        player_reg = Registration.objects.filter(
            tournament=efootball,
            user=player02.profile
        ).first()
        print(f'Has registration: {player_reg is not None}')
        
        if not player_reg:
            print('\n=== CREATING TEST REGISTRATION ===')
            # Create a test registration
            reg = Registration.objects.create(
                tournament=efootball,
                user=player02.profile,
                status='CONFIRMED',
                payment_status='verified'
            )
            print(f'Created registration ID: {reg.id}')
            print(f'Status: {reg.status}')
            print(f'Payment Status: {reg.payment_status}')
        else:
            print(f'Existing registration - Status: {player_reg.status}')
else:
    print('eFootball Champions tournament not found!')
