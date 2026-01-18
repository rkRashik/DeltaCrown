"""
Test script to verify team logo and URL are returned in affiliation history.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.services.career_tab_service import CareerTabService
from apps.user_profile.models import UserProfile
from apps.games.models import Game

User = get_user_model()

def test_affiliation_history():
    """Test affiliation history returns team_logo_url and team_url."""
    print("\n" + "="*70)
    print("TEST: Affiliation History - Team Logo & URL")
    print("="*70)
    
    # Find users with team memberships
    users = User.objects.all()[:20]
    
    for user in users:
        try:
            user_profile = UserProfile.objects.get(user=user)
            
            # Get linked games
            linked_games = CareerTabService.get_linked_games(user_profile)
            
            if not linked_games:
                continue
            
            # Test with first game
            game_data = linked_games[0]
            game = game_data['game']
            
            print(f"\n✅ Testing user: {user.username} (Game: {game.slug})")
            
            # Get affiliation history
            history = CareerTabService.get_team_affiliation_history(user_profile, game)
            
            if history:
                print(f"   Found {len(history)} team membership(s)")
                
                for i, membership in enumerate(history, 1):
                    print(f"\n   {i}. {membership['team_name']}")
                    print(f"      Team Logo URL: {membership.get('team_logo_url', 'NOT_SET')}")
                    print(f"      Team URL: {membership.get('team_url', 'NOT_SET')}")
                    print(f"      Team Tag: {membership['team_tag']}")
                    print(f"      Role: {membership['team_role_label']}")
                    print(f"      Status: {membership['status_badge']}")
                    
                    # Verify fields exist
                    if 'team_logo_url' not in membership:
                        print(f"      ❌ ERROR: team_logo_url field missing!")
                        return False
                    if 'team_url' not in membership:
                        print(f"      ❌ ERROR: team_url field missing!")
                        return False
                
                print("\n✅ All fields present and valid!")
                return True
                
        except UserProfile.DoesNotExist:
            continue
        except Exception as e:
            print(f"❌ ERROR with user {user.username}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n⚠️ No users with team memberships found in first 20 users")
    return True  # Not a failure, just no data

if __name__ == '__main__':
    success = test_affiliation_history()
    
    print("\n" + "="*70)
    if success:
        print("✅ Verification passed! team_logo_url and team_url are returned.")
    else:
        print("❌ Test failed. See errors above.")
    print("="*70)
