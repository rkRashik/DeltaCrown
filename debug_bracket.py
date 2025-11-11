import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'deltacrown.settings'

import django
django.setup()

from rest_framework.test import APIClient
from apps.tournaments.models import Tournament, Game, Registration, Bracket
from apps.accounts.models import User
from django.utils import timezone
from datetime import timedelta
import traceback
import random

# Clean up test data
print("Cleaning up test data...")
Tournament.objects.filter(slug__startswith='test-debug').delete()
User.objects.filter(username__startswith='testuser').delete()

# Create test data
game, _ = Game.objects.get_or_create(
    name='Valorant',
    defaults={
        'slug': 'valorant',
        'default_team_size': 5,
        'profile_id_field': 'riot_id',
        'default_result_type': 'map_score',
        'is_active': True
    }
)

slug = f'test-debug-{random.randint(1000, 9999)}'
organizer = User.objects.create_user(
    username=f'testuser{random.randint(1000, 9999)}',
    email=f'testuser{random.randint(1000, 9999)}@test.com',
    password='pass'
)

t = Tournament.objects.create(
    name='Test Debug',
    slug=slug,
    description='Test',
    organizer=organizer,
    game=game,
    format='single_elimination',
    participation_type='solo',
    status='registration_open',
    tournament_start=timezone.now() + timedelta(days=7),
    registration_start=timezone.now() - timedelta(days=1),
    registration_end=timezone.now() + timedelta(days=1),
    max_participants=8,
    min_participants=2
)

for i in range(4):
    u = User.objects.create_user(
        username=f'testuser{random.randint(10000, 99999)}',
        email=f'testuser{random.randint(10000, 99999)}@test.com',
        password='pass'
    )
    Registration.objects.create(
        tournament=t,
        user=u,
        status='confirmed',
        checked_in=True,
        checked_in_at=timezone.now()
    )

# Test the API
client = APIClient()
client.force_authenticate(user=organizer)

print(f"Tournament ID: {t.id}")
print(f"Tournament format: {t.format}")
print(f"Confirmed registrations: {Registration.objects.filter(tournament=t, status='confirmed').count()}")

try:
    r = client.post(f'/api/tournaments/brackets/tournaments/{t.id}/generate/', {}, format='json')
    print(f'\nStatus: {r.status_code}')
    if hasattr(r, 'data'):
        print(f'Data: {r.data}')
    else:
        print(f'Content: {r.content.decode()}')
except Exception as e:
    print(f'\nException: {type(e).__name__}: {e}')
    traceback.print_exc()
