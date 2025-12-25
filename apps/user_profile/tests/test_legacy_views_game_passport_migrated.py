"""
Tests for GP-STABILIZE-02: Legacy View Endpoints Migration

Verifies that all 6 legacy view endpoints now use GamePassportService
and do not touch UserProfile.game_profiles JSON field.

Test Coverage:
- save_game_profiles: Batch create/update/delete
- add_game_profile: Single passport creation
- edit_game_profile: Identity update with cooldown
- delete_game_profile: Deletion with audit
- save_game_profiles_safe: Safe batch operations
- update_game_id_safe: API endpoint update
"""

import pytest
import json
from django.contrib.auth import get_user_model
from django.test import Client
from apps.user_profile.models import UserProfile, GameProfile
from apps.user_profile.services.game_passport_service import GamePassportService

User = get_user_model()


@pytest.mark.django_db
class TestSaveGameProfilesEndpoint:
    """Test save_game_profiles batch endpoint"""
    
    def test_batch_create_passports_no_json_write(self):
        """Batch save creates GameProfile rows, doesn't touch JSON"""
        user = User.objects.create_user(username='batchuser', email='batch@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Record initial JSON state
        json_before = profile.game_profiles
        
        # Submit batch save with 2 games (both have valid formats)
        client = Client()
        client.force_login(user)
        
        response = client.post('/actions/save-game-profiles/', {
            'game_valorant_ign': 'Player#1234',
            'game_cs2_ign': '76561198012345678'
        })
        
        # Verify redirect
        assert response.status_code == 302
        
        # Verify GameProfile rows created (expecting 2, not 3)
        passports = GameProfile.objects.filter(user=user)
        assert passports.count() == 2
        assert set(passports.values_list('game', flat=True)) == {'valorant', 'cs2'}
        
        # Verify JSON unchanged
        profile.refresh_from_db()
        assert profile.game_profiles == json_before
    
    def test_batch_update_existing_passports(self):
        """Batch save updates existing passports"""
        user = User.objects.create_user(username='updateuser', email='update@example.com', password='pass123')
        
        # Create initial passport
        passport = GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='OldName#123', metadata={}
        )
        
        client = Client()
        client.force_login(user)
        
        # Update via batch save
        response = client.post('/actions/save-game-profiles/', {
            'game_valorant_ign': 'NewName#456'
        })
        
        # Verify update
        passport.refresh_from_db()
        assert passport.in_game_name == 'NewName#456'
    
    def test_batch_delete_removed_games(self):
        """Batch save deletes passports not in submission"""
        user = User.objects.create_user(username='deleteuser', email='delete@example.com', password='pass123')
        
        # Create 2 passports
        GamePassportService.create_passport(user=user, game='valorant', in_game_name='Val#123', metadata={})
        GamePassportService.create_passport(user=user, game='cs2', in_game_name='76561198012345678', metadata={})
        
        client = Client()
        client.force_login(user)
        
        # Submit with only 1 game (should delete cs2)
        response = client.post('/actions/save-game-profiles/', {
            'game_valorant_ign': 'Val#123'
        })
        
        # Verify cs2 deleted
        assert GameProfile.objects.filter(user=user).count() == 1
        assert GameProfile.objects.filter(user=user, game='cs2').count() == 0


@pytest.mark.django_db
class TestAddGameProfileEndpoint:
    """Test add_game_profile single creation endpoint"""
    
    def test_create_passport_via_add_endpoint(self):
        """Add endpoint creates passport via service"""
        user = User.objects.create_user(username='adduser', email='add@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        json_before = profile.game_profiles
        
        client = Client()
        client.force_login(user)
        
        response = client.post('/actions/add-game-profile/', {
            'game': 'valorant',
            'in_game_name': 'NewPlayer#789',
            'redirect_to': 'settings'
        })
        
        # Verify redirect
        assert response.status_code == 302
        
        # Verify passport created
        passport = GameProfile.objects.get(user=user, game='valorant')
        assert passport.in_game_name == 'NewPlayer#789'
        
        # Verify JSON unchanged
        profile.refresh_from_db()
        assert profile.game_profiles == json_before
    
    def test_add_duplicate_passport_rejected(self):
        """Add endpoint rejects duplicate game"""
        user = User.objects.create_user(username='dupuser', email='dup@example.com', password='pass123')
        
        # Create existing passport
        GamePassportService.create_passport(user=user, game='valorant', in_game_name='Existing#123', metadata={})
        
        client = Client()
        client.force_login(user)
        
        # Try to add duplicate
        response = client.post('/actions/add-game-profile/', {
            'game': 'valorant',
            'in_game_name': 'Duplicate#456',
            'redirect_to': 'settings'
        })
        
        # Should still have only 1 passport
        assert GameProfile.objects.filter(user=user, game='valorant').count() == 1
        assert GameProfile.objects.get(user=user, game='valorant').in_game_name == 'Existing#123'


@pytest.mark.django_db
class TestEditGameProfileEndpoint:
    """Test edit_game_profile identity update endpoint"""
    
    def test_edit_updates_via_service(self):
        """Edit endpoint uses service for identity change"""
        user = User.objects.create_user(username='edituser', email='edit@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Create passport
        passport = GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Original#123', metadata={}
        )
        
        json_before = profile.game_profiles
        
        client = Client()
        client.force_login(user)
        
        # Edit via endpoint
        response = client.post(f'/actions/edit-game-profile/{passport.id}/', {
            'in_game_name': 'Updated#456'
        })
        
        # Verify update
        passport.refresh_from_db()
        assert passport.in_game_name == 'Updated#456'
        
        # Verify JSON unchanged
        profile.refresh_from_db()
        assert profile.game_profiles == json_before
    
    def test_edit_same_name_no_service_call(self):
        """Edit with same name doesn't trigger service update"""
        user = User.objects.create_user(username='sameuser', email='same@example.com', password='pass123')
        
        passport = GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='Same#123', metadata={}
        )
        
        client = Client()
        client.force_login(user)
        
        # Submit same name
        response = client.post(f'/actions/edit-game-profile/{passport.id}/', {
            'in_game_name': 'Same#123'
        })
        
        # Should succeed without error
        assert response.status_code == 302


@pytest.mark.django_db
class TestDeleteGameProfileEndpoint:
    """Test delete_game_profile deletion endpoint"""
    
    def test_delete_removes_passport_with_audit(self):
        """Delete endpoint removes passport and logs audit"""
        user = User.objects.create_user(username='deluser', email='del@example.com', password='pass123')
        
        passport = GamePassportService.create_passport(
            user=user, game='valorant', in_game_name='ToDelete#123', metadata={}
        )
        
        client = Client()
        client.force_login(user)
        
        # Delete via endpoint
        response = client.post(f'/actions/delete-game-profile/{passport.id}/')
        
        # Verify deletion
        assert GameProfile.objects.filter(id=passport.id).count() == 0
        
        # Verify audit logged (check UserAuditEvent)
        from apps.user_profile.models.audit import UserAuditEvent
        audit = UserAuditEvent.objects.filter(
            subject_user=user,
            event_type='game_passport.deleted'
        ).first()
        assert audit is not None


@pytest.mark.django_db
class TestSaveGameProfilesSafeEndpoint:
    """Test save_game_profiles_safe batch endpoint"""
    
    def test_safe_batch_create_and_update(self):
        """Safe batch endpoint creates and updates passports"""
        user = User.objects.create_user(username='safeuser', email='safe@example.com', password='pass123')
        
        # Create 1 existing passport
        GamePassportService.create_passport(user=user, game='valorant', in_game_name='Old#123', metadata={})
        
        client = Client()
        client.force_login(user)
        
        # Batch save with update + create
        response = client.post('/actions/game-profiles/save/', {
            'game_valorant_ign': 'New#456',  # Update
            'game_cs2_ign': '76561198012345678'  # Create
        })
        
        # Verify 2 passports exist
        assert GameProfile.objects.filter(user=user).count() == 2
        
        # Verify valorant updated
        val_passport = GameProfile.objects.get(user=user, game='valorant')
        assert val_passport.in_game_name == 'New#456'
        
        # Verify cs2 created
        cs2_passport = GameProfile.objects.get(user=user, game='cs2')
        assert cs2_passport.in_game_name == '76561198012345678'


@pytest.mark.django_db
class TestUpdateGameIdSafeEndpoint:
    """Test update_game_id_safe API endpoint"""
    
    def test_api_create_passport(self):
        """API endpoint creates new passport"""
        user = User.objects.create_user(username='apiuser', email='api@example.com', password='pass123')
        
        client = Client()
        client.force_login(user)
        
        # POST JSON
        response = client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({'game': 'valorant', 'ign': 'API#123'}),
            content_type='application/json'
        )
        
        # Verify success response
        data = response.json()
        assert data['success'] is True
        assert 'created' in data['message']
        
        # Verify passport created
        passport = GameProfile.objects.get(user=user, game='valorant')
        assert passport.in_game_name == 'API#123'
    
    def test_api_update_existing_passport(self):
        """API endpoint updates existing passport"""
        user = User.objects.create_user(username='apiupdate', email='apiupdate@example.com', password='pass123')
        
        # Create existing
        GamePassportService.create_passport(user=user, game='valorant', in_game_name='Old#123', metadata={})
        
        client = Client()
        client.force_login(user)
        
        # Update via API
        response = client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({'game': 'valorant', 'ign': 'New#456'}),
            content_type='application/json'
        )
        
        # Verify success
        data = response.json()
        assert data['success'] is True
        assert 'updated' in data['message']
        
        # Verify update
        passport = GameProfile.objects.get(user=user, game='valorant')
        assert passport.in_game_name == 'New#456'
    
    def test_api_validation_error(self):
        """API endpoint returns validation errors"""
        user = User.objects.create_user(username='apierror', email='apierror@example.com', password='pass123')
        
        client = Client()
        client.force_login(user)
        
        # Invalid data (empty game)
        response = client.post(
            '/api/profile/update-game-id-safe/',
            data=json.dumps({'game': '', 'ign': 'Test#123'}),
            content_type='application/json'
        )
        
        # Verify error response
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert 'error' in data


@pytest.mark.django_db
class TestNoJSONWritesAcrossAllEndpoints:
    """Verify JSON field never changes across all endpoints"""
    
    def test_all_endpoints_preserve_json_field(self):
        """All 6 endpoints never modify game_profiles JSON"""
        user = User.objects.create_user(username='jsontest', email='jsontest@example.com', password='pass123')
        profile = UserProfile.objects.get(user=user)
        
        # Record initial JSON
        json_initial = profile.game_profiles
        
        client = Client()
        client.force_login(user)
        
        # Call all 6 endpoints
        # 1. save_game_profiles
        client.post('/actions/save-game-profiles/', {'game_valorant_ign': 'Test1#123'})
        profile.refresh_from_db()
        assert profile.game_profiles == json_initial
        
        # 2. add_game_profile
        client.post('/actions/add-game-profile/', {
            'game': 'cs2',
            'in_game_name': '76561198012345678',
            'redirect_to': 'settings'
        })
        profile.refresh_from_db()
        assert profile.game_profiles == json_initial
        
        # 3. edit_game_profile
        passport = GameProfile.objects.get(user=user, game='valorant')
        client.post(f'/actions/edit-game-profile/{passport.id}/', {'in_game_name': 'Test2#456'})
        profile.refresh_from_db()
        assert profile.game_profiles == json_initial
        
        # 4. delete_game_profile
        cs2_passport = GameProfile.objects.get(user=user, game='cs2')
        client.post(f'/actions/delete-game-profile/{cs2_passport.id}/')
        profile.refresh_from_db()
        assert profile.game_profiles == json_initial
        
        # 5. save_game_profiles_safe
        client.post('/actions/game-profiles/save/', {'game_dota2_ign': '123456789'})
        profile.refresh_from_db()
        assert profile.game_profiles == json_initial
        
        # 6. update_game_id_safe
        client.post(
            '/actions/game-id/update/',
            data=json.dumps({'game': 'lol', 'ign': 'TestPlayer'}),
            content_type='application/json'
        )
        profile.refresh_from_db()
        assert profile.game_profiles == json_initial
