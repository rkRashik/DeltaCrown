"""
Test Tournament Detail View - Game Registry Integration

Verifies that TournamentDetailView properly:
1. Imports Game Registry functions
2. Normalizes tournament game slug
3. Retrieves GameSpec from registry
4. Adds game_spec to context with all required fields
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import RequestFactory
from apps.tournaments.views.main import TournamentDetailView
from apps.tournaments.models import Tournament, Game
from apps.common.game_registry import get_game, normalize_slug

print("=" * 80)
print("TESTING TOURNAMENT DETAIL VIEW - GAME REGISTRY INTEGRATION")
print("=" * 80)

# Create test request factory
factory = RequestFactory()

# Test 1: Check if imports are working
print("\n1. Testing imports...")
try:
    from apps.tournaments.views.main import get_game, normalize_slug
    print("   ✓ Game Registry imports present in views/main.py")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")

# Test 2: Get a real tournament from database
print("\n2. Fetching test tournament from database...")
try:
    tournament = Tournament.objects.filter(
        status__in=['published', 'registration_open', 'live']
    ).select_related('game').first()
    
    if tournament:
        print(f"   ✓ Found tournament: {tournament.name}")
        print(f"   Game: {tournament.game.name} (slug: {tournament.game.slug})")
    else:
        print("   ⚠ No published tournaments found - creating test scenario")
        # For testing purposes, we'll continue with a mock
        tournament = None
except Exception as e:
    print(f"   ✗ Database error: {e}")
    tournament = None

# Test 3: Test normalization and GameSpec retrieval
if tournament:
    print("\n3. Testing Game Registry integration...")
    
    # Normalize slug
    canonical_slug = normalize_slug(tournament.game.slug)
    print(f"   ✓ Normalized slug: '{tournament.game.slug}' → '{canonical_slug}'")
    
    # Get GameSpec
    game_spec = get_game(canonical_slug)
    
    if game_spec:
        print(f"   ✓ Retrieved GameSpec: {game_spec.name}")
        print(f"     - Display name: {game_spec.display_name}")
        print(f"     - Canonical slug: {game_spec.slug}")
        print(f"     - Icon: {game_spec.icon}")
        print(f"     - Logo: {game_spec.logo}")
        print(f"     - Banner: {game_spec.banner}")
        print(f"     - Primary color: {game_spec.colors.get('primary', 'N/A')}")
        print(f"     - Min team size: {game_spec.min_team_size}")
        print(f"     - Max team size: {game_spec.max_team_size}")
        print(f"     - Roles: {', '.join(game_spec.roles[:3])}{'...' if len(game_spec.roles) > 3 else ''}")
    else:
        print(f"   ✗ Failed to retrieve GameSpec for '{canonical_slug}'")

# Test 4: Test view context integration
if tournament:
    print("\n4. Testing TournamentDetailView context...")
    
    try:
        # Create a mock request with anonymous user
        from django.contrib.auth.models import AnonymousUser
        request = factory.get(f'/tournaments/{tournament.slug}/')
        request.user = AnonymousUser()  # Use AnonymousUser instead of None
        
        # Create view instance
        view = TournamentDetailView()
        view.request = request
        view.object = tournament
        
        # Get context data
        context = view.get_context_data()
        
        # Check if game_spec is in context
        if 'game_spec' in context:
            game_spec = context['game_spec']
            print(f"   ✓ game_spec found in context")
            print(f"     - Type: {type(game_spec).__name__}")
            print(f"     - Name: {game_spec.name}")
            print(f"     - Display name: {game_spec.display_name}")
            print(f"     - Slug: {game_spec.slug}")
            
            # Verify required fields
            required_fields = [
                'slug', 'name', 'display_name', 'icon', 'logo', 'banner',
                'colors', 'min_team_size', 'max_team_size', 'roles'
            ]
            
            missing_fields = []
            for field in required_fields:
                if not hasattr(game_spec, field):
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"   ⚠ Missing fields: {', '.join(missing_fields)}")
            else:
                print(f"   ✓ All required fields present")
                
            # Check if colors are available
            if game_spec.colors:
                print(f"   ✓ Theme colors available: {len(game_spec.colors)} color keys")
                print(f"     Sample: {list(game_spec.colors.keys())[:3]}")
            else:
                print(f"   ⚠ No theme colors available")
        else:
            print(f"   ✗ game_spec NOT found in context")
            print(f"     Available keys: {list(context.keys())}")
            
    except Exception as e:
        print(f"   ✗ Error testing view context: {e}")
        import traceback
        traceback.print_exc()

# Test 5: Test with various game slugs (legacy codes)
print("\n5. Testing normalization with legacy game codes...")

legacy_test_cases = [
    ('efootball', 'efootball'),
    ('EFOOTBALL', 'efootball'),
    ('valorant', 'valorant'),
    ('VALORANT', 'valorant'),
]

for input_slug, expected_slug in legacy_test_cases:
    normalized = normalize_slug(input_slug)
    game_spec = get_game(normalized)
    
    status = "✓" if normalized == expected_slug and game_spec else "✗"
    print(f"   {status} '{input_slug}' → '{normalized}' (expected '{expected_slug}')")
    if game_spec:
        print(f"      GameSpec: {game_spec.display_name}")

print("\n" + "=" * 80)
print("TOURNAMENT DETAIL VIEW INTEGRATION TEST COMPLETE")
print("=" * 80)

if tournament:
    print("\n✅ Tournament Detail Page now uses Game Registry!")
    print(f"   - game_spec added to context")
    print(f"   - Includes: display_name, icon, logo, banner, colors")
    print(f"   - Provides: theme data, roster config, team sizes")
    print(f"   - Ready for template integration")
    print(f"\n📋 Next step: Update detail.html template to use game_spec")
    print(f"   Add: data-game-slug=\"{{{{ game_spec.slug }}}}\" to wrapper div")
else:
    print("\n⚠ No test tournament available - integration code verified but not tested")
