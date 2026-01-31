"""
Manual Query Budget Verification for P4-T1.4 Task C

Tests query count for team_detail_context.get_team_detail_context()
in three scenarios: anonymous, authenticated non-member, authenticated member.

Target: ≤6 queries per request
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.contrib.auth import get_user_model

from apps.organizations.services.team_detail_context import get_team_detail_context
from apps.teams.models import Team, TeamMembership
from apps.organizations.models import Organization

User = get_user_model()

def print_queries(queries):
    """Print queries in readable format."""
    for i, query in enumerate(queries, 1):
        sql = query['sql']
        if 'teams_team' in sql and 'SELECT' in sql:
            print(f"{i}. Team fetch (with select_related)")
        elif 'teams_teammembership' in sql:
            print(f"{i}. TeamMembership query")
        elif 'teams_teamsponsor' in sql:
            print(f"{i}. TeamSponsor query (partners)")
        elif 'teams_teaminvite' in sql:
            print(f"{i}. TeamInvite query (pending_actions)")
        elif 'teams_teamjoinrequest' in sql:
            print(f"{i}. TeamJoinRequest query (pending_actions)")
        elif 'organizations_organization' in sql:
            print(f"{i}. Organization query")
        elif 'organizations_teamranking' in sql:
            print(f"{i}. TeamRanking query")
        else:
            print(f"{i}. {sql[:100]}...")


def test_anonymous_viewer():
    """Test query count for anonymous viewer."""
    print("\n" + "=" * 80)
    print("TEST 1: Anonymous Viewer")
    print("=" * 80)
    
    # Find a team to test with
    team = Team.objects.first()
    if not team:
        print("❌ No teams found in database")
        return
    
    print(f"Testing with team: {team.slug}")
    
    with CaptureQueriesContext(connection) as ctx:
        context = get_team_detail_context(team_slug=team.slug, viewer=None)
    
    query_count = len(ctx.queries)
    print(f"\n📊 Query Count: {query_count}")
    print_queries(ctx.queries)
    
    if query_count <= 6:
        print(f"\n✅ PASS: {query_count} queries (within budget of 6)")
    else:
        print(f"\n⚠️ FAIL: {query_count} queries (exceeds budget of 6)")
    
    return query_count


def test_authenticated_non_member():
    """Test query count for authenticated non-member."""
    print("\n" + "=" * 80)
    print("TEST 2: Authenticated Non-Member")
    print("=" * 80)
    
    # Find a team and a user who is not a member
    team = Team.objects.first()
    if not team:
        print("❌ No teams found in database")
        return
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_non_member_qb',
        defaults={'email': 'test_non_member@test.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Ensure user is NOT a member of this team
    TeamMembership.objects.filter(team=team, user=user).delete()
    
    print(f"Testing with team: {team.slug}, user: {user.username}")
    
    with CaptureQueriesContext(connection) as ctx:
        context = get_team_detail_context(team_slug=team.slug, viewer=user)
    
    query_count = len(ctx.queries)
    print(f"\n📊 Query Count: {query_count}")
    print_queries(ctx.queries)
    
    if query_count <= 6:
        print(f"\n✅ PASS: {query_count} queries (within budget of 6)")
    else:
        print(f"\n⚠️ FAIL: {query_count} queries (exceeds budget of 6)")
    
    return query_count


def test_authenticated_member():
    """Test query count for authenticated team member."""
    print("\n" + "=" * 80)
    print("TEST 3: Authenticated Team Member")
    print("=" * 80)
    
    # Find a team
    team = Team.objects.first()
    if not team:
        print("❌ No teams found in database")
        return
    
    # Get or create a test user and make them a member
    user, created = User.objects.get_or_create(
        username='test_member_qb',
        defaults={'email': 'test_member@test.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    
    # Ensure user IS a member of this team
    membership, created = TeamMembership.objects.get_or_create(
        team=team,
        user=user,
        defaults={'role': 'MEMBER', 'status': 'ACTIVE'}
    )
    
    print(f"Testing with team: {team.slug}, user: {user.username}")
    
    with CaptureQueriesContext(connection) as ctx:
        context = get_team_detail_context(team_slug=team.slug, viewer=user)
    
    query_count = len(ctx.queries)
    print(f"\n📊 Query Count: {query_count}")
    print_queries(ctx.queries)
    
    if query_count <= 6:
        print(f"\n✅ PASS: {query_count} queries (within budget of 6)")
    else:
        print(f"\n⚠️ FAIL: {query_count} queries (exceeds budget of 6)")
    
    return query_count


if __name__ == '__main__':
    print("\n" + "🔍 P4-T1.4 TASK C: QUERY BUDGET VERIFICATION " + "\n")
    print("Target: ≤6 queries per request")
    print("Scenarios: Anonymous, Authenticated Non-Member, Authenticated Member")
    
    results = []
    
    try:
        results.append(('Anonymous', test_anonymous_viewer()))
        results.append(('Non-Member', test_authenticated_non_member()))
        results.append(('Member', test_authenticated_member()))
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    all_passed = True
    for scenario, count in results:
        status = "✅ PASS" if count <= 6 else "⚠️ FAIL"
        print(f"{scenario:20s}: {count} queries {status}")
        if count > 6:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("✅ ALL TESTS PASSED - Query budget ≤6 for all scenarios")
    else:
        print("⚠️ SOME TESTS FAILED - Optimization needed")
    print("=" * 80)
