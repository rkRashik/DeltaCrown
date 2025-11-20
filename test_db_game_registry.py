#!/usr/bin/env python
"""
Test script for Database-First Game Registry
Verifies that Django admin is now the primary source for game specs.
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.common.game_registry import get_all_games, get_game

def test_registry():
    print("=" * 70)
    print("DATABASE-FIRST GAME REGISTRY TEST")
    print("=" * 70)
    print()
    
    games = get_all_games()
    print(f"✅ Total games loaded: {len(games)}")
    print()
    
    # Separate DB games from fallback games
    db_games = [g for g in games if g.database_id]
    fallback_games = [g for g in games if not g.database_id]
    
    print(f"📊 Games from DATABASE (editable via Django admin): {len(db_games)}")
    print(f"📦 Games from ASSETS (fallback, read-only): {len(fallback_games)}")
    print()
    
    if db_games:
        print("-" * 70)
        print("DATABASE GAMES (Primary Source)")
        print("-" * 70)
        for game in sorted(db_games, key=lambda g: g.name):
            icon_status = "✅" if game.icon else "❌ MISSING"
            print(f"{game.name:30} ({game.slug:10}) | DB ID: {game.database_id:3} | Icon: {icon_status}")
            print(f"  → Profile Field: {game.profile_id_field}")
            print(f"  → Team Size: {game.min_team_size}v{game.max_team_size}")
            print(f"  → Result Type: {game.result_type}")
            if game.description:
                desc = game.description[:60] + "..." if len(game.description) > 60 else game.description
                print(f"  → Description: {desc}")
            print()
    
    if fallback_games:
        print("-" * 70)
        print("FALLBACK GAMES (Asset-Based, Not in Database)")
        print("-" * 70)
        print("⚠️ These games are NOT editable via Django admin!")
        print("⚠️ To make them editable, add them to the database.")
        print()
        for game in sorted(fallback_games, key=lambda g: g.name):
            print(f"{game.name:30} ({game.slug:10})")
        print()
    
    # Test a specific game
    print("-" * 70)
    print("DETAILED SPEC TEST (ALL NEW FIELDS)")
    print("-" * 70)
    if db_games:
        test_game = db_games[0]
        print(f"Testing: {test_game.name}")
        print(f"  Slug: {test_game.slug}")
        print(f"  Display Name: {test_game.display_name}")
        print(f"  Database ID: {test_game.database_id}")
        print()
        print("  📸 MEDIA FIELDS (NEW):")
        print(f"    Icon: {test_game.icon if test_game.icon else '❌ MISSING IN DB (using asset)'}")
        print(f"    Banner: {test_game.banner if test_game.banner else '❌ MISSING IN DB (using asset)'}")
        print(f"    Logo: {test_game.logo if test_game.logo else '❌ MISSING IN DB (using asset)'}")
        print(f"    Card: {test_game.card if test_game.card else '❌ MISSING IN DB (using asset)'}")
        print()
        print("  🎨 PRESENTATION FIELDS (NEW):")
        print(f"    Primary Color: {test_game.colors.get('primary', 'Not set')}")
        print(f"    Secondary Color: {test_game.colors.get('secondary', 'Not set')}")
        print(f"    Category: {test_game.category}")
        print(f"    Platform: {', '.join(test_game.platforms)}")
        print()
        print("  👥 TEAM STRUCTURE (NEW):")
        print(f"    Min Team Size: {test_game.min_team_size}")
        print(f"    Max Team Size: {test_game.max_team_size}")
        print(f"    Max Substitutes: {test_game.max_substitutes}")
        print()
        print("  🎮 ROLES (NEW):")
        print(f"    Roles: {', '.join(test_game.roles) if test_game.roles else 'None defined in DB (using roster config)'}")
        print()
        print("  📊 RESULT LOGIC (NEW):")
        print(f"    Result Type: {test_game.result_type}")
        print(f"    Result Format: {test_game.result_format if test_game.result_format else 'Not defined'}")
        print()
        print("  🔧 OTHER FIELDS:")
        print(f"    Profile ID Field: {test_game.profile_id_field}")
        print(f"    Is Active: {test_game.is_active}")
        print(f"    Description: {test_game.description[:80] + '...' if test_game.description and len(test_game.description) > 80 else (test_game.description or 'Not set')}")
    
    print()
    print("=" * 70)
    print("✅ TEST COMPLETE")
    print("=" * 70)
    print()
    print("📝 Summary:")
    print(f"  - {len(db_games)} games editable via Django admin")
    print(f"  - {len(fallback_games)} games using asset fallback")
    print()
    print("💡 To make more games editable:")
    print("  1. Go to Django admin → Tournaments → Games")
    print("  2. Add new Game entries with canonical slugs")
    print("  3. Registry will automatically use DB data as primary source")
    print()

if __name__ == '__main__':
    test_registry()
