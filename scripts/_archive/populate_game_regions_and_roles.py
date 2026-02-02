#!/usr/bin/env python
"""
Populate game regions and roles for all games in the database.
"""

import os
import sys
import django

from dotenv import load_dotenv
load_dotenv()


# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game, GameRosterConfig, GameRole

# ═══════════════════════════════════════════════════════════════════════════
# REGION CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════════

GAME_REGIONS = {
    'valorant': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'LATAM', 'name': 'Latin America'},
        {'code': 'BR', 'name': 'Brazil'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'TR', 'name': 'Turkey'},
        {'code': 'CIS', 'name': 'CIS'},
        {'code': 'MENA', 'name': 'Middle East & North Africa'},
        {'code': 'KR', 'name': 'Korea'},
        {'code': 'JP', 'name': 'Japan'},
        {'code': 'APAC', 'name': 'Asia-Pacific'},
        {'code': 'OCE', 'name': 'Oceania'},
        {'code': 'SA', 'name': 'South Asia'},
    ],
    
    'counter-strike-2': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'CIS', 'name': 'CIS'},
        {'code': 'MENA', 'name': 'Middle East & North Africa'},
        {'code': 'ASIA', 'name': 'Asia'},
        {'code': 'CN', 'name': 'China'},
        {'code': 'OCE', 'name': 'Oceania'},
    ],
    
    'dota-2': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'WEU', 'name': 'Western Europe'},
        {'code': 'EEU', 'name': 'Eastern Europe'},
        {'code': 'CN', 'name': 'China'},
        {'code': 'SEA', 'name': 'Southeast Asia'},
    ],
    
    'mobile-legends': [
        {'code': 'SEA', 'name': 'Southeast Asia'},
        {'code': 'ID', 'name': 'Indonesia'},
        {'code': 'MY-SG', 'name': 'Malaysia/Singapore'},
        {'code': 'PH', 'name': 'Philippines'},
        {'code': 'TH', 'name': 'Thailand'},
        {'code': 'VN', 'name': 'Vietnam'},
        {'code': 'MM', 'name': 'Myanmar'},
        {'code': 'BD', 'name': 'Bangladesh'},
        {'code': 'IN', 'name': 'India'},
        {'code': 'LATAM', 'name': 'Latin America'},
        {'code': 'NA', 'name': 'North America'},
    ],
    
    'pubg-mobile': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'AS', 'name': 'Asia'},
        {'code': 'KR-JP', 'name': 'Korea/Japan'},
        {'code': 'SEA', 'name': 'Southeast Asia'},
        {'code': 'MENA', 'name': 'Middle East & North Africa'},
    ],
    
    'free-fire': [
        {'code': 'SEA', 'name': 'Southeast Asia'},
        {'code': 'ID', 'name': 'Indonesia'},
        {'code': 'TH', 'name': 'Thailand'},
        {'code': 'VN', 'name': 'Vietnam'},
        {'code': 'BD', 'name': 'Bangladesh'},
        {'code': 'IN', 'name': 'India'},
        {'code': 'LATAM', 'name': 'Latin America'},
        {'code': 'BR', 'name': 'Brazil'},
        {'code': 'NA', 'name': 'North America'},
        {'code': 'ME', 'name': 'Middle East'},
    ],
    
    'call-of-duty-mobile': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'LATAM', 'name': 'Latin America'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'MEA', 'name': 'Middle East & Africa'},
        {'code': 'IN', 'name': 'India'},
        {'code': 'SEA', 'name': 'Southeast Asia'},
        {'code': 'JP', 'name': 'Japan'},
        {'code': 'KR', 'name': 'Korea'},
        {'code': 'OCE', 'name': 'Oceania'},
    ],
    
    'efootball': [
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'ASIA', 'name': 'Asia'},
        {'code': 'ME', 'name': 'Middle East'},
        {'code': 'OCE', 'name': 'Oceania'},
        {'code': 'GLOBAL', 'name': 'Global (Cross-Platform)'},
    ],
    
    'ea-sports-fc-26': [
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'ASIA', 'name': 'Asia'},
        {'code': 'ME', 'name': 'Middle East'},
        {'code': 'OCE', 'name': 'Oceania'},
        {'code': 'GLOBAL', 'name': 'Global (Cross-Platform)'},
    ],
    
    'rainbow-six-siege': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'LATAM', 'name': 'Latin America'},
        {'code': 'BR', 'name': 'Brazil'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'APAC', 'name': 'Asia-Pacific'},
        {'code': 'MENA', 'name': 'Middle East & North Africa'},
    ],
    
    'rocket-league': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'OCE', 'name': 'Oceania'},
        {'code': 'ASIA', 'name': 'Asia'},
        {'code': 'MENA', 'name': 'Middle East & North Africa'},
        {'code': 'SAM', 'name': 'South America'},
    ],
}

# ═══════════════════════════════════════════════════════════════════════════
# ROLE CONFIGURATIONS
# ═══════════════════════════════════════════════════════════════════════════

GAME_ROLES = {
    'valorant': [
        {'name': 'Duelist', 'code': 'DUE', 'icon': '⚔️', 'color': '#ff4654', 'description': 'Entry fragger, self-sufficient aggressive player', 'order': 1},
        {'name': 'Controller', 'code': 'CTRL', 'icon': '🌫️', 'color': '#7b68ee', 'description': 'Smoke/vision blocker, map control', 'order': 2},
        {'name': 'Initiator', 'code': 'INIT', 'icon': '⚡', 'color': '#ffd700', 'description': 'Info gatherer, team setup', 'order': 3},
        {'name': 'Sentinel', 'code': 'SENT', 'icon': '🛡️', 'color': '#00bfa5', 'description': 'Defender, site anchor', 'order': 4},
    ],
    
    'counter-strike-2': [
        {'name': 'AWPer', 'code': 'AWP', 'icon': '🎯', 'color': '#f5a623', 'description': 'Primary sniper, long-range threat', 'order': 1},
        {'name': 'Entry Fragger', 'code': 'ENTRY', 'icon': '⚔️', 'color': '#ff4654', 'description': 'First contact, opening kills', 'order': 2},
        {'name': 'Support', 'code': 'SUP', 'icon': '🤝', 'color': '#00bfa5', 'description': 'Utility user, team support', 'order': 3},
        {'name': 'Lurker', 'code': 'LURK', 'icon': '👁️', 'color': '#9c27b0', 'description': 'Map control, flank watcher', 'order': 4},
        {'name': 'IGL', 'code': 'IGL', 'icon': '🧠', 'color': '#2196f3', 'description': 'In-game leader, shot caller', 'order': 5},
    ],
    
    'dota-2': [
        {'name': 'Hard Carry (Pos 1)', 'code': 'POS1', 'icon': '👑', 'color': '#ffd700', 'description': 'Late-game carry, farm priority', 'order': 1},
        {'name': 'Mid (Pos 2)', 'code': 'POS2', 'icon': '⚡', 'color': '#ff4654', 'description': 'Solo mid, tempo controller', 'order': 2},
        {'name': 'Offlane (Pos 3)', 'code': 'POS3', 'icon': '⚔️', 'color': '#7b68ee', 'description': 'Initiator, space creator', 'order': 3},
        {'name': 'Soft Support (Pos 4)', 'code': 'POS4', 'icon': '🤝', 'color': '#00bfa5', 'description': 'Roaming support, utility', 'order': 4},
        {'name': 'Hard Support (Pos 5)', 'code': 'POS5', 'icon': '🛡️', 'color': '#2196f3', 'description': 'Ward bitch, babysitter', 'order': 5},
    ],
    
    'mobile-legends': [
        {'name': 'Tank', 'code': 'TNK', 'icon': '🛡️', 'color': '#607d8b', 'description': 'Frontline, damage absorber', 'order': 1},
        {'name': 'Fighter', 'code': 'FTR', 'icon': '⚔️', 'color': '#ff5722', 'description': 'Melee DPS, sustain fighter', 'order': 2},
        {'name': 'Assassin', 'code': 'ASN', 'icon': '🗡️', 'color': '#9c27b0', 'description': 'Burst damage, backline diver', 'order': 3},
        {'name': 'Mage', 'code': 'MAG', 'icon': '🔮', 'color': '#2196f3', 'description': 'Magic damage, crowd control', 'order': 4},
        {'name': 'Marksman', 'code': 'MM', 'icon': '🏹', 'color': '#ffd700', 'description': 'ADC, ranged physical DPS', 'order': 5},
        {'name': 'Support', 'code': 'SUP', 'icon': '💚', 'color': '#00bfa5', 'description': 'Healer, buffer, team utility', 'order': 6},
    ],
    
    'call-of-duty-mobile': [
        {'name': 'Slayer', 'code': 'SLY', 'icon': '🔫', 'color': '#ff4654', 'description': 'Main fragger, aggressive player', 'order': 1},
        {'name': 'Objective', 'code': 'OBJ', 'icon': '🎯', 'color': '#2196f3', 'description': 'Hardpoint/Dom player', 'order': 2},
        {'name': 'Support', 'code': 'SUP', 'icon': '🤝', 'color': '#00bfa5', 'description': 'Utility, team player', 'order': 3},
        {'name': 'Sniper', 'code': 'SNP', 'icon': '🎯', 'color': '#9c27b0', 'description': 'Long-range specialist', 'order': 4},
        {'name': 'Flex', 'code': 'FLX', 'icon': '🔄', 'color': '#ffd700', 'description': 'Adaptable, fills gaps', 'order': 5},
    ],
    
    'free-fire': [
        {'name': 'Rusher', 'code': 'RSH', 'icon': '⚡', 'color': '#ff4654', 'description': 'Aggressive pusher, early fights', 'order': 1},
        {'name': 'Sniper', 'code': 'SNP', 'icon': '🎯', 'color': '#2196f3', 'description': 'Long-range eliminations', 'order': 2},
        {'name': 'Support', 'code': 'SUP', 'icon': '💚', 'color': '#00bfa5', 'description': 'Healer, team support', 'order': 3},
        {'name': 'IGL', 'code': 'IGL', 'icon': '🧠', 'color': '#ffd700', 'description': 'Squad leader, shot caller', 'order': 4},
    ],
    
    'pubg-mobile': [
        {'name': 'Fragger', 'code': 'FRG', 'icon': '🔫', 'color': '#ff4654', 'description': 'Aggressive gunfighter', 'order': 1},
        {'name': 'Sniper', 'code': 'SNP', 'icon': '🎯', 'color': '#2196f3', 'description': 'Long-range specialist', 'order': 2},
        {'name': 'Support', 'code': 'SUP', 'icon': '💚', 'color': '#00bfa5', 'description': 'Medic, utility player', 'order': 3},
        {'name': 'IGL', 'code': 'IGL', 'icon': '🧠', 'color': '#ffd700', 'description': 'Team captain, decision maker', 'order': 4},
    ],
    
    'rainbow-six-siege': [
        {'name': 'Entry Fragger', 'code': 'ENTRY', 'icon': '⚔️', 'color': '#ff4654', 'description': 'First to push, aggressive', 'order': 1},
        {'name': 'Support', 'code': 'SUP', 'icon': '🤝', 'color': '#00bfa5', 'description': 'Utility player, team support', 'order': 2},
        {'name': 'Hard Breach', 'code': 'BREACH', 'icon': '💥', 'color': '#ff9800', 'description': 'Wall breacher (Thermite, Hibana)', 'order': 3},
        {'name': 'Flex', 'code': 'FLX', 'icon': '🔄', 'color': '#9c27b0', 'description': 'Adaptable, fills roles', 'order': 4},
        {'name': 'IGL', 'code': 'IGL', 'icon': '🧠', 'color': '#2196f3', 'description': 'In-game leader, strategy', 'order': 5},
    ],
    
    'rocket-league': [
        {'name': 'Striker', 'code': 'STR', 'icon': '⚽', 'color': '#ff4654', 'description': 'Offensive player, goal scorer', 'order': 1},
        {'name': 'Midfield', 'code': 'MID', 'icon': '🔄', 'color': '#ffd700', 'description': 'Transitional player, both ends', 'order': 2},
        {'name': 'Defender', 'code': 'DEF', 'icon': '🛡️', 'color': '#2196f3', 'description': 'Last man, goal protection', 'order': 3},
    ],
}

# Games without defined roles (1v1 sports games, BR without strict roles)
NO_ROLES_GAMES = ['efootball', 'ea-sports-fc-26']


def populate_regions_and_roles():
    """Populate regions and roles for all games."""
    
    print("=" * 70)
    print("POPULATING GAME REGIONS AND ROLES")
    print("=" * 70)
    
    games = Game.objects.filter(is_active=True)
    
    for game in games:
        print(f"\n📦 Processing: {game.display_name} ({game.slug})")
        
        # Get or create roster config
        roster_config, created = GameRosterConfig.objects.get_or_create(game=game)
        
        # ═══════════════════════════════════════════════════════════════
        # POPULATE REGIONS
        # ═══════════════════════════════════════════════════════════════
        if game.slug in GAME_REGIONS:
            regions = GAME_REGIONS[game.slug]
            roster_config.has_regions = True
            roster_config.available_regions = regions
            roster_config.save()
            print(f"  ✅ Added {len(regions)} regions")
            for region in regions[:3]:  # Show first 3
                print(f"     - {region['code']}: {region['name']}")
            if len(regions) > 3:
                print(f"     ... and {len(regions) - 3} more")
        else:
            # No specific regions for this game
            roster_config.has_regions = False
            roster_config.available_regions = []
            roster_config.save()
            print(f"  ⚠️  No regions configured (global game)")
        
        # ═══════════════════════════════════════════════════════════════
        # POPULATE ROLES
        # ═══════════════════════════════════════════════════════════════
        if game.slug in NO_ROLES_GAMES:
            # 1v1 games don't need roles
            roster_config.has_roles = False
            roster_config.save()
            print(f"  ⚠️  No roles (1v1 game)")
        elif game.slug in GAME_ROLES:
            roles_data = GAME_ROLES[game.slug]
            roster_config.has_roles = True
            roster_config.save()
            
            # Clear existing roles
            game.roles.all().delete()
            
            # Create new roles
            created_count = 0
            for role_data in roles_data:
                GameRole.objects.create(
                    game=game,
                    role_name=role_data['name'],
                    role_code=role_data['code'],
                    icon=role_data.get('icon', ''),
                    color=role_data.get('color', ''),
                    description=role_data.get('description', ''),
                    order=role_data.get('order', 0),
                    is_competitive=True,
                    is_active=True,
                )
                created_count += 1
            
            print(f"  ✅ Added {created_count} roles")
            for role in roles_data[:3]:  # Show first 3
                print(f"     - {role['icon']} {role['name']}: {role['description'][:40]}...")
            if len(roles_data) > 3:
                print(f"     ... and {len(roles_data) - 3} more")
        else:
            # No roles configured yet
            roster_config.has_roles = False
            roster_config.save()
            print(f"  ⚠️  No roles configured")
    
    print("\n" + "=" * 70)
    print("✨ SUMMARY")
    print("=" * 70)
    
    # Summary stats
    total_games = games.count()
    games_with_regions = GameRosterConfig.objects.filter(has_regions=True).count()
    games_with_roles = GameRosterConfig.objects.filter(has_roles=True).count()
    total_roles = GameRole.objects.filter(is_active=True).count()
    
    print(f"📊 Total Games: {total_games}")
    print(f"🌍 Games with Regions: {games_with_regions}")
    print(f"👥 Games with Roles: {games_with_roles}")
    print(f"⭐ Total Roles Defined: {total_roles}")
    
    print("\n🎮 Games by Type:")
    for game in games:
        config = game.roster_config
        status = []
        if config.has_regions:
            status.append(f"🌍 {len(config.available_regions)} regions")
        if config.has_roles:
            role_count = game.roles.filter(is_active=True).count()
            status.append(f"👥 {role_count} roles")
        
        status_str = ", ".join(status) if status else "⚠️ No regions/roles"
        print(f"  {game.display_name}: {status_str}")
    
    print("\n" + "=" * 70)
    print("✅ DONE!")
    print("=" * 70)


if __name__ == '__main__':
    populate_regions_and_roles()
