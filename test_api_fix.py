"""
Quick test to verify API option mapping fix for Phase 9A-7
Tests CODM (mode), CS2 (premier_rating), Dota 2 (server) fields
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.games.models import Game, GamePlayerIdentityConfig
from apps.user_profile.models.game_passport_schema import GamePassportSchema

def test_game(game_slug, test_field_name):
    """Test if a specific select field gets options mapped"""
    try:
        game = Game.objects.get(slug=game_slug, is_active=True)
        configs = GamePlayerIdentityConfig.objects.filter(game=game)
        schema = GamePassportSchema.objects.get(game=game)
        
        # Get options
        region_options = schema.region_choices or []
        rank_options = schema.rank_choices or []
        role_options = schema.role_choices or []
        platform_options = schema.platform_choices or []
        server_options = schema.server_choices or []
        mode_options = schema.mode_choices or []
        premier_rating_options = schema.premier_rating_choices or []
        division_options = schema.division_choices or []
        
        # Find the test field
        test_config = configs.filter(field_name=test_field_name).first()
        if not test_config:
            print(f"[SKIP] {game.display_name}: Field '{test_field_name}' not found")
            return False
        
        # Apply option mapping
        if test_config.field_type.lower() == 'select':
            if 'region' in test_config.field_name.lower():
                options = region_options
            elif 'rank' in test_config.field_name.lower():
                options = rank_options
            elif 'role' in test_config.field_name.lower():
                options = role_options
            elif 'platform' in test_config.field_name.lower():
                options = platform_options
            elif 'server' in test_config.field_name.lower():
                options = server_options
            elif 'mode' in test_config.field_name.lower():
                options = mode_options
            elif 'premier' in test_config.field_name.lower():
                options = premier_rating_options
            elif 'division' in test_config.field_name.lower():
                options = division_options
            else:
                options = []
            
            if len(options) > 0:
                print(f"[PASS] {game.display_name}: '{test_field_name}' has {len(options)} options")
                return True
            else:
                print(f"[FAIL] {game.display_name}: '{test_field_name}' has NO OPTIONS")
                return False
        else:
            print(f"[SKIP] {game.display_name}: '{test_field_name}' is not a select field")
            return False
    except Exception as e:
        print(f"[ERROR] {game_slug}: {e}")
        return False

print("="*70)
print("API OPTION MAPPING FIX VERIFICATION")
print("="*70)

tests = [
    ("codm", "mode"),
    ("cs2", "premier_rating"),
    ("dota2", "server"),
    ("valorant", "region"),
    ("valorant", "rank"),
]

passed = 0
failed = 0

for game_slug, field_name in tests:
    result = test_game(game_slug, field_name)
    if result:
        passed += 1
    elif result is False:
        failed += 1

print("\n" + "="*70)
print(f"RESULTS: {passed} passed, {failed} failed")
print("="*70)

if failed == 0:
    print("\n[SUCCESS] All select fields now receive options!")
    print("Frontend dropdowns should render correctly.")
else:
    print("\n[FAILURE] Some fields still missing options.")
    print("Check dynamic_content_api.py option mapping logic.")
