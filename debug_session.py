"""Debug current user session"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.utils import timezone

User = get_user_model()

print('=== ACTIVE SESSIONS ===')
active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
print(f'Total active sessions: {active_sessions.count()}')

for session in active_sessions[:5]:
    data = session.get_decoded()
    user_id = data.get('_auth_user_id')
    if user_id:
        try:
            user = User.objects.get(id=user_id)
            has_profile = hasattr(user, 'profile')
            print(f'\nSession User: {user.username}')
            print(f'  Has Profile: {has_profile}')
            if has_profile:
                print(f'  Profile ID: {user.profile.id}')
            print(f'  Expires: {session.expire_date}')
        except User.DoesNotExist:
            print(f'\nSession with invalid user ID: {user_id}')

print('\n\n=== HOW TO TEST ===')
print('1. Open browser at http://localhost:8000/')
print('2. Login as: player02')
print('3. Visit: http://localhost:8000/tournaments/t/efootball-champions/')
print('4. You should see "ENTER WAR ROOM" button')
print('5. You should see "You\'re Registered" badge')
print('6. You should see "Confirmed" badge')
