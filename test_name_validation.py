"""
Test script to verify team name normalization logic
Run with: python manage.py shell < test_name_validation.py
"""

from apps.organizations.models import Team
from apps.games.models import Game

print("=" * 60)
print("TEAM NAME NORMALIZATION TEST")
print("=" * 60)

# List all teams
teams = Team.objects.all()
print(f"\nTotal teams in database: {teams.count()}\n")

if teams.count() == 0:
    print("No teams found in database.")
else:
    print("Existing teams:")
    for t in teams:
        normalized = t.name.upper().replace(' ', '')
        org_name = t.organization.name if t.organization else "Independent"
        print(f"  ID: {t.id}")
        print(f"  Name: '{t.name}'")
        print(f"  Normalized: '{normalized}'")
        print(f"  Game ID: {t.game_id}")
        print(f"  Organization: {org_name}")
        print()

# Test normalization examples
print("\n" + "=" * 60)
print("NORMALIZATION EXAMPLES")
print("=" * 60)

test_names = [
    "Test Team",
    "testteam",
    "TEST TEAM",
    "T E S T T E A M",
    "TeSt TeAm",
    "Test  Team",
    " Test Team ",
]

print("\nAll these names will be normalized to the same value:")
for name in test_names:
    normalized = name.upper().replace(' ', '')
    print(f"  '{name}' -> '{normalized}'")

print("\n" + "=" * 60)
print("DUPLICATE CHECK SIMULATION")
print("=" * 60)

# Simulate a duplicate check
test_name = "Test Team"
normalized_input = test_name.upper().replace(' ', '')
print(f"\nChecking if '{test_name}' (normalized: '{normalized_input}') exists...")

game_id = 6  # Game ID where Test Team exists
mode = 'independent'  # or 'organization'

print(f"Game ID: {game_id}")
print(f"Mode: {mode}")

query = Team.objects.filter(game_id=game_id)
if mode == 'independent':
    query = query.filter(organization__isnull=True)

print(f"\nTeams found for this game/mode: {query.count()}")

duplicate_found = False
for team in query:
    team_normalized = team.name.upper().replace(' ', '')
    matches = (team_normalized == normalized_input)
    print(f"  '{team.name}' -> '{team_normalized}' ... {'MATCH!' if matches else 'different'}")
    if matches:
        duplicate_found = True
        break

print(f"\nResult: {'DUPLICATE FOUND - Should reject' if duplicate_found else 'NO DUPLICATE - Should allow'}")
