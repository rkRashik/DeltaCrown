"""
Team Invites Endpoints Tests - Phase D

Comprehensive tests for team invite endpoints:
- List invites API
- Accept/decline membership invites
- Accept/decline email invites
- Permission enforcement
- Query budget validation

Run: pytest apps/organizations/tests/test_team_invites_endpoints.py -v
"""

import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from datetime import timedelta
from unittest.mock import patch

from apps.organizations.models import Team, TeamMembership, TeamInvite, Organization
from apps.organizations.choices import MembershipStatus
from apps.games.models import Game

User = get_user_model()


@pytest.mark.django_db
class TestListInvitesEndpoint:
    """Test GET /api/vnext/teams/invites/ endpoint."""
    
    @pytest.fixture
    def setup_data(self):
        """Create test data."""
        # Users
        user1 = User.objects.create_user(username='user1', email='user1@test.com')
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        user3 = User.objects.create_user(username='user3', email='user3@test.com')
        
        # Game
        game = Game.objects.create(
            slug='valorant',
            name='Valorant',
            display_name='VALORANT',
            is_active=True
        )
        
        # Teams
        team1 = Team.objects.create(
            name='Team Alpha',
            slug='team-alpha',
            game_id=game,
            owner=user1
        )
        team2 = Team.objects.create(
            name='Team Beta',
            slug='team-beta',
            game_id=game,
            owner=user2
        )
        
        return {
            'user1': user1,
            'user2': user2,
            'user3': user3,
            'game': game,
            'team1': team1,
            'team2': team2,
        }
    
    def test_list_invites_empty(self, setup_data):
        """User with no invites returns empty lists."""
        client = APIClient()
        client.force_authenticate(user=setup_data['user1'])
        
        response = client.get('/api/vnext/teams/invites/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['data']['membership_invites'] == []
        assert data['data']['email_invites'] == []
        assert data['data']['total_count'] == 0
    
    def test_list_invites_membership_only(self, setup_data):
        """Returns only membership invites."""
        # Create membership invite
        membership = TeamMembership.objects.create(
            team=setup_data['team1'],
            user=setup_data['user2'],
            role='MANAGER',
            status=MembershipStatus.INVITED
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.get('/api/vnext/teams/invites/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['data']['membership_invites']) == 1
        assert data['data']['email_invites'] == []
        assert data['data']['total_count'] == 1
        
        # Check structure
        invite = data['data']['membership_invites'][0]
        assert invite['id'] == membership.id
        assert invite['team_name'] == 'Team Alpha'
        assert invite['team_slug'] == 'team-alpha'
        assert invite['game_name'] == 'Valorant'
        assert invite['role'] == 'MANAGER'
        assert invite['inviter_name'] == 'user1'
        assert 'created_at' in invite
        assert invite['status'] == MembershipStatus.INVITED
    
    def test_list_invites_email_only(self, setup_data):
        """Returns only email invites."""
        # Create email invite
        invite = TeamInvite.objects.create(
            team=setup_data['team1'],
            invited_email='user3@test.com',
            inviter=setup_data['user1'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user3'])
        
        response = client.get('/api/vnext/teams/invites/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['data']['membership_invites'] == []
        assert len(data['data']['email_invites']) == 1
        assert data['data']['total_count'] == 1
        
        # Check structure
        email_inv = data['data']['email_invites'][0]
        assert email_inv['token'] == str(invite.token)
        assert email_inv['team_name'] == 'Team Alpha'
        assert email_inv['team_slug'] == 'team-alpha'
        assert email_inv['game_name'] == 'Valorant'
        assert email_inv['role'] == 'PLAYER'
        assert email_inv['invited_email'] == 'user3@test.com'
        assert email_inv['inviter_name'] == 'user1'
        assert 'created_at' in email_inv
        assert 'expires_at' in email_inv
        assert email_inv['status'] == 'PENDING'
    
    def test_list_invites_mixed(self, setup_data):
        """Returns both membership and email invites."""
        # Create both types
        membership = TeamMembership.objects.create(
            team=setup_data['team1'],
            user=setup_data['user3'],
            role='MANAGER',
            status=MembershipStatus.INVITED
        )
        email_invite = TeamInvite.objects.create(
            team=setup_data['team2'],
            invited_email='user3@test.com',
            inviter=setup_data['user2'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user3'])
        
        response = client.get('/api/vnext/teams/invites/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['data']['membership_invites']) == 1
        assert len(data['data']['email_invites']) == 1
        assert data['data']['total_count'] == 2
    
    def test_list_invites_filters_expired(self, setup_data):
        """Expired email invites are automatically filtered out."""
        # Create expired invite
        expired_invite = TeamInvite.objects.create(
            team=setup_data['team1'],
            invited_email='user3@test.com',
            inviter=setup_data['user1'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() - timedelta(days=1)  # Expired
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user3'])
        
        response = client.get('/api/vnext/teams/invites/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['data']['email_invites'] == []  # Expired filtered out
        assert data['data']['total_count'] == 0
        
        # Verify invite was marked expired
        expired_invite.refresh_from_db()
        assert expired_invite.status == 'EXPIRED'
    
    def test_list_invites_unauthenticated(self):
        """Unauthenticated requests are rejected."""
        client = APIClient()
        response = client.get('/api/vnext/teams/invites/')
        assert response.status_code == 401


@pytest.mark.django_db
class TestAcceptMembershipInvite:
    """Test POST /api/vnext/teams/invites/membership/<id>/accept/"""
    
    @pytest.fixture
    def setup_data(self):
        """Create test data."""
        user1 = User.objects.create_user(username='user1', email='user1@test.com')
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        game = Game.objects.create(slug='valorant', name='Valorant', is_active=True)
        team = Team.objects.create(name='Team Alpha', slug='team-alpha', game_id=game, owner=user1)
        
        return {'user1': user1, 'user2': user2, 'team': team}
    
    def test_accept_success(self, setup_data):
        """Successfully accept membership invite."""
        # Create invite
        membership = TeamMembership.objects.create(
            team=setup_data['team'],
            user=setup_data['user2'],
            role='MANAGER',
            status=MembershipStatus.INVITED
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post(f'/api/vnext/teams/invites/membership/{membership.id}/accept/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['data']['team_slug'] == 'team-alpha'
        assert data['data']['role'] == 'MANAGER'
        assert 'team_url' in data['data']
        
        # Verify membership status changed
        membership.refresh_from_db()
        assert membership.status == MembershipStatus.ACTIVE
    
    def test_accept_forbidden_wrong_user(self, setup_data):
        """Cannot accept someone else's invite."""
        user3 = User.objects.create_user(username='user3', email='user3@test.com')
        
        membership = TeamMembership.objects.create(
            team=setup_data['team'],
            user=setup_data['user2'],
            role='MANAGER',
            status=MembershipStatus.INVITED
        )
        
        client = APIClient()
        client.force_authenticate(user=user3)  # Wrong user!
        
        response = client.post(f'/api/vnext/teams/invites/membership/{membership.id}/accept/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['ok'] is False
        assert data['error_code'] == 'INVITE_FORBIDDEN'
        
        # Verify membership unchanged
        membership.refresh_from_db()
        assert membership.status == MembershipStatus.INVITED
    
    def test_accept_already_accepted(self, setup_data):
        """Accepting already-accepted invite returns error."""
        membership = TeamMembership.objects.create(
            team=setup_data['team'],
            user=setup_data['user2'],
            role='MANAGER',
            status=MembershipStatus.ACTIVE  # Already active
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post(f'/api/vnext/teams/invites/membership/{membership.id}/accept/')
        
        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        assert data['error_code'] == 'INVITE_ALREADY_ACCEPTED'
    
    def test_accept_not_found(self, setup_data):
        """Non-existent membership returns 404."""
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post('/api/vnext/teams/invites/membership/99999/accept/')
        
        assert response.status_code == 404
        data = response.json()
        assert data['ok'] is False
        assert data['error_code'] == 'INVITE_NOT_FOUND'


@pytest.mark.django_db
class TestDeclineMembershipInvite:
    """Test POST /api/vnext/teams/invites/membership/<id>/decline/"""
    
    @pytest.fixture
    def setup_data(self):
        user1 = User.objects.create_user(username='user1', email='user1@test.com')
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        game = Game.objects.create(slug='valorant', name='Valorant', is_active=True)
        team = Team.objects.create(name='Team Alpha', slug='team-alpha', game_id=game, owner=user1)
        return {'user1': user1, 'user2': user2, 'team': team}
    
    def test_decline_success(self, setup_data):
        """Successfully decline membership invite."""
        membership = TeamMembership.objects.create(
            team=setup_data['team'],
            user=setup_data['user2'],
            role='MANAGER',
            status=MembershipStatus.INVITED
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post(f'/api/vnext/teams/invites/membership/{membership.id}/decline/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        
        # Verify status changed to DECLINED
        membership.refresh_from_db()
        assert membership.status == 'DECLINED'
    
    def test_decline_forbidden_wrong_user(self, setup_data):
        """Cannot decline someone else's invite."""
        user3 = User.objects.create_user(username='user3', email='user3@test.com')
        
        membership = TeamMembership.objects.create(
            team=setup_data['team'],
            user=setup_data['user2'],
            role='MANAGER',
            status=MembershipStatus.INVITED
        )
        
        client = APIClient()
        client.force_authenticate(user=user3)
        
        response = client.post(f'/api/vnext/teams/invites/membership/{membership.id}/decline/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INVITE_FORBIDDEN'


@pytest.mark.django_db
class TestAcceptEmailInvite:
    """Test POST /api/vnext/teams/invites/email/<token>/accept/"""
    
    @pytest.fixture
    def setup_data(self):
        user1 = User.objects.create_user(username='user1', email='user1@test.com')
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        game = Game.objects.create(slug='valorant', name='Valorant', is_active=True)
        team = Team.objects.create(name='Team Alpha', slug='team-alpha', game_id=game, owner=user1)
        return {'user1': user1, 'user2': user2, 'team': team}
    
    def test_accept_email_success(self, setup_data):
        """Successfully accept email invite."""
        invite = TeamInvite.objects.create(
            team=setup_data['team'],
            invited_email='user2@test.com',
            inviter=setup_data['user1'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post(f'/api/vnext/teams/invites/email/{invite.token}/accept/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['data']['team_slug'] == 'team-alpha'
        assert data['data']['role'] == 'PLAYER'
        
        # Verify invite marked accepted
        invite.refresh_from_db()
        assert invite.status == 'ACCEPTED'
        
        # Verify membership created
        membership = TeamMembership.objects.get(team=setup_data['team'], user=setup_data['user2'])
        assert membership.status == MembershipStatus.ACTIVE
        assert membership.role == 'PLAYER'
    
    def test_accept_email_expired(self, setup_data):
        """Cannot accept expired email invite."""
        invite = TeamInvite.objects.create(
            team=setup_data['team'],
            invited_email='user2@test.com',
            inviter=setup_data['user1'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() - timedelta(days=1)  # Expired
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post(f'/api/vnext/teams/invites/email/{invite.token}/accept/')
        
        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False
        assert data['error_code'] == 'INVITE_EXPIRED'
    
    def test_accept_email_wrong_email(self, setup_data):
        """Cannot accept invite with email mismatch."""
        user3 = User.objects.create_user(username='user3', email='user3@test.com')
        
        invite = TeamInvite.objects.create(
            team=setup_data['team'],
            invited_email='user2@test.com',  # Invited user2
            inviter=setup_data['user1'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        client = APIClient()
        client.force_authenticate(user=user3)  # user3 trying to accept
        
        response = client.post(f'/api/vnext/teams/invites/email/{invite.token}/accept/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INVITE_FORBIDDEN'
    
    def test_accept_email_invalid_token(self, setup_data):
        """Invalid token returns 404."""
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post('/api/vnext/teams/invites/email/00000000-0000-0000-0000-000000000000/accept/')
        
        assert response.status_code == 404
        data = response.json()
        assert data['error_code'] == 'INVITE_NOT_FOUND'


@pytest.mark.django_db
class TestDeclineEmailInvite:
    """Test POST /api/vnext/teams/invites/email/<token>/decline/"""
    
    @pytest.fixture
    def setup_data(self):
        user1 = User.objects.create_user(username='user1', email='user1@test.com')
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        game = Game.objects.create_user(slug='valorant', name='Valorant', is_active=True)
        team = Team.objects.create(name='Team Alpha', slug='team-alpha', game_id=game, owner=user1)
        return {'user1': user1, 'user2': user2, 'team': team}
    
    def test_decline_email_success(self, setup_data):
        """Successfully decline email invite."""
        invite = TeamInvite.objects.create(
            team=setup_data['team'],
            invited_email='user2@test.com',
            inviter=setup_data['user1'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        response = client.post(f'/api/vnext/teams/invites/email/{invite.token}/decline/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        
        # Verify status changed
        invite.refresh_from_db()
        assert invite.status == 'DECLINED'
    
    def test_decline_email_wrong_user(self, setup_data):
        """Cannot decline invite with email mismatch."""
        user3 = User.objects.create_user(username='user3', email='user3@test.com')
        
        invite = TeamInvite.objects.create(
            team=setup_data['team'],
            invited_email='user2@test.com',
            inviter=setup_data['user1'],
            role='PLAYER',
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        client = APIClient()
        client.force_authenticate(user=user3)
        
        response = client.post(f'/api/vnext/teams/invites/email/{invite.token}/decline/')
        
        assert response.status_code == 403
        data = response.json()
        assert data['error_code'] == 'INVITE_FORBIDDEN'


@pytest.mark.django_db
class TestQueryBudget:
    """Test query count for list_invites endpoint."""
    
    @pytest.fixture
    def setup_data(self):
        user1 = User.objects.create_user(username='user1', email='user1@test.com')
        user2 = User.objects.create_user(username='user2', email='user2@test.com')
        game = Game.objects.create(slug='valorant', name='Valorant', is_active=True)
        
        # Create multiple teams
        teams = []
        for i in range(5):
            team = Team.objects.create(
                name=f'Team {i}',
                slug=f'team-{i}',
                game_id=game,
                owner=user1
            )
            teams.append(team)
        
        # Create multiple invites for user2
        for team in teams:
            # Membership invite
            TeamMembership.objects.create(
                team=team,
                user=user2,
                role='PLAYER',
                status=MembershipStatus.INVITED
            )
            
            # Email invite
            TeamInvite.objects.create(
                team=team,
                invited_email='user2@test.com',
                inviter=user1,
                role='PLAYER',
                status='PENDING',
                expires_at=timezone.now() + timedelta(days=7)
            )
        
        return {'user1': user1, 'user2': user2, 'teams': teams}
    
    def test_query_budget_list_invites(self, setup_data, django_assert_num_queries):
        """List invites runs in ≤6 queries regardless of invite count."""
        client = APIClient()
        client.force_authenticate(user=setup_data['user2'])
        
        # Expected queries:
        # 1. Get user
        # 2. Get membership invites (with select_related)
        # 3. Get email invites (with select_related)
        # 4. Get teams with games for lookup
        # Total: ~4 queries
        
        with django_assert_num_queries(6):  # Budget is ≤6
            response = client.get('/api/vnext/teams/invites/')
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['data']['membership_invites']) == 5
        assert len(data['data']['email_invites']) == 5
