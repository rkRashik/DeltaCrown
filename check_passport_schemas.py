"""
Quick diagnostic: Check Game Passport schema coverage in database
"""
import django
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GamePassportSchema

print('\n' + '='*60)
print('GAME PASSPORT SCHEMA DIAGNOSTIC')
print('='*60)

games = Game.objects.filter(is_active=True).order_by('display_name')
print(f'\n✓ Total active games: {games.count()}')

print('\n' + '-'*60)
print('IDENTITY CONFIGS PER GAME')
print('-'*60)

games_with_configs = 0
games_without_configs = 0

for game in games:
    configs = GamePlayerIdentityConfig.objects.filter(game=game)
    config_count = configs.count()
    
    if config_count > 0:
        games_with_configs += 1
        print(f'\n✓ {game.display_name} ({game.slug}): {config_count} fields')
        for config in configs:
            required_badge = '⚠️  REQUIRED' if config.is_required else ''
            immutable_badge = '🔒 IMMUTABLE' if config.is_immutable else ''
            badges = f' {required_badge} {immutable_badge}'.strip()
            print(f'   - {config.field_name}: {config.field_type} {badges}')
    else:
        games_without_configs += 1
        print(f'\n❌ {game.display_name} ({game.slug}): NO CONFIGS')

print('\n' + '-'*60)
print(f'Summary: {games_with_configs} games WITH configs, {games_without_configs} games WITHOUT configs')

print('\n' + '-'*60)
print('GAME PASSPORT SCHEMAS (Dropdown Options)')
print('-'*60)

schemas = GamePassportSchema.objects.all()
print(f'\nTotal GamePassportSchema records: {schemas.count()}')

for schema in schemas:
    region_count = len(schema.region_choices) if schema.region_choices else 0
    rank_count = len(schema.rank_choices) if schema.rank_choices else 0
    role_count = len(schema.role_choices) if schema.role_choices else 0
    platform_count = len(schema.platform_choices) if schema.platform_choices else 0
    
    print(f'\n{schema.game.display_name}:')
    print(f'   Regions: {region_count}, Ranks: {rank_count}, Roles: {role_count}, Platforms: {platform_count}')
    
    if rank_count > 0:
        print(f'   First 5 ranks: {schema.rank_choices[:5]}')

print('\n' + '='*60)
print('DIAGNOSTIC COMPLETE')
print('='*60 + '\n')
