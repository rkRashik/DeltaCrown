"""
Management command to test query budget for team_detail_context
"""
from django.core.management.base import BaseCommand
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.contrib.auth import get_user_model

from apps.organizations.models import Team, TeamMembership
from apps.organizations.services.team_detail_context import get_team_detail_context

User = get_user_model()


class Command(BaseCommand):
    help = 'Test query budget for team detail context (P4-T1.4 Task C)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('P4-T1.4 TASK C: QUERY BUDGET VERIFICATION'))
        self.stdout.write(self.style.SUCCESS('='*80))
        self.stdout.write('Target: <=6 queries per request\n')
        
        # Find a team
        team = Team.objects.first()
        if not team:
            self.stdout.write(self.style.ERROR('âŒ No teams found in database'))
            return
        
        results = []
        
        # Test 1: Anonymous viewer
        self.stdout.write(self.style.WARNING('\nTEST 1: Anonymous Viewer'))
        self.stdout.write('-' * 80)
        with CaptureQueriesContext(connection) as ctx:
            context = get_team_detail_context(team_slug=team.slug, viewer=None)
        
        count = len(ctx.captured_queries)
        self.stdout.write(f'Team: {team.slug}')
        self.stdout.write(f'Query count: {count}')
        self._print_queries(ctx.captured_queries)
        
        if count <= 6:
            self.stdout.write(self.style.SUCCESS(f'PASS: {count} queries (within budget)'))
            results.append(('Anonymous', count, True))
        else:
            self.stdout.write(self.style.ERROR(f'FAIL: {count} queries (exceeds budget of 6)'))
            results.append(('Anonymous', count, False))
        
        # Test 2: Authenticated non-member
        self.stdout.write(self.style.WARNING('\nTEST 2: Authenticated Non-Member'))
        self.stdout.write('-' * 80)
        
        user, created = User.objects.get_or_create(
            username='test_non_member_qb',
            defaults={'email': 'test_non_member@test.com'}
        )
        if created:
            user.set_password('testpass123')
            user.save()
        
        # Ensure user is NOT a member (Legacy TeamMembership uses 'profile' FK)
        viewer_profile = getattr(user, 'userprofile', None) if hasattr(user, 'userprofile') else None
        if viewer_profile:
            TeamMembership.objects.filter(team=team, profile=viewer_profile).delete()
        
        try:
            with CaptureQueriesContext(connection) as ctx:
                context = get_team_detail_context(team_slug=team.slug, viewer=user)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            import traceback
            traceback.print_exc()
            return
        
        count = len(ctx.captured_queries)
        self.stdout.write(f'Team: {team.slug}')
        self.stdout.write(f'User: {user.username} (non-member)')
        self.stdout.write(f'Query count: {count}')
        self._print_queries(ctx.captured_queries)
        
        if count <= 6:
            self.stdout.write(self.style.SUCCESS(f'PASS: {count} queries (within budget)'))
            results.append(('Non-Member', count, True))
        else:
            self.stdout.write(self.style.ERROR(f'FAIL: {count} queries (exceeds budget of 6)'))
            results.append(('Non-Member', count, False))
        
        # Test 3: Authenticated member
        self.stdout.write(self.style.WARNING('\nTEST 3: Authenticated Team Member'))
        self.stdout.write('-' * 80)
        
        user2, created = User.objects.get_or_create(
            username='test_member_qb',
            defaults={'email': 'test_member@test.com'}
        )
        if created:
            user2.set_password('testpass123')
            user2.save()
        
        # Ensure user IS a member (Legacy TeamMembership uses 'profile' FK)
        viewer_profile2 = getattr(user2, 'userprofile', None) if hasattr(user2, 'userprofile') else None
        if viewer_profile2:
            membership, created = TeamMembership.objects.get_or_create(
                team=team,
                profile=viewer_profile2,
                defaults={'role': 'MEMBER', 'status': 'ACTIVE'}
            )
        
        with CaptureQueriesContext(connection) as ctx:
            context = get_team_detail_context(team_slug=team.slug, viewer=user2)
        
        count = len(ctx.captured_queries)
        self.stdout.write(f'Team: {team.slug}')
        self.stdout.write(f'User: {user2.username} (member)')
        self.stdout.write(f'Query count: {count}')
        self._print_queries(ctx.captured_queries)
        
        if count <= 6:
            self.stdout.write(self.style.SUCCESS(f'PASS: {count} queries (within budget)'))
            results.append(('Member', count, True))
        else:
            self.stdout.write(self.style.ERROR(f'FAIL: {count} queries (exceeds budget of 6)'))
            results.append(('Member', count, False))
        
        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('SUMMARY'))
        self.stdout.write(self.style.SUCCESS('='*80))
        
        all_passed = True
        for scenario, count, passed in results:
            status = 'PASS' if passed else 'FAIL'
            self.stdout.write(f'{scenario:20s}: {count} queries {status}')
            if not passed:
                all_passed = False
        
        self.stdout.write('\n' + '='*80)
        if all_passed:
            self.stdout.write(self.style.SUCCESS('ALL TESTS PASSED - Query budget <=6 for all scenarios'))
        else:
            self.stdout.write(self.style.ERROR('SOME TESTS FAILED - Optimization needed'))
        self.stdout.write('='*80 + '\n')
    
    def _print_queries(self, queries):
        """Print queries in readable format."""
        for i, query in enumerate(queries, 1):
            sql = query['sql']
            if 'teams_team' in sql and 'SELECT' in sql:
                self.stdout.write(f"  {i}. Team fetch (with select_related)")
            elif 'teams_teammembership' in sql:
                self.stdout.write(f"  {i}. TeamMembership query")
            elif 'teams_teamsponsor' in sql:
                self.stdout.write(f"  {i}. TeamSponsor query (partners)")
            elif 'teams_teaminvite' in sql:
                self.stdout.write(f"  {i}. TeamInvite query (pending_actions)")
            elif 'teams_teamjoinrequest' in sql:
                self.stdout.write(f"  {i}. TeamJoinRequest query (pending_actions)")
            elif 'organizations_organization' in sql:
                self.stdout.write(f"  {i}. Organization query")
            elif 'organizations_teamranking' in sql:
                self.stdout.write(f"  {i}. TeamRanking query")
            else:
                self.stdout.write(f"  {i}. {sql[:70]}...")
