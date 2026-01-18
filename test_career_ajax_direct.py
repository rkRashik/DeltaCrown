"""
Direct test of career_tab_data_api AJAX endpoint
Bypasses DB migration issues by using Request Factory
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.user_profile.views.public_profile_views import career_tab_data_api
from apps.games.models import Game
from apps.user_profile.models import GameProfile
import json

User = get_user_model()

def test_ajax_endpoint_directly():
    """Test career_tab_data_api() directly using RequestFactory"""
    
    print("\n" + "="*80)
    print("CAREER TAB AJAX ENDPOINT DIRECT TEST")
    print("="*80)
    
    # Find a user with game passports
    passport = (GameProfile.objects
                .filter(user__isnull=False)
                .select_related('user', 'game')
                .first())
    
    if not passport:
        print("\n❌ No game passports found in database")
        return
    
    user = passport.user
    game = passport.game
    
    print(f"\n✅ Testing with user: {user.username}")
    print(f"   Game: {game.slug}")
    
    # Create mock request
    factory = RequestFactory()
    request = factory.get(f'/@{user.username}/career-data/', {'game': game.slug})
    request.user = user  # Simulate authenticated request
    
    # Call view directly
    print("\n" + "-"*80)
    print(f"CALLING: career_tab_data_api(request, username='{user.username}')")
    print("-"*80)
    
    try:
        response = career_tab_data_api(request, username=user.username)
        
        print(f"\n✅ Response Status: {response.status_code}")
        print(f"   Content-Type: {response.get('Content-Type', 'not set')}")
        
        if response.status_code == 200:
            # Parse JSON
            data = json.loads(response.content.decode('utf-8'))
            
            print("\n" + "-"*80)
            print("RESPONSE JSON STRUCTURE")
            print("-"*80)
            print(f"Keys in response: {list(data.keys())}")
            print(f"\nFull JSON:")
            print(json.dumps(data, indent=2)[:1000])
            
            # Check if it's the expected structure
            if 'success' in data:
                print(f"\n✅ success: {data.get('success')}")
            
            if 'data' in data:
                career_data = data['data']
                print(f"\n📊 Career Data Keys: {list(career_data.keys())}")
                
                # Check passport data
                if 'passport' in career_data:
                    passport_data = career_data['passport']
                    print(f"\n🎮 Passport Data:")
                    print(f"   - in_game_name: {passport_data.get('in_game_name')}")
                    print(f"   - rank_name: {passport_data.get('rank_name')}")
                    print(f"   - rank_tier: {passport_data.get('rank_tier')}")
                    print(f"   - rank_points: {passport_data.get('rank_points')}")
                    print(f"   - peak_rank: {passport_data.get('peak_rank')}")
                
                # Check match stats
                if 'matches_played' in career_data:
                    print(f"\n📈 Matches Played: {career_data['matches_played']}")
                
                # Check team ranking
                if 'team_ranking' in career_data:
                    ranking = career_data['team_ranking']
                    print(f"\n🏆 Team Ranking:")
                    print(f"   - team_name: {ranking.get('team_name')}")
                    print(f"   - rank: {ranking.get('rank')}")
                    print(f"   - points: {ranking.get('points')}")
                
                # Check team history
                if 'team_history' in career_data:
                    history = career_data['team_history']
                    print(f"\n👥 Team History: {len(history)} affiliations")
                
                # Check achievements
                if 'achievements' in career_data:
                    achievements = career_data['achievements']
                    print(f"\n🏅 Achievements: {len(achievements)} earned")
                
                # Check display attributes
                if 'display_attributes' in career_data:
                    attrs = career_data['display_attributes']
                    print(f"\n🎨 Display Attributes: {len(attrs)} items")
                
                # CRITICAL: Verify JSON serialization (no Django model instances)
                print("\n" + "-"*80)
                print("JSON SERIALIZATION VALIDATION")
                print("-"*80)
                
                def check_for_django_models(obj, path=""):
                    """Recursively check for Django model instances"""
                    issues = []
                    
                    if hasattr(obj, '_meta'):  # Django model check
                        issues.append(f"Django model at {path}: {type(obj).__name__}")
                    elif isinstance(obj, dict):
                        for key, value in obj.items():
                            issues.extend(check_for_django_models(value, f"{path}.{key}"))
                    elif isinstance(obj, (list, tuple)):
                        for i, item in enumerate(obj):
                            issues.extend(check_for_django_models(item, f"{path}[{i}]"))
                    
                    return issues
                
                model_issues = check_for_django_models(career_data, "data")
                
                if model_issues:
                    print("❌ FAILED: Found Django model instances in payload:")
                    for issue in model_issues:
                        print(f"   - {issue}")
                else:
                    print("✅ PASSED: No Django model instances found")
                    print("✅ Payload is JSON-safe")
                
                # Show sample JSON
                print("\n" + "-"*80)
                print("SAMPLE JSON OUTPUT (first 500 chars)")
                print("-"*80)
                json_str = json.dumps(data, indent=2)
                print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
            
            else:
                print("\n❌ No 'data' key in response")
        
        else:
            print(f"\n❌ Request failed with status {response.status_code}")
            print(f"   Response: {response.content.decode('utf-8')[:500]}")
    
    except Exception as e:
        print(f"\n❌ Exception occurred:")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    test_ajax_endpoint_directly()
