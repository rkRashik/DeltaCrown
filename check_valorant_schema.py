from apps.games.models import Game
import json

# Test Valorant schema
game = Game.objects.get(name='Valorant')
print(f"Game: {game.name}")
print(f"  has_servers: {game.has_servers}")
print(f"  has_rank_system: {game.has_rank_system}")
print(f"  Platforms: {game.platforms}")

# Check roster config regions
roster = game.roster_config
print(f"\nRoster Config:")
print(f"  has_regions: {roster.has_regions}")
print(f"  Available regions: {len(roster.available_regions)}")
if roster.available_regions:
    print(f"  Regions: {json.dumps(roster.available_regions, indent=2)}")

# Check identity configs
identity_configs = game.identity_configs.all()
print(f"\nIdentity Configs: {identity_configs.count()}")
for config in identity_configs:
    print(f"  - {config.field_name}: {config.label}")
