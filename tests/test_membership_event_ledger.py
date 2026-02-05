"""
Tests for Append-Only Membership Event Ledger

Purpose: Verify event creation for all membership lifecycle events and query capabilities.
"""

import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.organizations.models import TeamMembership, TeamMembershipEvent
from apps.organizations.choices import MembershipRole, MembershipStatus, MembershipEventType
from tests.factories import create_independent_team

User = get_user_model()


@pytest.mark.django_db
class TestMembershipEventLedger:
    """Test append-only event ledger for all membership operations"""
    
    def test_joined_event_created_on_add_member(self, client):
        """Verify JOINED event created when user added to team"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        new_member = User.objects.create_user(username='player1', password='pass')
        
        client.login(username='creator', password='pass')
        
        # Initial event count (creator join)
        initial_count = TeamMembershipEvent.objects.filter(user=creator).count()
        
        # Add member
        url = reverse('organizations_api:team_manage_add_member', kwargs={'slug': 'delta'})
        response = client.post(url, {
            'user_id': new_member.id,
            'role': MembershipRole.PLAYER,
        }, content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify JOINED event created
        events = TeamMembershipEvent.objects.filter(user=new_member, team=team)
        assert events.count() == 1
        
        event = events.first()
        assert event.event_type == MembershipEventType.JOINED
        assert event.new_role == MembershipRole.PLAYER
        assert event.new_status == MembershipStatus.ACTIVE
        assert event.actor == creator
        assert event.membership is not None
    
    def test_role_changed_event_created_on_change_role(self, client):
        """Verify ROLE_CHANGED event with old/new role recorded"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        member_user = User.objects.create_user(username='player1', password='pass')
        
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        # Create JOINED event first
        TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=member_user,
            actor=creator,
            event_type=MembershipEventType.JOINED,
            new_role=MembershipRole.PLAYER,
            new_status=MembershipStatus.ACTIVE,
        )
        
        client.login(username='creator', password='pass')
        
        # Change role
        url = reverse('organizations_api:team_manage_change_role', kwargs={'slug': 'delta', 'membership_id': membership.id})
        response = client.post(url, {
            'role': MembershipRole.COACH,
        }, content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify ROLE_CHANGED event created
        events = TeamMembershipEvent.objects.filter(membership=membership, event_type=MembershipEventType.ROLE_CHANGED)
        assert events.count() == 1
        
        event = events.first()
        assert event.old_role == MembershipRole.PLAYER
        assert event.new_role == MembershipRole.COACH
        assert event.actor == creator
    
    def test_removed_event_created_on_remove_member(self, client):
        """Verify REMOVED event with status change and left_at timestamp"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        member_user = User.objects.create_user(username='player1', password='pass')
        
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        # Create JOINED event first
        TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=member_user,
            actor=creator,
            event_type=MembershipEventType.JOINED,
            new_role=MembershipRole.PLAYER,
            new_status=MembershipStatus.ACTIVE,
        )
        
        client.login(username='creator', password='pass')
        
        # Remove member
        url = reverse('organizations_api:team_manage_remove_member', kwargs={'slug': 'delta', 'membership_id': membership.id})
        response = client.post(url, content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify REMOVED event created
        events = TeamMembershipEvent.objects.filter(membership=membership, event_type=MembershipEventType.REMOVED)
        assert events.count() == 1
        
        event = events.first()
        assert event.old_status == MembershipStatus.ACTIVE
        assert event.new_status == MembershipStatus.INACTIVE
        assert event.metadata.get('reason') == 'removed_by_manager'
        
        # Verify membership status changed and left_at set
        membership.refresh_from_db()
        assert membership.status == MembershipStatus.INACTIVE
        assert membership.left_at is not None
    
    def test_left_event_created_on_self_removal(self, client):
        """Verify LEFT event when user removes themselves"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        member_user = User.objects.create_user(username='player1', password='pass')
        
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        # Create JOINED event first
        TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=member_user,
            actor=creator,
            event_type=MembershipEventType.JOINED,
            new_role=MembershipRole.PLAYER,
            new_status=MembershipStatus.ACTIVE,
        )
        
        client.login(username='player1', password='pass')
        
        # Remove self
        url = reverse('organizations_api:team_manage_remove_member', kwargs={'slug': 'delta', 'membership_id': membership.id})
        response = client.post(url, content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify LEFT event created
        events = TeamMembershipEvent.objects.filter(membership=membership)
        removal_event = events.filter(event_type=MembershipEventType.LEFT).first()
        
        assert removal_event is not None
        assert removal_event.metadata.get('reason') == 'self_removal'
        assert removal_event.actor == member_user
    
    def test_status_changed_event_created_on_moderation(self, client):
        """Verify STATUS_CHANGED event with metadata on moderation action"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass', is_staff=True)
        team = create_independent_team(creator, 'Delta', 'delta')
        member_user = User.objects.create_user(username='player1', password='pass')
        
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        client.login(username='creator', password='pass')
        
        # Suspend member
        url = reverse('organizations_api:team_manage_change_status', kwargs={'slug': 'delta', 'membership_id': membership.id})
        response = client.post(url, {
            'status': MembershipStatus.SUSPENDED,
            'reason': 'Toxic behavior in match',
            'duration_days': 7,
        }, content_type='application/json')
        
        assert response.status_code == 200
        
        # Verify STATUS_CHANGED event created
        events = TeamMembershipEvent.objects.filter(membership=membership, event_type=MembershipEventType.STATUS_CHANGED)
        assert events.count() == 1
        
        event = events.first()
        assert event.old_status == MembershipStatus.ACTIVE
        assert event.new_status == MembershipStatus.SUSPENDED
        assert event.metadata['reason'] == 'Toxic behavior in match'
        assert event.metadata['duration_days'] == 7
        assert event.actor == creator
    
    def test_user_team_history_endpoint_returns_ordered_timeline(self, client):
        """Verify user team history endpoint returns complete event timeline"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        player = User.objects.create_user(username='player1', password='pass')
        
        # Create membership
        membership = TeamMembership.objects.create(
            team=team,
            user=player,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        # Create event timeline
        joined_event = TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=player,
            actor=creator,
            event_type=MembershipEventType.JOINED,
            new_role=MembershipRole.PLAYER,
            new_status=MembershipStatus.ACTIVE,
        )
        
        role_change_event = TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=player,
            actor=creator,
            event_type=MembershipEventType.ROLE_CHANGED,
            old_role=MembershipRole.PLAYER,
            new_role=MembershipRole.COACH,
        )
        
        # Login as player (can view own history)
        client.login(username='player1', password='pass')
        
        # Get team history
        url = reverse('organizations_api:user_team_history', kwargs={'user_id': player.id})
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['user_id'] == player.id
        assert data['username'] == 'player1'
        assert len(data['history']) == 1
        
        team_history = data['history'][0]
        assert team_history['team_slug'] == 'delta'
        assert team_history['current_role'] == MembershipRole.COACH  # After role change
        assert len(team_history['events']) == 2
        assert team_history['events'][0]['type'] == MembershipEventType.JOINED
        assert team_history['events'][1]['type'] == MembershipEventType.ROLE_CHANGED
        
        # Verify role timeline
        assert len(team_history['role_timeline']) == 2
        assert team_history['role_timeline'][0]['role'] == MembershipRole.PLAYER
        assert team_history['role_timeline'][1]['role'] == MembershipRole.COACH
    
    def test_user_team_history_permission_denied_for_other_users(self, client):
        """Verify users cannot view other users' history (unless staff)"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        player = User.objects.create_user(username='player1', password='pass')
        other_user = User.objects.create_user(username='other', password='pass')
        
        # Login as other_user (not staff, not player)
        client.login(username='other', password='pass')
        
        # Try to get player's history
        url = reverse('organizations_api:user_team_history', kwargs={'user_id': player.id})
        response = client.get(url)
        
        assert response.status_code == 403
    
    def test_append_only_enforcement_raises_error_on_update(self):
        """Verify append-only enforcement prevents event updates"""
        # Setup
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        player = User.objects.create_user(username='player1', password='pass')
        
        membership = TeamMembership.objects.create(
            team=team,
            user=player,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        # Create event
        event = TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=player,
            actor=creator,
            event_type=MembershipEventType.JOINED,
            new_role=MembershipRole.PLAYER,
        )
        
        # Try to update event (should raise ValueError)
        event.new_role = MembershipRole.COACH
        
        with pytest.raises(ValueError, match='Append-only'):
            event.save()
    
    def test_team_creation_creates_joined_event_for_creator(self):
        """Verify factory creates JOINED event when team is created"""
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        
        # Verify JOINED event exists for creator
        events = TeamMembershipEvent.objects.filter(user=creator, team=team, event_type=MembershipEventType.JOINED)
        assert events.count() == 1
        
        event = events.first()
        assert event.new_role == MembershipRole.MANAGER
        assert event.new_status == MembershipStatus.ACTIVE
        assert event.metadata.get('team_creation') is True
    
    def test_add_member_rejects_owner_role(self, client):
        """Verify OWNER role assignment is rejected in add_member"""
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        new_member = User.objects.create_user(username='player1', password='pass')
        
        client.login(username='creator', password='pass')
        
        # Try to add member with OWNER role
        url = reverse('organizations_api:team_manage_add_member', kwargs={'slug': 'delta'})
        response = client.post(url, {
            'user_id': new_member.id,
            'role': MembershipRole.OWNER,
        }, content_type='application/json')
        
        assert response.status_code == 400
        data = response.json()
        assert 'OWNER role cannot be assigned' in data['error']
        assert 'MANAGER' in data['error']
    
    def test_change_role_rejects_owner_role(self, client):
        """Verify OWNER role assignment is rejected in change_role"""
        creator = User.objects.create_user(username='creator', password='pass')
        team = create_independent_team(creator, 'Delta', 'delta')
        member_user = User.objects.create_user(username='player1', password='pass')
        
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        client.login(username='creator', password='pass')
        
        # Try to change role to OWNER
        url = reverse('organizations_api:team_manage_change_role', kwargs={'slug': 'delta', 'membership_id': membership.id})
        response = client.post(url, {
            'role': MembershipRole.OWNER,
        }, content_type='application/json')
        
        assert response.status_code == 400
        data = response.json()
        assert 'OWNER role cannot be assigned' in data['error']
        assert 'MANAGER' in data['error']
    
    def test_pagination_stable_order_and_no_crash(self, client):
        """Verify pagination returns stable order and doesn't crash"""
        creator = User.objects.create_user(username='creator', password='pass')
        
        # Create multiple teams for player
        player = User.objects.create_user(username='player1', password='pass')
        teams = []
        for i in range(5):
            team = create_independent_team(creator, f'Team{i}', f'team{i}')
            membership = TeamMembership.objects.create(
                team=team,
                user=player,
                role=MembershipRole.PLAYER,
                status=MembershipStatus.ACTIVE,
                joined_at=timezone.now(),
            )
            TeamMembershipEvent.objects.create(
                membership=membership,
                team=team,
                user=player,
                actor=creator,
                event_type=MembershipEventType.JOINED,
                new_role=MembershipRole.PLAYER,
                new_status=MembershipStatus.ACTIVE,
            )
            teams.append(team)
        
        client.login(username='player1', password='pass')
        
        # Test pagination with limit
        url = reverse('organizations_api:user_team_history', kwargs={'user_id': player.id})
        response = client.get(url, {'limit': 3})
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify stable pagination structure
        assert 'pagination' in data
        assert data['pagination']['limit'] == 3
        assert len(data['history']) == 3
        
        # Verify ordered by joined_at desc
        joined_dates = [h['joined_at'] for h in data['history']]
        assert joined_dates == sorted(joined_dates, reverse=True)
        
        # Test cursor pagination
        if data['pagination']['next_cursor']:
            response2 = client.get(url, {'limit': 3, 'cursor': data['pagination']['next_cursor']})
            assert response2.status_code == 200
            data2 = response2.json()
            assert len(data2['history']) <= 3
    
    def test_metadata_redaction_for_non_staff(self, client):
        """Verify sensitive metadata is redacted for non-staff users"""
        creator = User.objects.create_user(username='creator', password='pass', is_staff=True)
        team = create_independent_team(creator, 'Delta', 'delta')
        member_user = User.objects.create_user(username='player1', password='pass')
        
        membership = TeamMembership.objects.create(
            team=team,
            user=member_user,
            role=MembershipRole.PLAYER,
            status=MembershipStatus.ACTIVE,
            joined_at=timezone.now(),
        )
        
        # Create event with sensitive metadata
        TeamMembershipEvent.objects.create(
            membership=membership,
            team=team,
            user=member_user,
            actor=creator,
            event_type=MembershipEventType.STATUS_CHANGED,
            old_status=MembershipStatus.ACTIVE,
            new_status=MembershipStatus.SUSPENDED,
            metadata={
                'reason': 'Toxic behavior',
                'duration_days': 7,
                'moderator_notes': 'Second offense',
                'public_note': 'Suspended'
            },
        )
        
        # Test as non-staff user (member viewing own history)
        client.login(username='player1', password='pass')
        url = reverse('organizations_api:user_team_history', kwargs={'user_id': member_user.id})
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        
        # Find STATUS_CHANGED event
        status_event = None
        for event in data['history'][0]['events']:
            if event['type'] == MembershipEventType.STATUS_CHANGED:
                status_event = event
                break
        
        assert status_event is not None
        # Verify sensitive fields are redacted
        assert 'reason' not in status_event['metadata']
        assert 'duration_days' not in status_event['metadata']
        assert 'moderator_notes' not in status_event['metadata']
        # Public fields remain
        assert 'public_note' in status_event['metadata']
        
        # Test as staff user
        client.login(username='creator', password='pass')
        response_staff = client.get(url)
        
        assert response_staff.status_code == 200
        data_staff = response_staff.json()
        
        # Find STATUS_CHANGED event in staff response
        status_event_staff = None
        for event in data_staff['history'][0]['events']:
            if event['type'] == MembershipEventType.STATUS_CHANGED:
                status_event_staff = event
                break
        
        # Verify staff sees all metadata
        assert 'reason' in status_event_staff['metadata']
        assert 'duration_days' in status_event_staff['metadata']
        assert 'moderator_notes' in status_event_staff['metadata']

