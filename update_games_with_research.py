"""
Update all 11 games with researched 2025 data
Based on actual game requirements and competitive systems
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print("\n=== UPDATING GAMES WITH RESEARCHED 2025 DATA ===\n")

updates = {
    'VALORANT': {
        'has_servers': True,  # Region-locked competitive
        'has_rank_system': True,
        'ranks': [
            {'value': 'iron_1', 'label': 'Iron 1'}, {'value': 'iron_2', 'label': 'Iron 2'}, {'value': 'iron_3', 'label': 'Iron 3'},
            {'value': 'bronze_1', 'label': 'Bronze 1'}, {'value': 'bronze_2', 'label': 'Bronze 2'}, {'value': 'bronze_3', 'label': 'Bronze 3'},
            {'value': 'silver_1', 'label': 'Silver 1'}, {'value': 'silver_2', 'label': 'Silver 2'}, {'value': 'silver_3', 'label': 'Silver 3'},
            {'value': 'gold_1', 'label': 'Gold 1'}, {'value': 'gold_2', 'label': 'Gold 2'}, {'value': 'gold_3', 'label': 'Gold 3'},
            {'value': 'platinum_1', 'label': 'Platinum 1'}, {'value': 'platinum_2', 'label': 'Platinum 2'}, {'value': 'platinum_3', 'label': 'Platinum 3'},
            {'value': 'diamond_1', 'label': 'Diamond 1'}, {'value': 'diamond_2', 'label': 'Diamond 2'}, {'value': 'diamond_3', 'label': 'Diamond 3'},
            {'value': 'ascendant_1', 'label': 'Ascendant 1'}, {'value': 'ascendant_2', 'label': 'Ascendant 2'}, {'value': 'ascendant_3', 'label': 'Ascendant 3'},
            {'value': 'immortal_1', 'label': 'Immortal 1'}, {'value': 'immortal_2', 'label': 'Immortal 2'}, {'value': 'immortal_3', 'label': 'Immortal 3'},
            {'value': 'radiant', 'label': 'Radiant'},
        ]
    },
    'Counter-Strike 2': {
        'has_servers': False,  # Global matchmaking
        'has_rank_system': True,  # CS Rating system (numerical)
        'ranks': [
            {'value': '0-4999', 'label': '0-4,999 (Grey)'}, {'value': '5000-9999', 'label': '5,000-9,999 (Light Blue)'},
            {'value': '10000-14999', 'label': '10,000-14,999 (Blue)'}, {'value': '15000-19999', 'label': '15,000-19,999 (Purple)'},
            {'value': '20000-24999', 'label': '20,000-24,999 (Pink)'}, {'value': '25000-29999', 'label': '25,000-29,999 (Red)'},
            {'value': '30000+', 'label': '30,000+ (Premier)'},
        ]
    },
    'Dota 2': {
        'has_servers': False,  # Global MMR system
        'has_rank_system': True,  # MMR-based medals
        'ranks': [
            {'value': 'herald', 'label': 'Herald'}, {'value': 'guardian', 'label': 'Guardian'}, 
            {'value': 'crusader', 'label': 'Crusader'}, {'value': 'archon', 'label': 'Archon'},
            {'value': 'legend', 'label': 'Legend'}, {'value': 'ancient', 'label': 'Ancient'},
            {'value': 'divine', 'label': 'Divine'}, {'value': 'immortal', 'label': 'Immortal'},
        ]
    },
    'PUBG MOBILE': {
        'has_servers': True,  # Server-based ranking
        'has_rank_system': True,
        'ranks': [
            {'value': 'bronze', 'label': 'Bronze'}, {'value': 'silver', 'label': 'Silver'}, 
            {'value': 'gold', 'label': 'Gold'}, {'value': 'platinum', 'label': 'Platinum'},
            {'value': 'diamond', 'label': 'Diamond'}, {'value': 'crown', 'label': 'Crown'},
            {'value': 'ace', 'label': 'Ace'}, {'value': 'ace_master', 'label': 'Ace Master'},
            {'value': 'ace_dominator', 'label': 'Ace Dominator'}, {'value': 'conqueror', 'label': 'Conqueror'},
        ]
    },
    'Mobile Legends: Bang Bang': {
        'has_servers': True,  # Server-based
        'has_rank_system': True,
        'ranks': [
            {'value': 'warrior', 'label': 'Warrior'}, {'value': 'elite', 'label': 'Elite'},
            {'value': 'master', 'label': 'Master'}, {'value': 'grandmaster', 'label': 'Grandmaster'},
            {'value': 'epic', 'label': 'Epic'}, {'value': 'legend', 'label': 'Legend'},
            {'value': 'mythic', 'label': 'Mythic'}, {'value': 'mythic_honor', 'label': 'Mythic Honor'},
            {'value': 'mythic_glory', 'label': 'Mythic Glory'}, {'value': 'mythic_immortal', 'label': 'Mythic Immortal'},
        ]
    },
    'Free Fire': {
        'has_servers': True,  # Server-based
        'has_rank_system': True,
        'ranks': [
            {'value': 'bronze', 'label': 'Bronze'}, {'value': 'silver', 'label': 'Silver'},
            {'value': 'gold', 'label': 'Gold'}, {'value': 'platinum', 'label': 'Platinum'},
            {'value': 'diamond', 'label': 'Diamond'}, {'value': 'heroic', 'label': 'Heroic'},
            {'value': 'grandmaster', 'label': 'Grandmaster'},
        ]
    },
    'Rocket League': {
        'has_servers': False,  # Global matchmaking
        'has_rank_system': True,
        'ranks': [
            {'value': 'bronze_1', 'label': 'Bronze I'}, {'value': 'bronze_2', 'label': 'Bronze II'}, {'value': 'bronze_3', 'label': 'Bronze III'},
            {'value': 'silver_1', 'label': 'Silver I'}, {'value': 'silver_2', 'label': 'Silver II'}, {'value': 'silver_3', 'label': 'Silver III'},
            {'value': 'gold_1', 'label': 'Gold I'}, {'value': 'gold_2', 'label': 'Gold II'}, {'value': 'gold_3', 'label': 'Gold III'},
            {'value': 'platinum_1', 'label': 'Platinum I'}, {'value': 'platinum_2', 'label': 'Platinum II'}, {'value': 'platinum_3', 'label': 'Platinum III'},
            {'value': 'diamond_1', 'label': 'Diamond I'}, {'value': 'diamond_2', 'label': 'Diamond II'}, {'value': 'diamond_3', 'label': 'Diamond III'},
            {'value': 'champion_1', 'label': 'Champion I'}, {'value': 'champion_2', 'label': 'Champion II'}, {'value': 'champion_3', 'label': 'Champion III'},
            {'value': 'grand_champion_1', 'label': 'Grand Champion I'}, {'value': 'grand_champion_2', 'label': 'Grand Champion II'}, {'value': 'grand_champion_3', 'label': 'Grand Champion III'},
            {'value': 'supersonic_legend', 'label': 'Supersonic Legend'},
        ]
    },
}

# Games using short_code lookup
updates_by_code = {
    'CODM': {
        'has_servers': False,  # Global matchmaking
        'has_rank_system': True,
        'ranks': [
            {'value': 'rookie', 'label': 'Rookie'}, {'value': 'veteran', 'label': 'Veteran'},
            {'value': 'elite', 'label': 'Elite'}, {'value': 'pro', 'label': 'Pro'},
            {'value': 'master', 'label': 'Master'}, {'value': 'grandmaster', 'label': 'Grandmaster'},
            {'value': 'legendary', 'label': 'Legendary'},
        ]
    },
    'R6': {
        'has_servers': False,  # Global MMR
        'has_rank_system': True,
        'ranks': [
            {'value': 'copper', 'label': 'Copper'}, {'value': 'bronze', 'label': 'Bronze'},
            {'value': 'silver', 'label': 'Silver'}, {'value': 'gold', 'label': 'Gold'},
            {'value': 'platinum', 'label': 'Platinum'}, {'value': 'emerald', 'label': 'Emerald'},
            {'value': 'diamond', 'label': 'Diamond'}, {'value': 'champion', 'label': 'Champion'},
        ]
    },
    'FC26': {
        'has_servers': True,  # Regional FUT Champions
        'has_rank_system': False,  # Uses Division system, not ranks
        'ranks': []  # No traditional ranks
    },
    'EFB': {
        'has_servers': False,  # Cross-platform global
        'has_rank_system': False,  # Uses rating/division system
        'ranks': []  # No traditional ranks
    },
}

# Update by name
for game_name, data in updates.items():
    try:
        game = Game.objects.get(name=game_name)
        game.has_servers = data['has_servers']
        game.has_rank_system = data['has_rank_system']
        game.available_ranks = data['ranks']
        game.save()
        rank_count = len(data['ranks'])
        servers = 'Yes' if data['has_servers'] else 'No'
        print(f"✓ {game.name:25} | Servers: {servers:3} | Ranks: {rank_count:2}")
    except Game.DoesNotExist:
        print(f"✗ {game_name:25} | NOT FOUND")

# Update by short code
for code, data in updates_by_code.items():
    try:
        game = Game.objects.get(short_code=code)
        game.has_servers = data['has_servers']
        game.has_rank_system = data['has_rank_system']
        game.available_ranks = data['ranks']
        game.save()
        rank_count = len(data['ranks'])
        servers = 'Yes' if data['has_servers'] else 'No'
        print(f"✓ {game.name:25} | Servers: {servers:3} | Ranks: {rank_count:2}")
    except Game.DoesNotExist:
        print(f"✗ Code {code:25} | NOT FOUND")

print("\n=== UPDATE COMPLETE ===\n")
print("Summary:")
print("- Games with servers: VALORANT, PUBG Mobile, MLBB, Free Fire, EA FC 26")
print("- Games without servers: CS2, Dota 2, COD Mobile, Rocket League, R6, eFootball")
print("- Games with rank systems: 9 games")
print("- Games without ranks: EA FC 26, eFootball (use divisions/ratings)")
