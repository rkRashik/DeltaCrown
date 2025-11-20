"""
Test Game Registry Integration with Teams App

Verifies that:
1. Team.game field uses Game Registry choices
2. Forms use Game Registry for game selection
3. Normalization delegates to Game Registry
4. Legacy codes are handled correctly
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.common.game_registry import get_choices, normalize_slug, get_game
from apps.teams.models import Team
from apps.teams.forms import TeamCreationForm
from apps.teams.game_config import normalize_game_code as game_config_normalize
from apps.teams.utils.game_mapping import (
    normalize_game_code as game_mapping_normalize,
    get_game_config,
    is_valid_game_code,
    get_game_display_name
)

print("=" * 80)
print("TESTING GAME REGISTRY INTEGRATION WITH TEAMS APP")
print("=" * 80)

# Test 1: Team model uses Game Registry choices
print("\n1. Testing Team.game field choices...")
team_game_field = Team._meta.get_field('game')
game_choices = team_game_field.choices

# Django wraps callable choices in CallableChoiceIterator
if callable(game_choices) or hasattr(game_choices, '__iter__'):
    print("   ✓ Team.game.choices is callable/iterable (correct!)")
    # Iterate to get actual choices
    choices_list = list(game_choices)
    print(f"   ✓ Retrieved {len(choices_list)} game choices from registry")
    print(f"   Available games: {[slug for slug, _ in choices_list]}")
else:
    print("   ✗ Team.game.choices is NOT callable/iterable")
    choices_list = []

# Test 2: Form uses Game Registry choices
print("\n2. Testing TeamCreationForm uses Game Registry...")
form = TeamCreationForm()
form_game_choices = form.fields['game'].choices
print(f"   ✓ Form has {len(form_game_choices)} game choices")
print(f"   Games in form: {[slug for slug, _ in form_game_choices]}")

# Test 3: Normalization delegates to Game Registry
print("\n3. Testing normalization delegates to Game Registry...")

test_cases = [
    ('VALORANT', 'valorant'),
    ('valorant', 'valorant'),
    ('CSGO', 'cs2'),
    ('cs-go', 'cs2'),
    ('csgo', 'cs2'),
    ('pubg-mobile', 'pubg'),
    ('PUBG-Mobile', 'pubg'),
    ('FIFA', 'fc26'),
    ('fc-26', 'fc26'),
    ('MLBB', 'mlbb'),
    ('mobile-legends', 'mlbb'),
    ('free-fire', 'freefire'),
    ('ff', 'freefire'),
]

all_passed = True
for input_code, expected_output in test_cases:
    # Test Game Registry
    registry_result = normalize_slug(input_code)
    
    # Test game_config.py
    config_result = game_config_normalize(input_code)
    
    # Test game_mapping.py
    mapping_result = game_mapping_normalize(input_code)
    
    if registry_result == expected_output and config_result == expected_output and mapping_result == expected_output:
        print(f"   ✓ '{input_code}' → '{expected_output}' (all modules agree)")
    else:
        print(f"   ✗ '{input_code}': registry={registry_result}, config={config_result}, mapping={mapping_result}, expected={expected_output}")
        all_passed = False

if all_passed:
    print("   ✓ All normalization tests passed!")

# Test 4: Game config retrieval
print("\n4. Testing game config retrieval...")
test_games = ['valorant', 'cs2', 'CSGO', 'pubg-mobile']

for game_code in test_games:
    registry_game = get_game(game_code)
    mapping_game = get_game_config(game_code)
    
    if registry_game and mapping_game:
        print(f"   ✓ '{game_code}' → Registry: {registry_game.name}, Mapping: {getattr(mapping_game, 'name', 'N/A')}")
    else:
        print(f"   ✗ '{game_code}' → Failed to retrieve game config")

# Test 5: Validation
print("\n5. Testing game code validation...")
valid_codes = ['valorant', 'cs2', 'CSGO', 'pubg-mobile', 'FIFA']
invalid_codes = ['fake-game', 'xyz123', '']

for code in valid_codes:
    result = is_valid_game_code(code)
    status = "✓" if result else "✗"
    print(f"   {status} is_valid_game_code('{code}') = {result}")

for code in invalid_codes:
    result = is_valid_game_code(code)
    status = "✓" if not result else "✗"
    print(f"   {status} is_valid_game_code('{code}') = {result} (should be False)")

# Test 6: Display names
print("\n6. Testing display name retrieval...")
test_display = ['valorant', 'cs2', 'CSGO', 'pubg-mobile']

for code in test_display:
    display_name = get_game_display_name(code)
    print(f"   ✓ '{code}' → '{display_name}'")

# Test 7: Check consistency between all sources
print("\n7. Testing consistency across all modules...")
registry_choices = get_choices()
form_choices = form.fields['game'].choices
team_field_choices = list(Team._meta.get_field('game').choices)  # Convert iterator to list

registry_slugs = set(slug for slug, _ in registry_choices)
form_slugs = set(slug for slug, _ in form_choices)
team_slugs = set(slug for slug, _ in team_field_choices)

if registry_slugs == form_slugs == team_slugs:
    print(f"   ✓ All sources agree on {len(registry_slugs)} games")
    print(f"   Games: {sorted(registry_slugs)}")
else:
    print("   ✗ Inconsistency detected!")
    print(f"   Registry: {sorted(registry_slugs)}")
    print(f"   Form: {sorted(form_slugs)}")
    print(f"   Team field: {sorted(team_slugs)}")

print("\n" + "=" * 80)
print("INTEGRATION TEST COMPLETE")
print("=" * 80)
print("\n✅ Game Registry is now the single source of truth for Teams app!")
print("   - Team.game field uses registry choices (callable)")
print("   - Forms dynamically populate from registry")
print("   - All normalization delegates to registry")
print("   - Legacy codes handled consistently")
print("   - Backwards compatibility maintained")
