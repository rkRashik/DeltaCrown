"""Quick query count test for anonymous viewer"""
from django.test.utils import CaptureQueriesContext
from django.db import connection
from apps.teams.models import Team
from apps.organizations.services.team_detail_context import get_team_detail_context

team = Team.objects.first()
if not team:
    print("No teams found")
else:
    print(f"Testing team: {team.slug}")
    
    with CaptureQueriesContext(connection) as ctx:
        context = get_team_detail_context(team_slug=team.slug, viewer=None)
    
    print(f"\nQuery count (anonymous): {len(ctx.queries)}")
    print("\nQueries:")
    for i, q in enumerate(ctx.queries, 1):
        sql = q['sql']
        if 'teams_team' in sql and 'SELECT' in sql:
            print(f"{i}. Team fetch")
        elif 'teammembership' in sql:
            print(f"{i}. TeamMembership")
        elif 'teamsponsor' in sql:
            print(f"{i}. TeamSponsor")
        elif 'teaminvite' in sql:
            print(f"{i}. TeamInvite")
        elif 'teamjoinrequest' in sql:
            print(f"{i}. TeamJoinRequest")
        else:
            print(f"{i}. {sql[:70]}...")
    
    if len(ctx.queries) <= 6:
        print(f"\n✅ PASS: {len(ctx.queries)} queries (within budget)")
    else:
        print(f"\n⚠️ FAIL: {len(ctx.queries)} queries (exceeds budget of 6)")
