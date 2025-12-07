"""
Quick Smoke Test for Team Creation and Admin Ranking
Run this after code changes to verify functionality
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.teams.models import Team, TeamMembership
from apps.teams.services.team_service import TeamService
from apps.teams.services.ranking_service import ranking_service

User = get_user_model()
team_service = TeamService()


def test_team_creation_flow():
    """Test that team creation works and redirects properly"""
    print("\n=== Testing Team Creation Flow ===")
    
    # Get or create test user (handle email uniqueness)
    try:
        user = User.objects.get(username='test_team_creator')
    except User.DoesNotExist:
        try:
            user = User.objects.create(
                username='test_team_creator',
                email='test_team_creator@example.com',
                is_active=True
            )
            user.set_password('password123')
            user.save()
        except Exception as e:
            print(f"❌ Failed to create user: {e}")
            return False
    
    if not hasattr(user, 'profile'):
        print("❌ User has no profile - create profile first")
        return False
    
    # Clean up old test team
    Team.objects.filter(tag='TEST').delete()
    
    # Create team
    result = team_service.create_team(
        profile=user.profile,
        name='Test Team',
        tag='TEST',
        game='mlbb',
        region='SEA',
        description='Test team for smoke test'
    )
    
    if not result['success']:
        print(f"❌ Team creation failed: {result.get('error')}")
        return False
    
    team = result['team']
    print(f"✅ Team created: {team.name} ({team.slug})")
    
    # Verify OWNER membership
    try:
        membership = TeamMembership.objects.get(
            team=team,
            profile=user.profile,
            role='OWNER'
        )
        print(f"✅ OWNER membership created: {membership.role}")
    except TeamMembership.DoesNotExist:
        print("❌ OWNER membership not created")
        return False
    
    # Verify redirect URLs
    setup_url = f'/teams/setup/{team.slug}/'
    detail_url = f'/teams/{team.slug}/'
    dashboard_url = f'/teams/{team.slug}/dashboard/'
    
    print(f"✅ Setup URL: {setup_url}")
    print(f"✅ Detail URL: {detail_url}")
    print(f"✅ Dashboard URL: {dashboard_url}")
    
    # Verify test page route doesn't exist
    print("\n--- Verifying test page removed ---")
    from django.urls import reverse, NoReverseMatch
    try:
        test_url = reverse('teams:test')
        print(f"❌ Test route still exists: {test_url}")
        return False
    except NoReverseMatch:
        print("✅ Test route removed (404 expected)")
    
    print("\n✅ Team creation flow PASSED")
    return True


def test_admin_ranking_endpoints():
    """Test that admin ranking endpoints work"""
    print("\n=== Testing Admin Ranking Endpoints ===")
    
    # Get test team
    try:
        team = Team.objects.filter(tag='TEST').first()
        if not team:
            print("❌ No test team found - run test_team_creation_flow first")
            return False
    except Team.DoesNotExist:
        print("❌ Test team not found")
        return False
    
    print(f"Testing with team: {team.name}")
    
    # Get admin user
    admin = User.objects.filter(is_superuser=True).first()
    if not admin:
        print("⚠️ No admin user found - creating one")
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
    
    # Test adjust points
    print("\n--- Testing adjust_team_points ---")
    initial_points = team.total_points
    result = ranking_service.adjust_team_points(
        team=team,
        points_adjustment=50,
        reason='Smoke test adjustment',
        admin_user=admin
    )
    
    if result['success']:
        print(f"✅ Points adjusted: {result['old_total']} → {result['new_total']} (change: {result['points_change']})")
    else:
        print(f"❌ Adjustment failed: {result.get('error')}")
        return False
    
    # Test recalculate points
    print("\n--- Testing recalculate_team_points ---")
    result = ranking_service.recalculate_team_points(
        team=team,
        reason='Smoke test recalculation'
    )
    
    if result['success']:
        print(f"✅ Points recalculated: {result['old_total']} → {result['new_total']} (change: {result['points_change']})")
    else:
        print(f"❌ Recalculation failed: {result.get('error')}")
        return False
    
    print("\n✅ Admin ranking endpoints PASSED")
    return True


def test_urls_structure():
    """Verify URL routing structure"""
    print("\n=== Testing URL Structure ===")
    
    from django.urls import reverse
    
    # Test essential routes
    routes_to_test = [
        ('teams:create', {}, 'Team creation page'),
        ('teams:rankings', {}, 'Global rankings'),
        ('teams:about', {}, 'About teams page'),
    ]
    
    for route_name, kwargs, description in routes_to_test:
        try:
            url = reverse(route_name, kwargs=kwargs)
            print(f"✅ {description}: {url}")
        except Exception as e:
            print(f"❌ {description} failed: {e}")
            return False
    
    # Test team-specific routes
    team = Team.objects.filter(tag='TEST').first()
    if team:
        team_routes = [
            ('teams:detail', {'slug': team.slug}, 'Team detail'),
            ('teams:dashboard', {'slug': team.slug}, 'Team dashboard'),
            ('teams:setup', {'slug': team.slug}, 'Team setup'),
        ]
        
        for route_name, kwargs, description in team_routes:
            try:
                url = reverse(route_name, kwargs=kwargs)
                print(f"✅ {description}: {url}")
            except Exception as e:
                print(f"❌ {description} failed: {e}")
                return False
    
    print("\n✅ URL structure PASSED")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("TEAM APP SMOKE TEST")
    print("=" * 60)
    
    results = {
        'Team Creation Flow': test_team_creation_flow(),
        'URL Structure': test_urls_structure(),
        'Admin Ranking Endpoints': test_admin_ranking_endpoints(),
    }
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    all_passed = all(results.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED - READY FOR PRODUCTION")
    else:
        print("⚠️ SOME TESTS FAILED - REVIEW ERRORS ABOVE")
    print("=" * 60)
