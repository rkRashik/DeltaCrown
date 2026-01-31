#!/usr/bin/env python
"""
Test script to reproduce validation endpoint failures.
Run with: python test_validation_endpoints.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from apps.games.models import Game

User = get_user_model()

def test_validation_endpoints():
    """Test validation endpoints and capture actual responses."""
    
    print("="*80)
    print("PHASE 0: REPRODUCING VALIDATION ENDPOINT FAILURES")
    print("="*80)
    
    # Use first available user
    user = User.objects.first()
    if not user:
        print("X Admin user not found! Please create one with: python manage.py createsuperuser")
        return
    print(f"OK Using user: {user.username} (id={user.id})")
    
    # Check if game exists
    try:
        game = Game.objects.filter(is_active=True).first()
        if not game:
            print("X No active games in database!")
            return
        game_slug = game.slug
        print(f"OK Game exists: {game_slug} (id={game.id})")
    except Exception as e:
        print(f"X Error checking games: {e}")
        return
    
    # Create authenticated client
    client = Client()
    client.force_login(user)
    
    print("\n" + "="*80)
    print("TEST 1: validate-name endpoint")
    print("="*80)
    
    url = f'/api/vnext/teams/validate-name/?name=Null+Boyz&game_slug={game_slug}&mode=independent'
    print(f"GET {url}")
    response = client.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.content.decode('utf-8')[:500]}")
    
    if response.status_code == 500:
        print("\n!! FAILURE: validate-name returned 500")
        print("Check server logs above for traceback")
    else:
        print(f"\nOK validate-name returned {response.status_code}")
        if response.status_code == 200:
            print(f"  JSON: {response.json()}")
    
    print("\n" + "="*80)
    print("TEST 2: validate-tag endpoint")
    print("="*80)
    
    url = f'/api/vnext/teams/validate-tag/?tag=NULL&game_slug={game_slug}&mode=independent'
    print(f"GET {url}")
    response = client.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.content.decode('utf-8')[:500]}")
    
    if response.status_code == 500:
        print("\n!! FAILURE: validate-tag returned 500")
        print("Check server logs above for traceback")
    else:
        print(f"\nOK validate-tag returned {response.status_code}")
        if response.status_code == 200:
            print(f"  JSON: {response.json()}")
    
    # TEST 3: Create team endpoint
    print("\n" + "="*80)
    print("TEST 3: create-team endpoint")
    print("="*80)
    
    create_payload = {
        'name': 'Test Team Phase0',
        'tag': 'TP0',
        'game_slug': game_slug,
        'region': 'Bangladesh',
        'mode': 'independent'  # Independent team (no org)
    }
    
    url = '/api/vnext/teams/create/'
    print(f"POST {url}")
    print(f"Payload: {create_payload}")
    
    import json
    response = client.post(
        url,
        data=json.dumps(create_payload),
        content_type='application/json'
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.content.decode('utf-8')[:500]}")
    
    if response.status_code == 201:
        print("\nOK create-team returned 201")
        response_data = json.loads(response.content)
        print(f"  Created team: {response_data.get('name')} ({response_data.get('slug')})")
    else:
        print(f"\n!! FAILURE: create-team returned {response.status_code}")
        print("  Check server logs above for traceback")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("If any endpoint returned 500, check the console output above for:")
    print("  - The actual exception type and message")
    print("  - The Team model being used (should be organizations.models.Team)")
    print("  - The db_table (should be 'organizations_team')")
    print("  - The SQL query being executed")
    print("="*80)

if __name__ == '__main__':
    test_validation_endpoints()
