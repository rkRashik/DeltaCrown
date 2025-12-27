from apps.games.models import Game, GamePlayerIdentityConfig

g = Game.objects.first()
print('Game:', g.name)
print('\nIdentity configs:')
for c in g.identity_configs.all():
    print(f'  - {c.field_name}: {c.display_name} (required={c.is_required})')

print('\nPlatforms:', g.platforms)
print('Has roster config:', hasattr(g, 'roster_config'))

if hasattr(g, 'roster_config') and g.roster_config:
    print('Has regions:', g.roster_config.has_regions)
    print('Regions:', g.roster_config.available_regions if g.roster_config.has_regions else 'None')
    
print('\n--- Checking all 11 games ---')
for game in Game.objects.filter(is_active=True)[:11]:
    print(f'\n{game.name}:')
    print(f'  Platforms: {game.platforms}')
    configs = game.identity_configs.all()
    print(f'  Identity fields: {[c.field_name for c in configs]}')
    if hasattr(game, 'roster_config') and game.roster_config:
        print(f'  Regions: {game.roster_config.available_regions if game.roster_config.has_regions else "None"}')
