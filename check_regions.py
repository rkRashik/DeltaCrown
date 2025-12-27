from apps.games.models import Game

v = Game.objects.get(name='Valorant')
print(f'Valorant regions: {len(v.roster_config.available_regions)}')
print('Regions:')
for r in v.roster_config.available_regions:
    print(f"  {r['code']}: {r['name']}")
