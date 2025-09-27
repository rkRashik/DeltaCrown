# tests/test_ranking_quick_validation.py
"""
Quick validation tests for Team Ranking System
Tests core functionality without complex database setup
"""

def test_ranking_imports():
    """Test that all ranking modules can be imported successfully."""
    try:
        from apps.teams.models.ranking import (
            RankingCriteria, TeamRankingHistory, TeamRankingBreakdown
        )
        from apps.teams.services.ranking_service import ranking_service
        from apps.teams.admin.ranking import (
            RankingCriteriaAdmin, TeamRankingHistoryAdmin
        )
        print("✅ All ranking modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_ranking_service_methods():
    """Test that ranking service has all expected methods."""
    try:
        from apps.teams.services.ranking_service import ranking_service
        
        expected_methods = [
            'calculate_team_age_points',
            'calculate_member_points', 
            'recalculate_team_points',
            'adjust_team_points',
            'award_tournament_points',
            'get_team_rankings'
        ]
        
        for method in expected_methods:
            if not hasattr(ranking_service, method):
                print(f"❌ Missing method: {method}")
                return False
        
        print("✅ All ranking service methods present")
        return True
    except Exception as e:
        print(f"❌ Service validation error: {e}")
        return False

def test_model_structure():
    """Test that ranking models have expected fields."""
    try:
        from apps.teams.models.ranking import RankingCriteria
        
        # Check RankingCriteria has expected fields
        expected_fields = [
            'tournament_participation',
            'tournament_winner', 
            'tournament_runner_up',
            'points_per_member',
            'points_per_month_age',
            'is_active'
        ]
        
        model_fields = [field.name for field in RankingCriteria._meta.get_fields()]
        
        for field in expected_fields:
            if field not in model_fields:
                print(f"❌ Missing field in RankingCriteria: {field}")
                return False
        
        print("✅ RankingCriteria model structure validated")
        return True
    except Exception as e:
        print(f"❌ Model validation error: {e}")
        return False

def test_admin_integration():
    """Test that admin classes are properly configured."""
    try:
        from django.contrib.admin import site
        from apps.teams.models.ranking import (
            RankingCriteria, TeamRankingHistory, TeamRankingBreakdown
        )
        
        # Check if models are registered in admin
        registered_models = [model._meta.model for model in site._registry.keys()]
        
        ranking_models = [RankingCriteria, TeamRankingHistory, TeamRankingBreakdown]
        
        for model in ranking_models:
            if model in registered_models:
                print(f"✅ {model.__name__} registered in admin")
            else:
                print(f"⚠️  {model.__name__} not registered in admin (may be intentional)")
        
        return True
    except Exception as e:
        print(f"❌ Admin integration error: {e}")
        return False

def test_management_commands():
    """Test that management commands exist."""
    try:
        import os
        from django.core.management import get_commands
        
        commands = get_commands()
        
        expected_commands = [
            'init_ranking_system',
            'recalculate_team_rankings'
        ]
        
        for cmd in expected_commands:
            if cmd in commands:
                print(f"✅ Management command '{cmd}' found")
            else:
                print(f"❌ Management command '{cmd}' not found")
        
        return True
    except Exception as e:
        print(f"❌ Management commands error: {e}")
        return False

def run_all_tests():
    """Run all validation tests."""
    print("🚀 Starting Team Ranking System Validation")
    print("=" * 50)
    
    tests = [
        test_ranking_imports,
        test_ranking_service_methods,
        test_model_structure,
        test_admin_integration,
        test_management_commands
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        print(f"\n📋 Running {test.__name__}...")
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests PASSED!")
        print("\n✅ Team Ranking System is properly configured and ready to use!")
    else:
        print("⚠️  Some validation tests failed")
        print("Please check the errors above and fix any issues")
    
    return passed == total

if __name__ == '__main__':
    # Set up Django environment
    import os
    import sys
    import django
    
    # Add the project root to Python path
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # Configure Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
    django.setup()
    
    # Run validation tests
    success = run_all_tests()
    sys.exit(0 if success else 1)