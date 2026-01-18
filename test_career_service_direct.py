"""
Direct CareerTabService Test - Bypass profile_story issue
"""
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.user_profile.models import GameProfile
from apps.user_profile.services.career_tab_service import CareerTabService
from django.core.serializers.json import DjangoJSONEncoder

User = get_user_model()

def test_career_service_directly():
    """Test CareerTabService methods directly"""
    print("\n" + "="*80)
    print("CAREER TAB SERVICE DIRECT TEST")
    print("="*80)
    
    # Find user with passport
    passport = GameProfile.objects.filter(
        visibility=GameProfile.VISIBILITY_PUBLIC,
        status=GameProfile.STATUS_ACTIVE
    ).select_related('user', 'game').first()
    
    if not passport:
        print("❌ No game passports found!")
        return
    
    user = passport.user
    print(f"\n✅ Testing with user: {user.username}")
    print(f"   Game: {passport.game.slug}")
    
    # Get profile - bypass profile_story column issue with only()
    from apps.user_profile.models import UserProfile
    user_profile = UserProfile.objects.only('id', 'user', 'primary_game').get(user=user)
    print(f"   Has profile: {user_profile is not None}")
    
    # Test 1: get_linked_games
    print("\n" + "-"*80)
    print("TEST 1: get_linked_games()")
    print("-"*80)
    try:
        linked_games = CareerTabService.get_linked_games(user_profile)
        print(f"✅ Returned {len(linked_games)} game(s)")
        for game_item in linked_games:
            print(f"   - {game_item['game_name']} (slug: {game_item['game_slug']}, is_primary: {game_item['is_primary']})")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: get_game_passport
    print("\n" + "-"*80)
    print("TEST 2: get_game_passport()")
    print("-"*80)
    try:
        passport_obj = CareerTabService.get_game_passport(user_profile, passport.game)
        if passport_obj:
            print(f"✅ Passport found")
            print(f"   - in_game_name: {passport_obj.in_game_name}")
            print(f"   - rank_name: {passport_obj.rank_name}")
            print(f"   - rank_tier: {passport_obj.rank_tier}")
        else:
            print("⚠️  No passport found")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: get_matches_played_count
    print("\n" + "-"*80)
    print("TEST 3: get_matches_played_count()")
    print("-"*80)
    try:
        count = CareerTabService.get_matches_played_count(user_profile, passport.game)
        print(f"✅ Matches played: {count}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: get_team_ranking
    print("\n" + "-"*80)
    print("TEST 4: get_team_ranking()")
    print("-"*80)
    try:
        ranking = CareerTabService.get_team_ranking(user_profile, passport.game)
        if ranking:
            print(f"✅ Team ranking found: {ranking}")
        else:
            print("✅ No team ranking (expected for users not in teams)")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: get_team_affiliation_history
    print("\n" + "-"*80)
    print("TEST 5: get_team_affiliation_history()")
    print("-"*80)
    try:
        team_history = CareerTabService.get_team_affiliation_history(user_profile, passport.game)
        print(f"✅ Team history: {len(team_history)} entries")
        for entry in team_history[:3]:
            print(f"   - {entry}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: get_achievements
    print("\n" + "-"*80)
    print("TEST 6: get_achievements()")
    print("-"*80)
    try:
        achievements = CareerTabService.get_achievements(user_profile, passport.game)
        print(f"✅ Achievements: {len(achievements)} entries")
        for entry in achievements[:3]:
            print(f"   - {entry}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 7: get_display_attributes
    print("\n" + "-"*80)
    print("TEST 7: get_display_attributes()")
    print("-"*80)
    try:
        attrs = CareerTabService.get_display_attributes(passport_obj)
        print(f"✅ Display attributes: {len(attrs)} entries")
        for attr in attrs:
            print(f"   - {attr['label']}: {attr['value']}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 8: JSON Serialization Test
    print("\n" + "-"*80)
    print("TEST 8: JSON Serialization (Full Career Data Payload)")
    print("-"*80)
    try:
        # Build full payload like career_tab_data_api does
        passport_obj = CareerTabService.get_game_passport(user_profile, passport.game)
        
        career_data = {
            'game_slug': passport.game.slug,
            'game_name': passport.game.display_name,
            'passport': {
                'in_game_name': passport_obj.in_game_name if passport_obj else None,
                'rank_name': passport_obj.rank_name if passport_obj else 'Unranked',
                'rank_tier': passport_obj.rank_tier if passport_obj else 0,
                'rank_points': passport_obj.rank_points if passport_obj else None,
                'peak_rank': passport_obj.peak_rank if passport_obj else None,
                'game_name': passport.game.display_name,
            } if passport_obj else None,
            'display_attributes': CareerTabService.get_display_attributes(passport_obj),
            'matches_played': CareerTabService.get_matches_played_count(user_profile, passport.game),
            'team_ranking': CareerTabService.get_team_ranking(user_profile, passport.game),
            'team_history': CareerTabService.get_team_affiliation_history(user_profile, passport.game),
            'achievements': CareerTabService.get_achievements(user_profile, passport.game),
        }
        
        # Try to serialize
        json_str = json.dumps(career_data, cls=DjangoJSONEncoder, indent=2)
        print("✅ JSON serialization successful!")
        print(f"\n📦 Payload size: {len(json_str)} bytes")
        print(f"\n📋 Sample JSON (first 500 chars):")
        print(json_str[:500])
        
        # Check for Django model instances
        def check_for_models(obj, path="root"):
            issues = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    issues.extend(check_for_models(v, f"{path}.{k}"))
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    issues.extend(check_for_models(v, f"{path}[{i}]"))
            elif hasattr(obj, '_meta'):  # Django model
                issues.append(f"❌ Django model at: {path} (type: {type(obj).__name__})")
            return issues
        
        issues = check_for_models(career_data)
        if issues:
            print("\n⚠️  JSON SAFETY ISSUES:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n✅ All data is JSON-safe (no Django model instances)")
    
    except Exception as e:
        print(f"❌ JSON serialization failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_career_service_directly()
    
    print("\n" + "="*80)
    print("✅ CAREER TAB SERVICE TEST COMPLETE")
    print("="*80)
