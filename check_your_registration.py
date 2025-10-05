"""Check rkrashik registration"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament, Registration
from apps.user_profile.models import UserProfile

User = get_user_model()

print('=== CHECKING YOUR USER (rkrashik) ===')
user = User.objects.filter(username='rkrashik').first()
if user:
    print(f'User: {user.username}')
    print(f'Has Profile: {hasattr(user, "profile")}')
    
    if hasattr(user, 'profile'):
        print(f'Profile ID: {user.profile.id}')
        print(f'Display Name: {user.profile.display_name}')
        
        # Check eFootball tournament
        efootball = Tournament.objects.filter(slug='efootball-champions').first()
        if efootball:
            print(f'\n=== CHECKING EFOOTBALL REGISTRATION ===')
            print(f'Tournament: {efootball.name}')
            
            user_reg = Registration.objects.filter(
                tournament=efootball,
                user=user.profile
            ).first()
            
            if user_reg:
                print(f'✅ YOU HAVE A REGISTRATION!')
                print(f'   Status: {user_reg.status}')
                print(f'   Payment Status: {user_reg.payment_status}')
                print(f'   Created: {user_reg.created_at}')
                
                print(f'\n✅ You should see:')
                print(f'   - "ENTER WAR ROOM" button')
                print(f'   - "You\'re Registered" badge')
                if user_reg.status == 'CONFIRMED':
                    print(f'   - "Confirmed" badge (green)')
                else:
                    print(f'   - "Payment Pending" badge (yellow)')
            else:
                print(f'❌ NO REGISTRATION FOUND')
                print(f'\nCreating registration for you...')
                
                reg = Registration.objects.create(
                    tournament=efootball,
                    user=user.profile,
                    status='CONFIRMED',
                    payment_status='verified'
                )
                print(f'✅ Created registration ID: {reg.id}')
                print(f'\nNow refresh the page: http://localhost:8000/tournaments/t/efootball-champions/')
else:
    print('User rkrashik not found!')
