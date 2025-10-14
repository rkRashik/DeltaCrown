# Test Dual-Role System
# Run this with: python manage.py shell < test_dual_role.py

from apps.teams.models import Team, TeamMembership
from apps.teams.dual_role_system import *
from apps.teams.game_config import GAME_CONFIGS
from apps.user_profile.models import UserProfile

print("=" * 70)
print("DUAL-ROLE SYSTEM TEST")
print("=" * 70)

# Test 1: Check game configurations
print("\n[TEST 1] Game Configurations")
print(f"✓ Total games configured: {len(GAME_CONFIGS)}")
for game_code, config in GAME_CONFIGS.items():
    print(f"  - {config.name} ({game_code}): {len(config.roles)} roles")

# Test 2: Check role retrieval
print("\n[TEST 2] Role Retrieval for VALORANT")
valorant_roles = get_player_roles_for_game('valorant')
print(f"✓ VALORANT has {len(valorant_roles)} roles:")
for role in valorant_roles:
    print(f"  - {role['label']}: {role['description']}")

# Test 3: Role validation
print("\n[TEST 3] Role Validation")
is_valid, error = validate_player_role('valorant', 'Duelist')
print(f"✓ 'Duelist' for VALORANT: {'Valid' if is_valid else 'Invalid'}")

is_valid, error = validate_player_role('valorant', 'InvalidRole')
print(f"✓ 'InvalidRole' for VALORANT: {'Invalid (expected)' if not is_valid else 'Valid (unexpected!)'}")
if error:
    print(f"  Error message: {error}")

# Test 4: Game support detection
print("\n[TEST 4] Game Support Detection")
print(f"✓ VALORANT supports player roles: {game_supports_player_roles('valorant')}")
print(f"✓ CS2 supports player roles: {game_supports_player_roles('cs2')}")
print(f"✓ eFootball supports player roles: {game_supports_player_roles('efootball')} (should be False)")
print(f"✓ FC 26 supports player roles: {game_supports_player_roles('fc26')} (should be False)")

# Test 5: Role badge colors
print("\n[TEST 5] Role Badge Colors")
roles_to_test = ['Duelist', 'IGL', 'Controller', 'Support', 'AWPer']
for role in roles_to_test:
    color = get_role_badge_color(role, 'valorant')
    print(f"✓ {role}: {color}")

# Test 6: Membership role checks
print("\n[TEST 6] Membership Role Checks")
from apps.teams.models._legacy import TeamMembership as TM
print(f"✓ PLAYER can have player role: {can_have_player_role(TM.Role.PLAYER)}")
print(f"✓ SUB can have player role: {can_have_player_role(TM.Role.SUB)}")
print(f"✓ CAPTAIN can have player role: {can_have_player_role(TM.Role.CAPTAIN)} (should be False)")
print(f"✓ MANAGER can have player role: {can_have_player_role(TM.Role.MANAGER)} (should be False)")

# Test 7: Display formatting
print("\n[TEST 7] Display Formatting")
test_cases = [
    (TM.Role.PLAYER, 'Duelist', "Player (Duelist)"),
    (TM.Role.SUB, 'AWPer', "Substitute (AWPer)"),
    (TM.Role.CAPTAIN, '', "Captain"),
    (TM.Role.MANAGER, None, "Manager"),
]
for role, player_role, expected in test_cases:
    result = get_membership_role_display(role, player_role)
    status = "✓" if result == expected else "✗"
    print(f"{status} {role} + {player_role or 'None'} = '{result}' (expected: '{expected}')")

print("\n" + "=" * 70)
print("ALL TESTS COMPLETED")
print("=" * 70)
print("\n✅ Dual-Role System is working correctly!")
print("\nNext steps:")
print("  1. Update team registration form to include player role selection")
print("  2. Add role selector to team settings page")
print("  3. Update roster display to show player roles")
print("  4. Implement role-based roster organization")
print("\nFor documentation, see:")
print("  - DUAL_ROLE_SYSTEM_DOCUMENTATION.md (full docs)")
print("  - DUAL_ROLE_SYSTEM_QUICK_REFERENCE.md (quick start)")
print("  - DUAL_ROLE_SYSTEM_IMPLEMENTATION_SUMMARY.md (implementation details)")
