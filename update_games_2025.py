"""
Update all 11 games with 2025 competitive data
Uses EXACT names from database
"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game

print("\n" + "="*70)
print(" UPDATING ALL 11 GAMES WITH 2025 COMPETITIVE DATA")
print("="*70 + "\n")

# EXACT names from database (checked with seed_games output)
GAME_DATA = {
    'Valorant': {
        'has_servers': True,
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
        'has_servers': False,
        'has_rank_system': True,
        'ranks': [
            {'value': '0-4999', 'label': '0-4,999 (Grey)'}, 
            {'value': '5000-9999', 'label': '5,000-9,999 (Light Blue)'},
            {'value': '10000-14999', 'label': '10,000-14,999 (Blue)'}, 
            {'value': '15000-19999', 'label': '15,000-19,999 (Purple)'},
            {'value': '20000-24999', 'label': '20,000-24,999 (Pink)'}, 
            {'value': '25000-29999', 'label': '25,000-29,999 (Red)'},
            {'value': '30000+', 'label': '30,000+ (Premier)'},
        ]
    },
    'Dota 2': {
        'has_servers': False,
        'has_rank_system': True,
        'ranks': [
            {'value': 'herald', 'label': 'Herald'}, {'value': 'guardian', 'label': 'Guardian'}, 
            {'value': 'crusader', 'label': 'Crusader'}, {'value': 'archon', 'label': 'Archon'},
            {'value': 'legend', 'label': 'Legend'}, {'value': 'ancient', 'label': 'Ancient'},
            {'value': 'divine', 'label': 'Divine'}, {'value': 'immortal', 'label': 'Immortal'},
        ]
    },
    'EA Sports FC 26': {
        'has_servers': True,  # FUT Champions regional
        'has_rank_system': False,  # Uses divisions not ranks
        'ranks': []
    },
    'eFootball': {
        'has_servers': False,
        'has_rank_system': False,  # Uses rating system
        'ranks': []
    },
    'PUBG Mobile': {
        'has_servers': True,
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
        'has_servers': True,
        'has_rank_system': True,
        'ranks': [
            {'value': 'warrior', 'label': 'Warrior'}, {'value': 'elite', 'label': 'Elite'}, 
            {'value': 'master', 'label': 'Master'}, {'value': 'grandmaster', 'label': 'Grandmaster'},
            {'value': 'epic', 'label': 'Epic'}, {'value': 'legend', 'label': 'Legend'},
            {'value': 'mythic', 'label': 'Mythic'}, {'value': 'mythic_glory', 'label': 'Mythic Glory'},
            {'value': 'mythic_immortal', 'label': 'Mythic Immortal'}, {'value': 'mythic_honor', 'label': 'Mythic Honor'},
        ]
    },
    'Free Fire': {
        'has_servers': True,
        'has_rank_system': True,
        'ranks': [
            {'value': 'bronze', 'label': 'Bronze'}, {'value': 'silver', 'label': 'Silver'}, 
            {'value': 'gold', 'label': 'Gold'}, {'value': 'platinum', 'label': 'Platinum'},
            {'value': 'diamond', 'label': 'Diamond'}, {'value': 'heroic', 'label': 'Heroic'},
            {'value': 'grandmaster', 'label': 'Grandmaster'},
        ]
    },
    'Call of Duty: Mobile': {
        'has_servers': False,
        'has_rank_system': True,
        'ranks': [
            {'value': 'rookie', 'label': 'Rookie'}, {'value': 'veteran', 'label': 'Veteran'}, 
            {'value': 'elite', 'label': 'Elite'}, {'value': 'pro', 'label': 'Pro'},
            {'value': 'master', 'label': 'Master'}, {'value': 'grandmaster', 'label': 'Grandmaster'},
            {'value': 'legendary', 'label': 'Legendary'},
        ]
    },
    'Rocket League': {
        'has_servers': False,
        'has_rank_system': True,
        'ranks': [
            {'value': 'bronze_1', 'label': 'Bronze I'}, {'value': 'bronze_2', 'label': 'Bronze II'}, {'value': 'bronze_3', 'label': 'Bronze III'},
            {'value': 'silver_1', 'label': 'Silver I'}, {'value': 'silver_2', 'label': 'Silver II'}, {'value': 'silver_3', 'label': 'Silver III'},
            {'value': 'gold_1', 'label': 'Gold I'}, {'value': 'gold_2', 'label': 'Gold II'}, {'value': 'gold_3', 'label': 'Gold III'},
            {'value': 'platinum_1', 'label': 'Platinum I'}, {'value': 'platinum_2', 'label': 'Platinum II'}, {'value': 'platinum_3', 'label': 'Platinum III'},
            {'value': 'diamond_1', 'label': 'Diamond I'}, {'value': 'diamond_2', 'label': 'Diamond II'}, {'value': 'diamond_3', 'label': 'Diamond III'},
            {'value': 'champion_1', 'label': 'Champion I'}, {'value': 'champion_2', 'label': 'Champion II'}, {'value': 'champion_3', 'label': 'Champion III'},
            {'value': 'grand_champion_1', 'label': 'Grand Champion I'}, {'value': 'grand_champion_2', 'label': 'Grand Champion II'}, 
            {'value': 'grand_champion_3', 'label': 'Grand Champion III'}, {'value': 'supersonic_legend', 'label': 'Supersonic Legend'},
        ]
    },
    'Rainbow Six Siege': {
        'has_servers': False,
        'has_rank_system': True,
        'ranks': [
            {'value': 'copper', 'label': 'Copper'}, {'value': 'bronze', 'label': 'Bronze'}, 
            {'value': 'silver', 'label': 'Silver'}, {'value': 'gold', 'label': 'Gold'},
            {'value': 'platinum', 'label': 'Platinum'}, {'value': 'emerald', 'label': 'Emerald'},
            {'value': 'diamond', 'label': 'Diamond'}, {'value': 'champion', 'label': 'Champion'},
        ]
    },
}

# Update each game
updated = 0
failed = []

for game_name, data in GAME_DATA.items():
    try:
        game = Game.objects.get(name=game_name)
        
        game.has_servers = data['has_servers']
        game.has_rank_system = data['has_rank_system']
        game.available_ranks = data['ranks']
        game.save()
        
        servers_icon = "[S]" if data['has_servers'] else "[-]"
        ranks_count = len(data['ranks'])
        
        print(f"[OK] {game_name:<25} {servers_icon} Servers: {'Yes' if data['has_servers'] else 'No':<3}  Ranks: {ranks_count:>2}")
        updated += 1
        
    except Game.DoesNotExist:
        print(f"[!!] {game_name:<25} NOT FOUND IN DATABASE")
        failed.append(game_name)
    except Exception as e:
        print(f"[!!] {game_name:<25} ERROR: {e}")
        failed.append(game_name)

print("\n" + "="*70)
print(f" COMPLETE: {updated}/{len(GAME_DATA)} games updated successfully")
if failed:
    print(f" Failed: {', '.join(failed)}")
print("="*70 + "\n")
