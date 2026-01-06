"""
Phase 9A-17: Test passport creation with DEBUG tracing
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.games.models import Game
from apps.user_profile.models import GameProfile
import json

User = get_user_model()

# Get or create test user
user, _ = User.objects.get_or_create(
    username='testuser_phase9a17',
    defaults={'email': 'test@example.com'}
)
user.set_password('testpass123')
user.save()

print(f"[OK] Test user: {user.username}")

# Clean up any existing eFootball passports
GameProfile.objects.filter(user=user, game__slug='efootball').delete()
print("[OK] Cleaned existing eFootball passports")

# Get eFootball game
efootball = Game.objects.filter(slug='efootball').first()
if not efootball:
    print("[ERROR] eFootball game not found! Available games:")
    for g in Game.objects.filter(is_active=True):
        print(f"  - {g.slug}: {g.display_name}")
    exit(1)

print(f"[OK] Game: {efootball.display_name} ({efootball.slug})")

# Test payloads
test_payloads = [
    {
        "name": "Valid eFootball passport",
        "payload": {
            "game_id": efootball.id,
            "metadata": {
                "konami_id": "TestUser123",
                "efootball_id": "1234567890",
                "platform": "pc",
                "username": "TestPlayer"
            }
        }
    },
    {
        "name": "Missing required field (konami_id)",
        "payload": {
            "game_id": efootball.id,
            "metadata": {
                "efootball_id": "1234567890",
                "platform": "pc"
            }
        }
    },
    {
        "name": "Invalid efootball_id (not 10 digits)",
        "payload": {
            "game_id": efootball.id,
            "metadata": {
                "konami_id": "TestUser123",
                "efootball_id": "123",  # Too short
                "platform": "pc"
            }
        }
    }
]

# Simulate API call
from django.test import RequestFactory
from apps.user_profile.views.game_passports_api import create_game_passport_api

factory = RequestFactory()

for test in test_payloads:
    print(f"\n{'='*60}")
    print(f"TEST: {test['name']}")
    print(f"Payload: {json.dumps(test['payload'], indent=2)}")
    print('='*60)
    
    request = factory.post(
        '/profile/api/game-passports/create/',
        data=json.dumps(test['payload']),
        content_type='application/json'
    )
    request.user = user
    
    response = create_game_passport_api(request)
    
    print(f"Status: {response.status_code}")
    
    try:
        response_data = json.loads(response.content)
        print(f"Response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code == 500:
            print("\n[ERROR] 500 ERROR DETAILS:")
            if 'traceback' in response_data:
                print(response_data['traceback'])
    except:
        print(f"Raw response: {response.content}")
    
    # Clean up created passport
    GameProfile.objects.filter(user=user, game=efootball).delete()

print("\n" + "="*60)
print("[OK] All tests complete")
