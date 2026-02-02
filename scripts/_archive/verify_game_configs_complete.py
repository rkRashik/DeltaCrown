#!/usr/bin/env python
"""
Verify game configurations including regions and roles.
"""

import os
import sys
import django

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game, GameRosterConfig, GameRole


def verify_game_configurations():
    """Display all game configurations."""
    
    print("=" * 100)
    print("GAME CONFIGURATIONS - COMPLETE DETAILS")
    print("=" * 100)
    
    games = Game.objects.filter(is_active=True).order_by('display_name')
    
    for idx, game in enumerate(games, 1):
        roster_config = game.roster_config
        
        print(f"\n{idx}. {game.display_name} ({game.slug})")
        print(f"   {'⭐ FEATURED' if game.is_featured else '   '}")
        print(f"   Category: {game.get_category_display()} | Type: {game.get_game_type_display()}")
        print(f"   Platforms: {', '.join(game.platforms)}")
        print(f"   Developer: {game.developer}")
        print(f"   Colors: {game.primary_color} / {game.secondary_color}")
        
        # Team Size
        print(f"\n   📊 Team Configuration:")
        print(f"      Team Size: {roster_config.min_team_size}-{roster_config.max_team_size} players")
        print(f"      Substitutes: {roster_config.min_substitutes}-{roster_config.max_substitutes}")
        print(f"      Total Roster: {roster_config.min_roster_size}-{roster_config.max_roster_size}")
        
        # Regions
        if roster_config.has_regions and roster_config.available_regions:
            print(f"\n   🌍 Available Regions ({len(roster_config.available_regions)}):")
            # Display in columns
            regions = roster_config.available_regions
            for i in range(0, len(regions), 3):
                region_batch = regions[i:i+3]
                region_strs = [f"{r['code']}: {r['name']}" for r in region_batch]
                print(f"      {' | '.join(region_strs)}")
        else:
            print(f"\n   🌍 Available Regions: None (Global game)")
        
        # Roles
        roles = game.roles.filter(is_active=True).order_by('order')
        if roster_config.has_roles and roles.exists():
            print(f"\n   👥 Game Roles ({roles.count()}):")
            for role in roles:
                print(f"      {role.icon} {role.role_name} ({role.role_code})")
                print(f"         {role.description}")
                if role.color:
                    print(f"         Color: {role.color}")
        else:
            print(f"\n   👥 Game Roles: None (1v1 game or no defined roles)")
        
        # Player Identity
        identity_configs = game.identity_configs.all().order_by('order')
        if identity_configs.exists():
            print(f"\n   🎮 Player Identity Fields:")
            for config in identity_configs:
                required = "✓" if config.is_required else "○"
                print(f"      [{required}] {config.display_name}: {config.placeholder or config.field_name}")
        
        print(f"\n   {'-' * 96}")
    
    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    
    total_games = games.count()
    featured_games = games.filter(is_featured=True).count()
    games_with_regions = GameRosterConfig.objects.filter(has_regions=True).count()
    games_with_roles = GameRosterConfig.objects.filter(has_roles=True).count()
    total_roles = GameRole.objects.filter(is_active=True).count()
    
    print(f"\n📊 Statistics:")
    print(f"   Total Games: {total_games}")
    print(f"   Featured Games: {featured_games}")
    print(f"   Games with Regions: {games_with_regions}")
    print(f"   Games with Roles: {games_with_roles}")
    print(f"   Total Roles Defined: {total_roles}")
    
    # Category breakdown
    print(f"\n📂 By Category:")
    for category_code, category_name in Game.CATEGORY_CHOICES:
        count = games.filter(category=category_code).count()
        if count > 0:
            print(f"   {category_name}: {count} games")
    
    # Platform breakdown
    print(f"\n💻 By Platform:")
    pc_games = [g for g in games if 'PC' in g.platforms]
    console_games = [g for g in games if 'Console' in g.platforms]
    mobile_games = [g for g in games if 'Mobile' in g.platforms]
    multi_platform = [g for g in games if len(g.platforms) > 1]
    
    print(f"   PC: {len(pc_games)} games")
    print(f"   Console: {len(console_games)} games")
    print(f"   Mobile: {len(mobile_games)} games")
    print(f"   Multi-Platform: {len(multi_platform)} games")
    
    print("\n" + "=" * 100)


if __name__ == '__main__':
    verify_game_configurations()
