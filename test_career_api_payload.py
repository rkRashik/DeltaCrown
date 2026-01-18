#!/usr/bin/env python
"""Generate sample JSON payloads for Valorant and eFootball to verify API structure"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.games.models import Game
from django.test import RequestFactory
from apps.user_profile.views.public_profile_views import career_tab_data_api

print("=" * 80)
print("CAREER TAB API PAYLOAD VERIFICATION")
print("=" * 80)

# Get first user with game profiles
from apps.user_profile.models import GameProfile

valorant_game = Game.objects.filter(slug='valorant').first()
efootball_game = Game.objects.filter(slug__icontains='football').first()

user = None
if valorant_game:
    gp = GameProfile.objects.filter(game=valorant_game).select_related('user').first()
    if gp:
        user = gp.user

if not user:
    # Fallback: any user with game profiles
    gp = GameProfile.objects.select_related('user').first()
    if gp:
        user = gp.user

if not user:
    print("ERROR: No users with game profiles found")
    exit(1)

print(f"\nUser: @{user.username}")
print(f"Testing with games: {[g.slug for g in Game.objects.all()[:3]]}")

factory = RequestFactory()

# Test 1: Valorant
print("\n" + "=" * 80)
print("TEST 1: VALORANT PAYLOAD")
print("=" * 80)

valorant = Game.objects.filter(slug='valorant').first()
if valorant:
    request = factory.get(f'/@{user.username}/career-data/', {'game': valorant.slug})
    request.user = user
    response = career_tab_data_api(request, user.username)
    
    if response.status_code == 200:
        data = json.loads(response.content)
        print(json.dumps(data, indent=2))
        
        # Verify structure
        print("\n" + "-" * 80)
        print("STRUCTURE VALIDATION:")
        print("-" * 80)
        
        required_keys = ['identity_slots', 'attributes_sidebar', 'stats_engine', 'affiliation_history']
        for key in required_keys:
            if key in data:
                print(f"✓ {key}: {type(data[key]).__name__}")
                if key == 'identity_slots':
                    slots = data[key]
                    print(f"  Slot A: {slots.get('A', {}).get('label')} = {slots.get('A', {}).get('value')}")
                    print(f"  Slot B: {slots.get('B', {}).get('label')} = {slots.get('B', {}).get('value')}")
                    print(f"  Slot C: {slots.get('C', {}).get('label')} = {slots.get('C', {}).get('value')}")
                    print(f"  Slot D: {slots.get('D', {}).get('label')} = {slots.get('D', {}).get('value')}")
                elif key == 'attributes_sidebar':
                    print(f"  Items: {len(data[key])}")
                    for item in data[key][:3]:
                        print(f"    - {item.get('label')}: {item.get('value')}")
                elif key == 'stats_engine':
                    engine = data[key]
                    print(f"  Category: {engine.get('category')}")
                    print(f"  Tiles: {len(engine.get('tiles', []))}")
                elif key == 'affiliation_history':
                    print(f"  Teams: {len(data[key])}")
                    for team in data[key][:2]:
                        print(f"    - {team.get('team_name')} ({team.get('team_role_label')}) - {team.get('status_badge')}")
            else:
                print(f"✗ MISSING: {key}")
    else:
        print(f"ERROR: API returned status {response.status_code}")
        print(response.content.decode())
else:
    print("Valorant game not found, skipping...")

# Test 2: eFootball
print("\n" + "=" * 80)
print("TEST 2: eFOOTBALL PAYLOAD")
print("=" * 80)

efootball = Game.objects.filter(slug__icontains='football').first()
if efootball:
    request = factory.get(f'/@{user.username}/career-data/', {'game': efootball.slug})
    request.user = user
    response = career_tab_data_api(request, user.username)
    
    if response.status_code == 200:
        data = json.loads(response.content)
        print(json.dumps(data, indent=2))
        
        # Verify structure
        print("\n" + "-" * 80)
        print("STRUCTURE VALIDATION:")
        print("-" * 80)
        
        required_keys = ['identity_slots', 'attributes_sidebar', 'stats_engine']
        for key in required_keys:
            if key in data:
                print(f"✓ {key}: {type(data[key]).__name__}")
                if key == 'identity_slots':
                    slots = data[key]
                    print(f"  Slot A: {slots.get('A', {}).get('label')} = {slots.get('A', {}).get('value')}")
                    print(f"  Slot B: {slots.get('B', {}).get('label')} = {slots.get('B', {}).get('value')}")
                    print(f"  Slot C: {slots.get('C', {}).get('label')} = {slots.get('C', {}).get('value')}")
                elif key == 'stats_engine':
                    engine = data[key]
                    print(f"  Category: {engine.get('category')} (should be 'athlete')")
            else:
                print(f"✗ MISSING: {key}")
    else:
        print(f"ERROR: API returned status {response.status_code}")
        print(response.content.decode())
else:
    print("eFootball game not found, skipping...")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
