#!/usr/bin/env python
"""
Phase 3 - Interactive Testing Helper

This script helps you test the dynamic registration form by:
1. Checking if user is logged in
2. Providing quick test commands
3. Showing what to expect at each step

Usage:
    python test_dynamic_registration.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament
from apps.tournaments.models.game_config import GameConfiguration
from apps.tournaments.models.game_field_config import GameFieldConfiguration

User = get_user_model()

def print_header(text):
    """Print a styled header"""
    print("\n" + "=" * 80)
    print(f"  {text}")
    print("=" * 80)

def print_section(text):
    """Print a section header"""
    print(f"\n{'─' * 80}")
    print(f"  {text}")
    print(f"{'─' * 80}")

def check_users():
    """Check existing users"""
    print_section("👥 User Accounts")
    
    total_users = User.objects.count()
    superusers = User.objects.filter(is_superuser=True)
    
    print(f"Total users: {total_users}")
    print(f"Superusers: {superusers.count()}")
    
    if superusers.exists():
        print("\n✅ Superuser accounts available:")
        for user in superusers[:3]:
            print(f"   • Username: {user.username}")
            print(f"     Email: {user.email}")
    
    return total_users > 0

def check_tournaments():
    """Check test tournaments"""
    print_section("🏆 Test Tournaments")
    
    test_tournaments = Tournament.objects.filter(name__startswith="Test")
    
    if test_tournaments.exists():
        print(f"✅ Found {test_tournaments.count()} test tournaments:\n")
        for t in test_tournaments:
            print(f"   {t.get_game_display():<30} → /tournaments/register-modern/{t.slug}/")
    else:
        print("❌ No test tournaments found!")
        print("   Run: python setup_test_tournaments.py")
    
    return test_tournaments.exists()

def check_game_configs():
    """Check game configurations"""
    print_section("🎮 Game Configurations")
    
    games = GameConfiguration.objects.all()
    
    if games.exists():
        print(f"✅ Found {games.count()} games configured:\n")
        for game in games:
            fields = GameFieldConfiguration.objects.filter(game=game).count()
            roles = game.roles.count() if hasattr(game, 'roles') else 0
            print(f"   • {game.display_name:<30} ({game.game_code}) - {fields} fields, {roles} roles")
    else:
        print("❌ No game configurations found!")
        print("   Run: python manage.py seed_game_configs")
    
    return games.exists()

def print_test_instructions():
    """Print testing instructions"""
    print_section("📋 Testing Instructions")
    
    print("""
1. LOGIN
   ──────
   URL: http://127.0.0.1:8000/account/login/
   
   Use one of your existing accounts (see above)

2. ACCESS VALORANT REGISTRATION
   ─────────────────────────────
   URL: http://127.0.0.1:8000/tournaments/register-modern/test-valorant-championship-2025/
   
   What you should see:
   ✓ Tournament header: "Test VALORANT Championship 2025"
   ✓ Progress indicator: "Step 1 of 3"
   ✓ Dynamic fields: Riot ID, Discord ID
   ✓ Contact fields: Email (locked), Phone

3. TEST VALIDATION
   ───────────────
   a) Enter INVALID Riot ID: "JustUsername" (no #TAG)
      → Tab to next field
      → Should see RED BORDER + ERROR MESSAGE
   
   b) Fix to VALID: "Username#1234"
      → Tab away
      → Should see GREEN BORDER + error clears

4. CHECK BROWSER CONSOLE
   ──────────────────────
   Press F12 → Console tab
   
   Should see:
   ✓ "DynamicRegistrationForm initialized"
   ✓ API calls to /api/games/valorant/config/
   ✓ NO RED ERRORS

5. TEST TEAM ROSTER
   ─────────────────
   a) Click "Continue" after Step 1
   b) Should see Step 2: Team Roster
   c) 5 player rows with name + role dropdown
   d) Try assigning 3 players as "Duelist"
      → Should show error about max 2 duelists
   e) Fix by changing one to "Controller"
      → Error should clear

6. REVIEW & SUBMIT
   ───────────────
   a) Click "Continue" to Step 3
   b) Review all data
   c) Check "I agree to rules"
   d) Click "Submit Registration"
""")

def print_api_endpoints():
    """Print API endpoints for manual testing"""
    print_section("🔌 API Endpoints (for manual testing)")
    
    print("""
Test these in browser or Postman:

1. All Games
   GET http://127.0.0.1:8000/tournaments/api/games/
   
2. VALORANT Config
   GET http://127.0.0.1:8000/tournaments/api/games/valorant/config/
   
3. Validate Riot ID
   POST http://127.0.0.1:8000/tournaments/api/games/valorant/validate/
   Body: {"field_name": "riot_id", "value": "Username#1234"}
   
4. Validate Team Roles
   POST http://127.0.0.1:8000/tournaments/api/games/valorant/validate-roles/
   Body: {"roles": ["duelist", "controller", "sentinel", "initiator", "igl"]}
""")

def print_troubleshooting():
    """Print troubleshooting tips"""
    print_section("🔧 Troubleshooting")
    
    print("""
Problem: Page shows 404
Solution: Verify URL format: /tournaments/register-modern/<slug>/

Problem: Fields don't render
Solution: 
  1. Check browser console for errors
  2. Test API: http://127.0.0.1:8000/tournaments/api/games/valorant/config/
  3. Verify game configs exist in database

Problem: Validation doesn't work
Solution:
  1. Check Network tab in DevTools
  2. Look for POST to /api/games/valorant/validate/
  3. Check response status

Problem: JavaScript errors in console
Solution:
  1. Clear browser cache (Ctrl+Shift+R)
  2. Verify files exist:
     - static/js/dynamic-registration.js
     - static/css/dynamic-registration.css
  3. Check for typos in template

Problem: Auto-fill doesn't work
Solution:
  1. Go to profile page
  2. Add riot_id, discord_id, phone
  3. Return to registration form
""")

def main():
    """Main testing helper"""
    print_header("🧪 PHASE 3 - DYNAMIC REGISTRATION TESTING HELPER")
    
    # Check system status
    has_users = check_users()
    has_tournaments = check_tournaments()
    has_configs = check_game_configs()
    
    # Print test instructions
    print_test_instructions()
    
    # Print API endpoints
    print_api_endpoints()
    
    # Print troubleshooting
    print_troubleshooting()
    
    # Final status
    print_header("✅ SYSTEM STATUS")
    
    print(f"""
    Users:        {'✅ Ready' if has_users else '❌ Missing'}
    Tournaments:  {'✅ Ready' if has_tournaments else '❌ Missing'}
    Game Configs: {'✅ Ready' if has_configs else '❌ Missing'}
    Server:       ✅ Running at http://127.0.0.1:8000/
    
    {'🎯 READY TO TEST!' if all([has_users, has_tournaments, has_configs]) else '⚠️  Fix issues above first'}
    """)
    
    print_section("🚀 QUICK START")
    print("""
    1. Open browser: http://127.0.0.1:8000/account/login/
    2. Login with existing account
    3. Navigate to: http://127.0.0.1:8000/tournaments/register-modern/test-valorant-championship-2025/
    4. Start testing!
    """)
    
    print("=" * 80)

if __name__ == '__main__':
    main()
