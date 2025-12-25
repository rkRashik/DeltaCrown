"""
Tests for UP-CLEANUP-04 Phase C Part 2: Safe Game Profile Mutation Endpoints

Coverage:
- Game profile batch save (validation, audit, deduplication)
- Game ID API update (privacy, audit, validation)
- Follow event types (FOLLOW_CREATED, FOLLOW_DELETED)

Tests (14 total):
- save_game_profiles_safe: 6 tests
- update_game_id_safe: 4 tests
- Follow event type updates: 4 tests
"""
import pytest
import json
from django.test import Client
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.user_profile.models_main import GameProfile, Follow
from apps.user_profile.models.audit import UserAuditEvent

User = get_user_model()


@pytest.fixture
def charlie_cleanup04(db):
    """Create test user charlie with profile."""
    user = User.objects.create_user(
        username='charlie_cleanup04',
        email='charlie@test.com',
        password='pass123'
    )
    # Profile created via signal
    return user


@pytest.fixture
def dave_cleanup04(db):
    """Create test user dave with profile."""
    user = User.objects.create_user(
        username='dave_cleanup04',
        email='dave@test.com',
        password='pass123'
    )
    return user


@pytest.mark.django_db
class TestSaveGameProfilesSafe:
    """Test safe game profiles batch save endpoint."""
    
    def test_batch_save_creates_game_profiles(self, client: Client, charlie_cleanup04):
        """Batch save creates multiple game profiles."""
        client.force_login(charlie_cleanup04)
        
        response = client.post('/actions/game-profiles/save/', {
            'game_valorant_ign': 'Charlie#VAL',
            'game_valorant_role': 'Duelist',
            'game_valorant_rank': 'Platinum',
            'game_dota2_ign': 'CharlieDota',
            'game_dota2_role': 'Mid',
        })
        
        assert response.status_code == 302  # Redirect to settings
        
        # Verify game profiles created
        valorant = GameProfile.objects.get(user=charlie_cleanup04, game='valorant')
        assert valorant.in_game_name == 'Charlie#VAL'
        assert valorant.main_role == 'Duelist'
        assert valorant.rank_name == 'Platinum'
        
        dota = GameProfile.objects.get(user=charlie_cleanup04, game='dota2')
        assert dota.in_game_name == 'CharlieDota'
        assert dota.main_role == 'Mid'
    
    def test_batch_save_creates_audit_events(self, client: Client, charlie_cleanup04):
        """Batch save records audit events for each game."""
        client.force_login(charlie_cleanup04)
        initial_count = UserAuditEvent.objects.count()
        
        client.post('/actions/game-profiles/save/', {
            'game_valorant_ign': 'Charlie#VAL',
            'game_dota2_ign': 'CharlieDota',
        })
        
        # Verify 2 audit events created (one per game)
        new_events = UserAuditEvent.objects.filter(
            subject_user=charlie_cleanup04,
            event_type=UserAuditEvent.EventType.GAME_PROFILE_CREATED
        ).count()
        assert new_events == 2
    
    def test_batch_save_updates_existing_profiles(self, client: Client, charlie_cleanup04):
        """Batch save updates existing game profiles (not duplicate)."""
        client.force_login(charlie_cleanup04)
        
        # Create initial profile
        GameProfile.objects.create(
            user=charlie_cleanup04,
            game='valorant',
            in_game_name='OldName#123',
            main_role='Sentinel'
        )
        
        # Update via batch save
        client.post('/actions/game-profiles/save/', {
            'game_valorant_ign': 'NewName#456',
            'game_valorant_role': 'Duelist',
        })
        
        # Verify only 1 profile exists (updated, not duplicated)
        assert GameProfile.objects.filter(user=charlie_cleanup04, game='valorant').count() == 1
        
        profile = GameProfile.objects.get(user=charlie_cleanup04, game='valorant')
        assert profile.in_game_name == 'NewName#456'
        assert profile.main_role == 'Duelist'
    
    def test_batch_save_removes_omitted_games(self, client: Client, charlie_cleanup04):
        """Batch save removes game profiles not in submitted data."""
        client.force_login(charlie_cleanup04)
        
        # Create 2 profiles
        GameProfile.objects.create(user=charlie_cleanup04, game='valorant', in_game_name='Player1')
        GameProfile.objects.create(user=charlie_cleanup04, game='dota2', in_game_name='Player2')
        
        # Submit only valorant (dota2 omitted)
        client.post('/actions/game-profiles/save/', {
            'game_valorant_ign': 'Player1Updated',
        })
        
        # Verify dota2 removed
        assert GameProfile.objects.filter(user=charlie_cleanup04, game='valorant').exists()
        assert not GameProfile.objects.filter(user=charlie_cleanup04, game='dota2').exists()
    
    def test_batch_save_validates_ign_length(self, client: Client, charlie_cleanup04):
        """Batch save validates IGN length (100 char max)."""
        client.force_login(charlie_cleanup04)
        
        long_ign = 'A' * 101  # Exceeds MAX_IGN_LENGTH
        
        response = client.post('/actions/game-profiles/save/', {
            'game_valorant_ign': long_ign,
        })
        
        # Should show error message
        assert response.status_code == 302
        # Profile should not be created
        assert not GameProfile.objects.filter(user=charlie_cleanup04, game='valorant').exists()
    
    def test_batch_save_skips_empty_ign(self, client: Client, charlie_cleanup04):
        """Batch save skips games with empty IGN."""
        client.force_login(charlie_cleanup04)
        
        client.post('/actions/game-profiles/save/', {
            'game_valorant_ign': '',  # Empty
            'game_dota2_ign': 'ValidPlayer',
        })
        
        # Only dota2 should be created
        assert not GameProfile.objects.filter(user=charlie_cleanup04, game='valorant').exists()
        assert GameProfile.objects.filter(user=charlie_cleanup04, game='dota2').exists()


@pytest.mark.django_db
class TestUpdateGameIdSafe:
    """Test safe game ID API endpoint."""
    
    def test_update_game_id_creates_profile(self, client: Client, charlie_cleanup04):
        """Update game ID creates new game profile."""
        client.force_login(charlie_cleanup04)
        
        response = client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({
                'game': 'valorant',
                'ign': 'TestPlayer#123',
                'role': 'Controller',
                'rank': 'Diamond'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'created' in data['message']
        
        # Verify profile created
        profile = GameProfile.objects.get(user=charlie_cleanup04, game='valorant')
        assert profile.in_game_name == 'TestPlayer#123'
        assert profile.main_role == 'Controller'
        assert profile.rank_name == 'Diamond'
    
    def test_update_game_id_updates_existing(self, client: Client, charlie_cleanup04):
        """Update game ID updates existing profile."""
        client.force_login(charlie_cleanup04)
        
        # Create initial
        GameProfile.objects.create(
            user=charlie_cleanup04,
            game='valorant',
            in_game_name='OldName#000',
            main_role='Sentinel'
        )
        
        # Update
        response = client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({
                'game': 'valorant',
                'ign': 'NewName#999',
                'role': 'Duelist'
            }),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'updated' in data['message']
        
        # Verify only 1 profile (updated)
        assert GameProfile.objects.filter(user=charlie_cleanup04, game='valorant').count() == 1
        profile = GameProfile.objects.get(user=charlie_cleanup04, game='valorant')
        assert profile.in_game_name == 'NewName#999'
        assert profile.main_role == 'Duelist'
    
    def test_update_game_id_creates_audit_event(self, client: Client, charlie_cleanup04):
        """Update game ID records audit event."""
        client.force_login(charlie_cleanup04)
        initial_count = UserAuditEvent.objects.count()
        
        client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({
                'game': 'dota2',
                'ign': 'DotaPlayer'
            }),
            content_type='application/json'
        )
        
        # Verify audit event created
        assert UserAuditEvent.objects.count() == initial_count + 1
        
        audit = UserAuditEvent.objects.latest('created_at')
        assert audit.event_type == UserAuditEvent.EventType.GAME_PROFILE_CREATED
        assert audit.subject_user_id == charlie_cleanup04.id
        assert audit.object_type == 'GameProfile'
    
    def test_update_game_id_validates_required_fields(self, client: Client, charlie_cleanup04):
        """Update game ID validates required fields."""
        client.force_login(charlie_cleanup04)
        
        # Missing game
        response = client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({'ign': 'Player'}),
            content_type='application/json'
        )
        assert response.status_code == 400
        assert not response.json()['success']
        
        # Missing IGN
        response = client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({'game': 'valorant'}),
            content_type='application/json'
        )
        assert response.status_code == 400
        assert not response.json()['success']


@pytest.mark.django_db
class TestFollowEventTypes:
    """Test updated follow/unfollow event types."""
    
    def test_follow_uses_follow_created_event(self, client: Client, charlie_cleanup04, dave_cleanup04):
        """Follow action uses FOLLOW_CREATED event type."""
        client.force_login(charlie_cleanup04)
        
        # Enable privacy (allow follow)
        from apps.user_profile.models import PrivacySettings
        PrivacySettings.objects.get_or_create(
            user_profile=dave_cleanup04.profile,
            defaults={'allow_friend_requests': True}
        )
        
        initial_count = UserAuditEvent.objects.count()
        
        response = client.post(f'/actions/follow-safe/{dave_cleanup04.username}/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify FOLLOW_CREATED event
        audit = UserAuditEvent.objects.latest('created_at')
        assert audit.event_type == UserAuditEvent.EventType.FOLLOW_CREATED
        assert audit.subject_user_id == dave_cleanup04.id  # Person being followed
        assert audit.actor_user_id == charlie_cleanup04.id  # Person doing the follow
    
    def test_unfollow_uses_follow_deleted_event(self, client: Client, charlie_cleanup04, dave_cleanup04):
        """Unfollow action uses FOLLOW_DELETED event type."""
        client.force_login(charlie_cleanup04)
        
        # Create follow first
        from apps.user_profile.models_main import Follow
        Follow.objects.create(follower=charlie_cleanup04, following=dave_cleanup04)
        
        initial_count = UserAuditEvent.objects.count()
        
        response = client.post(f'/actions/unfollow-safe/{dave_cleanup04.username}/')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        
        # Verify FOLLOW_DELETED event
        audit = UserAuditEvent.objects.latest('created_at')
        assert audit.event_type == UserAuditEvent.EventType.FOLLOW_DELETED
        assert audit.subject_user_id == dave_cleanup04.id
        assert audit.actor_user_id == charlie_cleanup04.id
    
    def test_follow_event_has_correct_metadata(self, client: Client, charlie_cleanup04, dave_cleanup04):
        """Follow audit event contains correct metadata."""
        client.force_login(charlie_cleanup04)
        
        # Enable privacy
        from apps.user_profile.models import PrivacySettings
        PrivacySettings.objects.get_or_create(
            user_profile=dave_cleanup04.profile,
            defaults={'allow_friend_requests': True}
        )
        
        client.post(f'/actions/follow-safe/{dave_cleanup04.username}/')
        
        audit = UserAuditEvent.objects.latest('created_at')
        assert audit.object_type == 'Follow'
        assert audit.source_app == 'user_profile'
        # Should have after_snapshot with follow details
        assert 'following' in audit.after_snapshot
    
    def test_unfollow_event_has_before_snapshot(self, client: Client, charlie_cleanup04, dave_cleanup04):
        """Unfollow audit event captures before snapshot."""
        client.force_login(charlie_cleanup04)
        
        # Create follow
        from apps.user_profile.models_main import Follow
        Follow.objects.create(follower=charlie_cleanup04, following=dave_cleanup04)
        
        client.post(f'/actions/unfollow-safe/{dave_cleanup04.username}/')
        
        audit = UserAuditEvent.objects.latest('created_at')
        # Should have before_snapshot with follow details
        assert 'following' in audit.before_snapshot
        assert audit.after_snapshot == {}  # Empty after deletion
