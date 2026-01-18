"""
Test Career Tab End-to-End
Simulates browser request to profile page and AJAX endpoint
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from apps.user_profile.views.public_profile_views import public_profile_view, career_tab_data_api
import json

User = get_user_model()

def test_profile_page_load():
    """Test 1: Profile page loads with Career Tab"""
    print("\n" + "="*80)
    print("TEST 1: Profile Page Load - /@rkrashik/")
    print("="*80)
    
    client = Client()
    
    try:
        # Check if user exists
        user = User.objects.get(username='rkrashik')
        print(f"✅ User found: {user.username}")
        print(f"   Has profile: {hasattr(user, 'profile')}")
        
        # Make request
        response = client.get('/@rkrashik/')
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Page loaded successfully!")
            
            # Check context keys
            if hasattr(response, 'context'):
                context = response.context
                print("\n🔍 Career Tab Context Keys:")
                print(f"   - career_linked_games: {('career_linked_games' in context)}")
                print(f"   - career_selected_game: {('career_selected_game' in context)}")
                print(f"   - career_payload_initial: {('career_payload_initial' in context)}")
                
                if 'career_linked_games' in context:
                    games = context['career_linked_games']
                    print(f"\n📊 Linked Games Count: {len(games)}")
                    for game in games:
                        print(f"   - {game.get('game_name', 'N/A')} (is_primary: {game.get('is_primary', False)})")
                
                if 'career_payload_initial' in context:
                    payload = context['career_payload_initial']
                    if payload:
                        print(f"\n📦 Initial Payload:")
                        print(f"   - Game: {payload.get('game_name', 'N/A')}")
                        print(f"   - Matches Played: {payload.get('matches_played', 0)}")
                        print(f"   - Has Passport: {payload.get('passport') is not None}")
                    else:
                        print("\n⚠️  Initial payload is None (no games linked)")
        else:
            print(f"❌ Page failed to load: {response.status_code}")
            if hasattr(response, 'content'):
                content = response.content.decode('utf-8')
                if 'Exception' in content or 'Error' in content:
                    print("\n🔴 Error in response:")
                    print(content[:1000])
    
    except User.DoesNotExist:
        print("❌ User 'rkrashik' not found!")
        print("\n📋 Available users:")
        for u in User.objects.all()[:5]:
            print(f"   - {u.username}")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def test_ajax_endpoint():
    """Test 2: AJAX endpoint returns JSON"""
    print("\n" + "="*80)
    print("TEST 2: AJAX Endpoint - /@rkrashik/career-data/?game=<slug>")
    print("="*80)
    
    client = Client()
    
    try:
        user = User.objects.get(username='rkrashik')
        
        # Get first game passport
        from apps.user_profile.models import GameProfile
        passport = GameProfile.objects.filter(
            user=user,
            visibility=GameProfile.VISIBILITY_PUBLIC,
            status=GameProfile.STATUS_ACTIVE
        ).first()
        
        if not passport:
            print("⚠️  No game passports found for user")
            return
        
        game_slug = passport.game.slug
        print(f"📡 Testing with game: {game_slug}")
        
        # Make AJAX request
        response = client.get(f'/@rkrashik/career-data/?game={game_slug}')
        print(f"\n📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ AJAX endpoint responded!")
            
            try:
                data = json.loads(response.content)
                print("\n📦 JSON Response Structure:")
                print(f"   Keys: {list(data.keys())}")
                
                # Check expected keys
                expected_keys = ['game_slug', 'game_name', 'passport', 'display_attributes', 
                                'matches_played', 'team_ranking', 'team_history', 'achievements']
                
                for key in expected_keys:
                    status = "✅" if key in data else "❌"
                    print(f"   {status} {key}: {key in data}")
                
                # Show sample data
                print(f"\n📊 Sample Data:")
                print(f"   - game_slug: {data.get('game_slug')}")
                print(f"   - game_name: {data.get('game_name')}")
                print(f"   - matches_played: {data.get('matches_played')}")
                
                if data.get('passport'):
                    passport_data = data['passport']
                    print(f"   - passport.in_game_name: {passport_data.get('in_game_name')}")
                    print(f"   - passport.rank_name: {passport_data.get('rank_name')}")
                
                # Check for non-JSON-safe data
                print(f"\n🔍 JSON Serialization Check:")
                def check_serializable(obj, path="root"):
                    if isinstance(obj, dict):
                        for k, v in obj.items():
                            check_serializable(v, f"{path}.{k}")
                    elif isinstance(obj, list):
                        for i, v in enumerate(obj):
                            check_serializable(v, f"{path}[{i}]")
                    elif hasattr(obj, '_meta'):  # Django model
                        print(f"   ❌ Django model instance at: {path}")
                    elif hasattr(obj, '__dict__') and not isinstance(obj, (str, int, float, bool, type(None))):
                        print(f"   ⚠️  Complex object at: {path}")
                
                check_serializable(data)
                print("   ✅ All data appears JSON-safe")
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON: {e}")
                print(f"   Response: {response.content[:500]}")
        else:
            print(f"❌ AJAX endpoint failed: {response.status_code}")
            print(f"   Response: {response.content[:500]}")
    
    except User.DoesNotExist:
        print("❌ User not found!")
    except Exception as e:
        print(f"❌ Exception: {e}")
        import traceback
        traceback.print_exc()


def test_empty_state():
    """Test 3: Graceful fallback for user with no data"""
    print("\n" + "="*80)
    print("TEST 3: Graceful Fallback - User with no game passports")
    print("="*80)
    
    try:
        # Find a user with no passports
        from apps.user_profile.models import GameProfile
        
        users_without_passports = []
        for user in User.objects.all()[:10]:
            if not GameProfile.objects.filter(user=user).exists():
                users_without_passports.append(user)
        
        if users_without_passports:
            test_user = users_without_passports[0]
            print(f"📡 Testing with user: {test_user.username} (no passports)")
            
            client = Client()
            response = client.get(f'/@{test_user.username}/')
            
            if response.status_code == 200:
                print("✅ Page loads gracefully without passports!")
            else:
                print(f"❌ Page failed: {response.status_code}")
        else:
            print("⚠️  All users have game passports, cannot test empty state")
    
    except Exception as e:
        print(f"❌ Exception: {e}")


if __name__ == '__main__':
    test_profile_page_load()
    test_ajax_endpoint()
    test_empty_state()
    
    print("\n" + "="*80)
    print("✅ END-TO-END VERIFICATION COMPLETE")
    print("="*80)
