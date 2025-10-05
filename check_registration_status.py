"""Check registration status for debugging"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament, Registration
from apps.user_profile.models import UserProfile

User = get_user_model()

print('=== USER CHECK ===')
users = User.objects.all()[:5]
for u in users:
    has_profile = hasattr(u, 'profile')
    print(f'User: {u.username} - Has Profile: {has_profile}')
    if has_profile:
        print(f'  Profile ID: {u.profile.id}')

print('\n=== TOURNAMENT CHECK ===')
t = Tournament.objects.first()
if t:
    print(f'Tournament: {t.name}')
    print(f'Slug: {t.slug}')
    print(f'Status: {t.status}')

print('\n=== REGISTRATION CHECK ===')
if t:
    regs = Registration.objects.filter(tournament=t)
    print(f'Total Registrations: {regs.count()}')
    for r in regs[:5]:
        user_name = r.user.display_name if r.user else "None"
        team_name = r.team.name if r.team else "None"
        print(f'  - User: {user_name} | Team: {team_name} | Status: {r.status}')
    
    print('\n=== CHECKING SPECIFIC USER ===')
    if users:
        test_user = users[0]
        print(f'Testing with user: {test_user.username}')
        if hasattr(test_user, 'profile'):
            user_reg = Registration.objects.filter(
                tournament=t,
                user=test_user.profile
            ).first()
            print(f'Has registration: {user_reg is not None}')
            if user_reg:
                print(f'  Status: {user_reg.status}')
                print(f'  Payment Status: {user_reg.payment_status}')
