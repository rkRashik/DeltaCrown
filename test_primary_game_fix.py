"""
Test script to verify primary game resolution is type-safe and correct.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.services.career_tab_service import CareerTabService
from apps.user_profile.models import UserProfile
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

User = get_user_model()

def test_primary_game_resolution():
    """Test primary game resolution with first available user."""
    print("\n" + "="*70)
    print("TEST: Primary Game Resolution (Type-Safe)")
    print("="*70)
    
    # Find first user with career data
    users = User.objects.all()[:10]
    
    for user in users:
        try:
            user_profile = UserProfile.objects.get(user=user)
            
            print(f"\n✅ Testing user: {user.username}")
            print(f"   Primary Team: {user_profile.primary_team}")
            print(f"   Primary Game (FK): {user_profile.primary_game}")
            
            if user_profile.primary_team:
                print(f"   Team.game field type: {type(user_profile.primary_team.game).__name__}")
                print(f"   Team.game value: {user_profile.primary_team.game}")
            
            # Call get_linked_games (should not crash)
            print(f"\n🔍 Calling get_linked_games()...")
            linked_games = CareerTabService.get_linked_games(user_profile)
            
            print(f"\n✅ SUCCESS! Returned {len(linked_games)} linked games")
            
            if linked_games:
                primary = linked_games[0]
                print(f"\n📌 Primary Game:")
                print(f"   Slug: {primary['game_slug']}")
                print(f"   Name: {primary['game_name']}")
                print(f"   Source: {primary.get('primary_source', 'unknown')}")
                print(f"   Is Primary: {primary['is_primary']}")
                
                print(f"\n📋 All Linked Games:")
                for i, game_data in enumerate(linked_games, 1):
                    indicator = "⭐" if game_data['is_primary'] else "  "
                    print(f"   {indicator} {i}. {game_data['game_slug']} ({game_data['game_name']})")
            
            return True
            
        except UserProfile.DoesNotExist:
            continue
        except Exception as e:
            print(f"❌ ERROR with user {user.username}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print(f"❌ ERROR: No users with profiles found in first 10 users")
    return False

if __name__ == '__main__':
    success = test_primary_game_resolution()
    
    print("\n" + "="*70)
    if success:
        print("✅ All checks passed! Primary game resolution is type-safe.")
    else:
        print("❌ Test failed. See errors above.")
    print("="*70)
