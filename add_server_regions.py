"""
Add server regions for games with has_servers=True
"""
from apps.games.models import Game, GameRosterConfig

# Define server regions for each game
GAME_REGIONS = {
    'Valorant': [
        {'code': 'NA', 'name': 'North America'},
        {'code': 'LATAM', 'name': 'Latin America'},
        {'code': 'BR', 'name': 'Brazil'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'AP', 'name': 'Asia Pacific'},
        {'code': 'KR', 'name': 'Korea'},
        {'code': 'MENA', 'name': 'Middle East & North Africa'},
    ],
    'PUBG Mobile': [
        {'code': 'ASIA', 'name': 'Asia'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'ME', 'name': 'Middle East'},
        {'code': 'KRJP', 'name': 'Korea/Japan'},
    ],
    'Mobile Legends: Bang Bang': [
        {'code': 'SEA', 'name': 'Southeast Asia'},
        {'code': 'NA', 'name': 'North America'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'ME', 'name': 'Middle East'},
        {'code': 'ID', 'name': 'Indonesia'},
        {'code': 'PH', 'name': 'Philippines'},
        {'code': 'MY/SG', 'name': 'Malaysia/Singapore'},
    ],
    'Free Fire': [
        {'code': 'BR', 'name': 'Brazil'},
        {'code': 'LATAM', 'name': 'Latin America'},
        {'code': 'NA', 'name': 'North America'},
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'ME', 'name': 'Middle East'},
        {'code': 'ASIA', 'name': 'Asia'},
        {'code': 'SEA', 'name': 'Southeast Asia'},
        {'code': 'IND', 'name': 'India'},
    ],
    'EA Sports FC 26': [
        {'code': 'EU', 'name': 'Europe'},
        {'code': 'NA-EAST', 'name': 'North America East'},
        {'code': 'NA-WEST', 'name': 'North America West'},
        {'code': 'ASIA', 'name': 'Asia'},
        {'code': 'OCE', 'name': 'Oceania'},
        {'code': 'SA', 'name': 'South America'},
        {'code': 'ME', 'name': 'Middle East'},
    ],
}

print("\\n" + "="*70)
print(" ADDING SERVER REGIONS FOR GAMES WITH has_servers=True")
print("="*70 + "\\n")

updated = 0
failed = []

for game_name, regions in GAME_REGIONS.items():
    try:
        game = Game.objects.get(name=game_name)
        roster_config = game.roster_config
        
        # Update roster config with regions
        roster_config.has_regions = True
        roster_config.available_regions = regions
        roster_config.save()
        
        print(f"[OK] {game_name:<30} Added {len(regions):>2} regions")
        updated += 1
        
    except Game.DoesNotExist:
        print(f"[!!] {game_name:<30} Game NOT FOUND")
        failed.append(game_name)
    except Exception as e:
        print(f"[!!] {game_name:<30} ERROR: {e}")
        failed.append(game_name)

print("\\n" + "="*70)
print(f" COMPLETE: {updated}/{len(GAME_REGIONS)} games updated")
if failed:
    print(f" Failed: {', '.join(failed)}")
print("="*70 + "\\n")

# Verify one game
print("\\nVerification - Valorant regions:")
val = Game.objects.get(name='Valorant')
print(f"  has_regions: {val.roster_config.has_regions}")
print(f"  Total regions: {len(val.roster_config.available_regions)}")
for region in val.roster_config.available_regions[:3]:
    print(f"  - {region['code']}: {region['name']}")
print("  ...")
