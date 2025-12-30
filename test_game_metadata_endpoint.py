"""Test game metadata endpoint"""
import django
import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game
from django.test import Client

# Create test client
client = Client()

# Get a game
game = Game.objects.filter(is_active=True).first()

if not game:
    print("[ERROR] No active games found in database")
else:
    print(f"\n[OK] Testing game metadata endpoint with: {game.name} (ID={game.id})")
    
    # Test endpoint
    url = f"/profile/api/games/{game.id}/metadata/"
    print(f"URL: {url}")
    
    response = client.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        import json
        data = response.json()
        print(f"\n[SUCCESS] Response:")
        print(json.dumps(data, indent=2))
        
        if data.get('success'):
            print(f"\nMetadata Summary:")
            print(f"   Game: {data['game']['name']}")
            print(f"   Regions: {len(data.get('regions', []))} options")
            print(f"   Ranks: {len(data.get('ranks', []))} options")
            print(f"   Schema config: {list(data.get('schema', {}).keys())}")
    else:
        print(f"\n[ERROR] Response:")
        print(response.content.decode()[:500])
