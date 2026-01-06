"""
Test GET /profile/api/games/ schema completeness
Phase 9A-7: Verify frontend receives complete dropdown options
"""
import django
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models import GamePassportSchema

def safe_image_url(field):
    try:
        if not field:
            return None
        return getattr(field, 'url', None)
    except Exception:
        return None

print("\n" + "="*70)
print("GAMES API SCHEMA TEST (Simulating GET /profile/api/games/)")
print("="*70)

# Simulate the actual API logic from dynamic_content_api.py
games = Game.objects.filter(is_active=True).order_by('display_name')[:3]  # Test first 3 games

for game in games:
    print(f"\n{'='*70}")
    print(f"GAME: {game.display_name} (slug={game.slug})")
    print(f"{'='*70}")
    
    # Get identity configs (field definitions)
    identity_configs = GamePlayerIdentityConfig.objects.filter(
        game=game
    ).order_by('order', 'id')
    
    print(f"\n[OK] Identity configs: {identity_configs.count()} fields")
    for config in identity_configs:
        print(f"   - {config.field_name}: {config.field_type}, required={config.is_required}, immutable={config.is_immutable}")
    
    # Get GamePassportSchema (dropdown options)
    try:
        game_schema = GamePassportSchema.objects.get(game=game)
        region_options = game_schema.region_choices or []
        rank_options = game_schema.rank_choices or []
        role_options = game_schema.role_choices or []
        platform_options = game_schema.platform_choices or []
        server_options = game_schema.server_choices or []
        mode_options = game_schema.mode_choices or []
        premier_rating_options = game_schema.premier_rating_choices or []
        division_options = game_schema.division_choices or []
        
        print(f"\n[OK] GamePassportSchema dropdown options:")
        print(f"   - Regions: {len(region_options)}")
        print(f"   - Ranks: {len(rank_options)}")
        print(f"   - Roles: {len(role_options)}")
        print(f"   - Platforms: {len(platform_options)}")
        print(f"   - Servers: {len(server_options)}")
        print(f"   - Modes: {len(mode_options)}")
        print(f"   - Premier Ratings: {len(premier_rating_options)}")
        print(f"   - Divisions: {len(division_options)}")
        
    except GamePassportSchema.DoesNotExist:
        print(f"\n❌ NO GamePassportSchema found!")
        region_options = []
        rank_options = []
        role_options = []
        platform_options = []
        server_options = []
        mode_options = []
        premier_rating_options = []
        division_options = []
    
    # Serialize passport schema (CURRENT API LOGIC)
    print(f"\n{'─'*70}")
    print("SERIALIZED PASSPORT_SCHEMA (what API returns):")
    print(f"{'─'*70}")
    
    passport_schema = []
    
    for config in identity_configs:
        field_data = {
            'key': config.field_name,
            'label': config.display_name,
            'type': config.field_type.lower() if config.field_type else 'text',
            'required': config.is_required,
            'immutable': config.is_immutable,
            'placeholder': config.placeholder or '',
            'help_text': config.help_text or '',
            'validation_regex': config.validation_regex or '',
            'min_length': config.min_length,
            'max_length': config.max_length
        }
        
        # UPDATED OPTION MAPPING LOGIC (Phase 9A-7 with 8 choice types)
        if config.field_type and config.field_type.lower() == 'select':
            if 'region' in config.field_name.lower():
                field_data['options'] = region_options
            elif 'rank' in config.field_name.lower():
                field_data['options'] = rank_options
            elif 'role' in config.field_name.lower():
                field_data['options'] = role_options
            elif 'platform' in config.field_name.lower():
                field_data['options'] = platform_options
            elif 'server' in config.field_name.lower():
                field_data['options'] = server_options
            elif 'mode' in config.field_name.lower():
                field_data['options'] = mode_options
            elif 'premier' in config.field_name.lower():
                field_data['options'] = premier_rating_options
            elif 'division' in config.field_name.lower():
                field_data['options'] = division_options
            else:
                field_data['options'] = []
        
        passport_schema.append(field_data)
        
        # Print field
        options_indicator = ""
        if field_data.get('options'):
            options_indicator = f" → {len(field_data['options'])} options"
        elif field_data['type'] == 'select':
            options_indicator = f" → ⚠️  NO OPTIONS (will show empty dropdown)"
        
        print(f"   {field_data['key']} ({field_data['type']}){options_indicator}")
    
    # Show sample of fields with missing options
    missing_options = [f for f in passport_schema if f['type'] == 'select' and not f.get('options')]
    if missing_options:
        print(f"\n❌ PROBLEM: {len(missing_options)} select fields have NO OPTIONS:")
        for f in missing_options:
            print(f"   - {f['key']}: {f['label']}")
        print("\n   → These will render as empty dropdowns in the UI!")

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
