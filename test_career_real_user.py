#!/usr/bin/env python
"""Test Career Tab AJAX endpoint with real user data."""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import GameProfile
from django.test import RequestFactory
from apps.user_profile.views.public_profile_views import career_tab_data_api

# Find any user with at least 1 passport
gp = GameProfile.objects.select_related('user', 'game').first()
if not gp:
    print("ERROR: No GameProfile records found in database")
    exit(1)

test_user = gp.user
game_slug = gp.game.slug

print(f"Testing Career Tab AJAX with:")
print(f"  User: @{test_user.username}")
print(f"  Game: {game_slug}")
print(f"  URL: /@{test_user.username}/career-data/?game={game_slug}")
print(f"\n{'='*60}\n")

# Simulate AJAX request
factory = RequestFactory()
request = factory.get(f'/@{test_user.username}/career-data/', {'game': game_slug})
request.user = test_user

try:
    response = career_tab_data_api(request, username=test_user.username)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = json.loads(response.content)
        print(f"\nJSON Response:")
        print(json.dumps(data, indent=2))
        
        # Validate structure
        print(f"\n{'='*60}")
        print("VALIDATION:")
        print(f"  ✓ passport_card: {bool(data.get('passport_card'))}")
        print(f"  ✓ standing: {bool(data.get('standing'))}")
        print(f"  ✓ team_history: {len(data.get('team_history', []))} records")
        print(f"  ✓ achievements: {len(data.get('achievements', []))} records")
        print(f"  ✓ game_selector: {len(data.get('game_selector', []))} games")
    else:
        print(f"ERROR: {response.content.decode()}")
except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
