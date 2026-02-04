"""
Test: Team HQ Management Console (Phase 16)

Tests for templates/teams/manage_hq.html and partials.
Ensures rendering, permission enforcement, and no owner field regressions.
"""

import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

from apps.teams.models._legacy import Team, TeamMembership

User = get_user_model()


@pytest.mark.django_db
class TestManageHQRendering:
    """Test: manage_hq.html renders correctly for authorized users."""
    
    def test_manage_hq_renders_for_owner(self, client: Client, django_user_model):
        """Test: Team owner can access manage HQ page (200 OK)."""
        # Setup: Create owner
        owner_user = django_user_model.objects.create_user(
            username='owner',
            password='pass123',
            email='owner@test.com'
        )
        owner_profile = owner_user.userprofile
        
        # Create team with owner membership
        team = Team.objects.create(
            name='Test Squad',
            tag='TST',
            game_id=1,
            region='NA'
        )
        TeamMembership.objects.create(
            team=team,
            profile=owner_profile,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Act: Request manage HQ page
        client.force_login(owner_user)
        response = client.get(reverse('teams:manage', args=[team.slug]))
        
        # Assert: 200 OK, correct template used
        assert response.status_code == 200
        assert 'teams/manage_hq.html' in [t.name for t in response.templates]
        
        # Assert: Context has expected variables
        assert 'team' in response.context
        assert 'user_membership' in response.context
        assert 'members' in response.context
        assert 'can_manage_roster' in response.context
        assert 'is_owner' in response.context
        
        # Assert: Owner flags set correctly
        assert response.context['is_owner'] is True
        assert response.context['can_manage_roster'] is True
    
    def test_manage_hq_renders_for_manager(self, client: Client, django_user_model):
        """Test: Team manager can access manage HQ page (200 OK)."""
        # Setup: Create owner and manager
        owner_user = django_user_model.objects.create_user(
            username='owner',
            password='pass123',
            email='owner@test.com'
        )
        manager_user = django_user_model.objects.create_user(
            username='manager',
            password='pass123',
            email='manager@test.com'
        )
        owner_profile = owner_user.userprofile
        manager_profile = manager_user.userprofile
        
        # Create team
        team = Team.objects.create(
            name='Test Squad',
            tag='TST',
            game_id=1,
            region='NA'
        )
        TeamMembership.objects.create(
            team=team,
            profile=owner_profile,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        )
        TeamMembership.objects.create(
            team=team,
            profile=manager_profile,
            role=TeamMembership.Role.MANAGER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Act: Request manage HQ page as manager
        client.force_login(manager_user)
        response = client.get(reverse('teams:manage', args=[team.slug]))
        
        # Assert: 200 OK, manager can see page
        assert response.status_code == 200
        assert response.context['is_owner'] is False
        assert response.context['can_manage_roster'] is True  # Managers can manage roster


@pytest.mark.django_db
class TestManageHQPermissions:
    """Test: manage_hq.html enforces permission rules."""
    
    def test_manage_hq_forbidden_for_non_manager(self, client: Client, django_user_model):
        """Test: Regular members cannot access manage HQ (403 or redirect)."""
        # Setup: Create owner and regular member
        owner_user = django_user_model.objects.create_user(
            username='owner',
            password='pass123',
            email='owner@test.com'
        )
        member_user = django_user_model.objects.create_user(
            username='member',
            password='pass123',
            email='member@test.com'
        )
        owner_profile = owner_user.userprofile
        member_profile = member_user.userprofile
        
        # Create team
        team = Team.objects.create(
            name='Test Squad',
            tag='TST',
            game_id=1,
            region='NA'
        )
        TeamMembership.objects.create(
            team=team,
            profile=owner_profile,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        )
        TeamMembership.objects.create(
            team=team,
            profile=member_profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Act: Request manage HQ page as regular member
        client.force_login(member_user)
        response = client.get(reverse('teams:manage', args=[team.slug]))
        
        # Assert: 403 Forbidden or redirect (not 200)
        assert response.status_code in [403, 302], \
            "Regular members should not access manage HQ"
    
    def test_manage_hq_forbidden_for_non_member(self, client: Client, django_user_model):
        """Test: Non-members cannot access manage HQ (403 or redirect)."""
        # Setup: Create owner and outsider
        owner_user = django_user_model.objects.create_user(
            username='owner',
            password='pass123',
            email='owner@test.com'
        )
        outsider_user = django_user_model.objects.create_user(
            username='outsider',
            password='pass123',
            email='outsider@test.com'
        )
        owner_profile = owner_user.userprofile
        
        # Create team (no membership for outsider)
        team = Team.objects.create(
            name='Test Squad',
            tag='TST',
            game_id=1,
            region='NA'
        )
        TeamMembership.objects.create(
            team=team,
            profile=owner_profile,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Act: Request manage HQ page as outsider
        client.force_login(outsider_user)
        response = client.get(reverse('teams:manage', args=[team.slug]))
        
        # Assert: 403 Forbidden or redirect
        assert response.status_code in [403, 302], \
            "Non-members should not access manage HQ"


@pytest.mark.django_db
class TestManageHQDataWiring:
    """Test: manage_hq.html uses correct context variables."""
    
    def test_roster_list_displays_members(self, client: Client, django_user_model):
        """Test: Roster section shows all active members."""
        # Setup: Create team with 3 members
        owner_user = django_user_model.objects.create_user(
            username='owner',
            password='pass123',
            email='owner@test.com'
        )
        member1_user = django_user_model.objects.create_user(
            username='player1',
            password='pass123',
            email='p1@test.com'
        )
        member2_user = django_user_model.objects.create_user(
            username='player2',
            password='pass123',
            email='p2@test.com'
        )
        owner_profile = owner_user.userprofile
        member1_profile = member1_user.userprofile
        member2_profile = member2_user.userprofile
        
        team = Team.objects.create(
            name='Test Squad',
            tag='TST',
            game_id=1,
            region='NA'
        )
        TeamMembership.objects.create(
            team=team,
            profile=owner_profile,
            role=TeamMembership.Role.OWNER,
            status=TeamMembership.Status.ACTIVE
        )
        TeamMembership.objects.create(
            team=team,
            profile=member1_profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        TeamMembership.objects.create(
            team=team,
            profile=member2_profile,
            role=TeamMembership.Role.PLAYER,
            status=TeamMembership.Status.ACTIVE
        )
        
        # Act: Request page
        client.force_login(owner_user)
        response = client.get(reverse('teams:manage', args=[team.slug]))
        
        # Assert: members queryset in context
        assert response.status_code == 200
        assert 'members' in response.context
        assert response.context['members'].count() == 3
        
        # Assert: HTML contains member usernames
        content = response.content.decode('utf-8')
        assert 'owner' in content
        assert 'player1' in content
        assert 'player2' in content


@pytest.mark.regression
class TestManageHQOwnerFieldRegression:
    """Regression test: Ensure no team.owner field usage (Phase 16)."""
    
    def test_owner_field_not_reintroduced_in_templates(self):
        """Test: manage_hq partials don't reference team.owner."""
        import re
        from pathlib import Path
        
        # Check: All manage_hq partials
        partials_dir = Path('g:/My Projects/WORK/DeltaCrown/templates/teams/manage_hq/partials')
        
        if not partials_dir.exists():
            pytest.skip(f"Partials directory not found: {partials_dir}")
        
        # Pattern: team.owner (not TeamMembership.Role.OWNER)
        forbidden_pattern = r'\{\{\s*team\.owner\s*\}\}|\{\%\s*if\s+team\.owner\s*\%\}'
        
        violations = []
        for partial_file in partials_dir.glob('*.html'):
            with open(partial_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            matches = re.findall(forbidden_pattern, content)
            if matches:
                violations.append(f"{partial_file.name}: {matches}")
        
        if violations:
            pytest.fail(
                "Found team.owner references in manage_hq partials:\n" +
                "\n".join(violations) +
                "\n\nShould use: user_membership.role check or is_owner context variable"
            )
    
    def test_owner_field_not_in_manage_view(self):
        """Test: apps/teams/views/public.py doesn't use team.owner in manage view."""
        import re
        from pathlib import Path
        
        view_file = Path('g:/My Projects/WORK/DeltaCrown/apps/teams/views/public.py')
        
        if not view_file.exists():
            pytest.skip(f"View file not found: {view_file}")
        
        with open(view_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern: team.owner (not .Role.OWNER)
        forbidden_pattern = r'team\.owner(?!\w)'
        
        matches = list(re.finditer(forbidden_pattern, content))
        if matches:
            line_nums = [content[:m.start()].count('\n') + 1 for m in matches]
            pytest.fail(
                f"Found team.owner references in public.py at lines: {line_nums}\n"
                "Should use: team.created_by or membership.role checks"
            )
