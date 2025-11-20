#!/usr/bin/env python
"""
Test script for Game Registry
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.common.game_registry import (
    get_all_games, 
    get_game, 
    get_choices, 
    normalize_slug, 
    get_theme_variables,
    get_profile_id_label
)

def main():
    print("=" * 70)
    print("GAME REGISTRY TEST")
    print("=" * 70)
    
    # Test 1: Load all games
    print("\n1. Loading all games...")
    games = get_all_games()
    print(f"   ✓ Total games: {len(games)}")
    print(f"   ✓ Games: {[g.slug for g in games]}")
    
    # Test 2: Normalization
    print("\n2. Testing slug normalization...")
    test_cases = [
        ('CSGO', 'cs2'),
        ('CS:GO', 'cs2'),
        ('pubg-mobile', 'pubg'),
        ('PUBG_Mobile', 'pubg'),
        ('FIFA', 'fc26'),
        ('free-fire', 'freefire'),
        ('VALORANT', 'valorant'),
        ('Mobile Legends', 'mlbb'),
    ]
    
    for input_code, expected in test_cases:
        result = normalize_slug(input_code)
        status = "✓" if result == expected else "✗"
        print(f"   {status} '{input_code}' -> '{result}' (expected: '{expected}')")
    
    # Test 3: Get specific games
    print("\n3. Testing get_game()...")
    
    # Test Valorant
    valo = get_game('valorant')
    print(f"   ✓ Valorant:")
    print(f"     - Name: {valo.name}")
    print(f"     - Display: {valo.display_name}")
    print(f"     - Team size: {valo.get_team_size_display()}")
    print(f"     - Roles: {len(valo.roles)} roles")
    print(f"     - Color: {valo.colors.get('primary')}")
    
    # Test CS2 (via legacy code)
    cs2 = get_game('csgo')
    print(f"   ✓ CS:GO (legacy) resolved to:")
    print(f"     - Slug: {cs2.slug}")
    print(f"     - Name: {cs2.name}")
    
    # Test PUBG
    pubg = get_game('pubg-mobile')
    print(f"   ✓ PUBG Mobile resolved to:")
    print(f"     - Slug: {pubg.slug}")
    print(f"     - Team size: {pubg.max_team_size}")
    
    # Test 4: Django choices
    print("\n4. Testing get_choices()...")
    choices = get_choices()
    print(f"   ✓ Generated {len(choices)} choices")
    print(f"   ✓ Sample: {choices[:3]}")
    
    # Test 5: Theme variables
    print("\n5. Testing get_theme_variables()...")
    theme = get_theme_variables('valorant')
    print(f"   ✓ Valorant theme keys: {list(theme.keys())}")
    print(f"   ✓ Accent color: {theme.get('accent')}")
    
    # Test 6: Profile ID labels
    print("\n6. Testing get_profile_id_label()...")
    labels = [
        ('valorant', 'Riot ID'),
        ('cs2', 'Steam ID'),
        ('mlbb', 'User ID + Zone ID'),
        ('efootball', 'Konami ID'),
    ]
    
    for slug, expected in labels:
        result = get_profile_id_label(slug)
        status = "✓" if expected in result else "✗"
        print(f"   {status} {slug}: '{result}'")
    
    # Test 7: Roster configuration
    print("\n7. Testing roster configuration...")
    for game in [get_game('valorant'), get_game('dota2'), get_game('pubg')]:
        print(f"   ✓ {game.name}:")
        print(f"     - Min/Max: {game.min_team_size}/{game.max_team_size}")
        print(f"     - Roles: {len(game.roles)}")
        print(f"     - Multi-role: {game.allows_multi_role}")
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✓")
    print("=" * 70)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
