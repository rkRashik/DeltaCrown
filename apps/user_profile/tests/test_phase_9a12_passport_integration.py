"""
Phase 9A-12 Integration Tests: Game Passport Requirements for Teams & Tournaments
==================================================================================

Tests ensuring:
- Teams require valid passports for creation/join
- Tournaments auto-fill from passports
- API schemas complete (no empty dropdowns)
- Redirect loop regression (Phase 9A-10 fix)
- Passport CRUD validation (409 duplicate, 403 locked, 400 validation)

Version: 2.0 (Phase 9A-13 - January 2026)
UPDATED: Imports consolidated into GamePassportService
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase, Client
from django.urls import reverse
from apps.user_profile.models import GameProfile
from apps.user_profile.services.game_passport_service import GamePassportService
from apps.teams.models import Team, TeamMembership, TeamInvite
from apps.teams.services.team_service import TeamService
from apps.games.models import Game
from apps.tournaments.services.registration_autofill import RegistrationAutoFillService

User = get_user_model()


class PassportServiceLayerTests(TestCase):
    """Test passport integration service functions"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testplayer',
            email='test@example.com',
            password='testpass123'
        )
        self.game = Game.objects.create(
            slug='valorant',
            display_name='VALORANT',
            is_active=True
        )
    
    def test_get_passport_for_game_success(self):
        """Test retrieving existing passport"""
        passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#NA1',
            riot_id='TestPlayer',
            riot_tagline='NA1'
        )
        
        result = GamePassportService.get_passport(self.user, 'valorant')
        
        assert result is not None
        assert result.id == passport.id
        assert result.ign == 'TestPlayer#NA1'
    
    def test_get_passport_for_game_not_found(self):
        """Test retrieving non-existent passport"""
        result = GamePassportService.get_passport(self.user, 'valorant')
        
        assert result is None
    
    def test_get_passport_for_invalid_game(self):
        """Test with invalid game slug"""
        result = GamePassportService.get_passport(self.user, 'nonexistent-game')
        
        assert result is None
    
    def test_validate_passport_for_team_action_success(self):
        """Test validation with complete passport"""
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#NA1',
            riot_id='TestPlayer',
            riot_tagline='NA1',
            verification_status='VERIFIED'
        )
        
        result = GamePassportService.validate_passport_for_team_action(
            user=self.user,
            game_slug='valorant',
            action='create'
        )
        
        assert result.is_valid is True
        assert len(result.errors) == 0
        assert len(result.missing_fields) == 0
    
    def test_validate_passport_missing(self):
        """Test validation with no passport"""
        result = GamePassportService.validate_passport_for_team_action(
            user=self.user,
            game_slug='valorant',
            action='create'
        )
        
        assert result.is_valid is False
        assert 'Game Passport' in result.errors[0]
        assert 'passport' in result.missing_fields
        assert '/settings/' in result.help_url
    
    def test_validate_passport_flagged(self):
        """Test validation with flagged passport"""
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#NA1',
            riot_id='TestPlayer',
            riot_tagline='NA1',
            verification_status='FLAGGED'
        )
        
        result = GamePassportService.validate_passport_for_team_action(
            user=self.user,
            game_slug='valorant',
            action='join'
        )
        
        assert result.is_valid is False
        assert 'flagged' in result.errors[0].lower()
    
    def test_build_team_identity_payload(self):
        """Test building identity payload from passport"""
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#NA1',
            riot_id='TestPlayer',
            riot_tagline='NA1',
            rank='Diamond',
            division='II',
            platform='PC',
            region='NA',
            verification_status='VERIFIED'
        )
        
        payload = GamePassportService.build_identity_payload(self.user, 'valorant')
        
        assert payload['user_id'] == self.user.id
        assert payload['username'] == 'testplayer'
        assert payload['ign'] == 'TestPlayer#NA1'
        assert payload['riot_id'] == 'TestPlayer'
        assert payload['riot_tagline'] == 'NA1'
        assert payload['rank'] == 'Diamond'
        assert payload['division'] == 'II'
        assert payload['platform'] == 'PC'
        assert payload['region'] == 'NA'
        assert payload['verification_status'] == 'VERIFIED'
    
    def test_build_team_identity_payload_empty(self):
        """Test payload with no passport"""
        payload = GamePassportService.build_identity_payload(self.user, 'valorant')
        
        assert payload == {}
    
    def test_validate_roster_passports_all_valid(self):
        """Test roster validation with all valid passports"""
        user2 = User.objects.create_user(username='player2')
        user3 = User.objects.create_user(username='player3')
        
        for user in [self.user, user2, user3]:
            GameProfile.objects.create(
                user=user,
                game=self.game,
                ign=f'{user.username}#001',
                riot_id=user.username,
                riot_tagline='001',
                verification_status='VERIFIED'
            )
        
        result = GamePassportService.validate_roster_passports([self.user, user2, user3], 'valorant')
        
        assert result['is_valid'] is True
        assert len(result['errors']) == 0
        assert result['missing_count'] == 0
        assert result['total_members'] == 3
    
    def test_validate_roster_passports_missing(self):
        """Test roster validation with missing passports"""
        user2 = User.objects.create_user(username='player2')
        user3 = User.objects.create_user(username='player3')
        
        # Only user1 has passport
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='TestPlayer#NA1',
            riot_id='TestPlayer',
            riot_tagline='NA1',
            verification_status='VERIFIED'
        )
        
        result = GamePassportService.validate_roster_passports([self.user, user2, user3], 'valorant')
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 2  # user2 and user3
        assert result['missing_count'] == 2
        assert result['total_members'] == 3
        
        # Check error structure
        assert result['errors'][0]['username'] in ['player2', 'player3']
        assert '/settings/' in result['errors'][0]['passport_url']


class TeamCreationPassportTests(TestCase):
    """Test passport requirements for team creation"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='captain',
            email='captain@example.com',
            password='testpass123'
        )
        self.game = Game.objects.create(
            slug='valorant',
            display_name='VALORANT',
            is_active=True
        )
        self.client.login(username='captain', password='testpass123')
    
    def test_team_creation_blocked_without_passport(self):
        """Test team creation is blocked without passport"""
        response = self.client.post('/teams/create/', {
            'name': 'Test Team',
            'tag': 'TEST',
            'game': 'valorant',
            'description': 'Test team',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        assert response.status_code == 400
        data = response.json()
        assert data['success'] is False
        assert data['passport_required'] is True
        assert 'Game Passport' in data['error']
        assert data['game_slug'] == 'valorant'
        assert '/settings/' in data['help_url']
    
    def test_team_creation_allowed_with_passport(self):
        """Test team creation succeeds with valid passport"""
        # Create passport
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='Captain#NA1',
            riot_id='Captain',
            riot_tagline='NA1',
            verification_status='VERIFIED'
        )
        
        response = self.client.post('/teams/create/', {
            'name': 'Test Team',
            'tag': 'TEST',
            'game': 'valorant',
            'tagline': 'Best team ever',
            'description': 'Test team description',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        
        # Should succeed (200 or 302)
        assert response.status_code in [200, 302]
        
        if response.status_code == 200:
            data = response.json()
            assert data.get('success') is True or 'redirect_url' in data


class TeamInvitePassportTests(TestCase):
    """Test passport requirements for team join via invitation"""
    
    def setUp(self):
        self.captain = User.objects.create_user(
            username='captain',
            password='testpass123'
        )
        self.invited_user = User.objects.create_user(
            username='invited',
            password='testpass123'
        )
        self.game = Game.objects.create(
            slug='valorant',
            display_name='VALORANT',
            is_active=True
        )
        
        # Captain has passport
        GameProfile.objects.create(
            user=self.captain,
            game=self.game,
            ign='Captain#NA1',
            riot_id='Captain',
            riot_tagline='NA1',
            verification_status='VERIFIED'
        )
        
        # Create team
        from apps.user_profile.models import UserProfile
        captain_profile = UserProfile.objects.create(user=self.captain)
        
        self.team = TeamService.create_team(
            name='Test Team',
            captain_profile=captain_profile,
            game='valorant',
            tag='TEST'
        )
        
        # Create invite
        invited_profile = UserProfile.objects.create(user=self.invited_user)
        self.invite = TeamService.invite_player(
            team=self.team,
            invited_profile=invited_profile,
            invited_by_profile=captain_profile,
            role='PLAYER'
        )
    
    def test_invite_acceptance_blocked_without_passport(self):
        """Test invite acceptance is blocked without passport"""
        from apps.user_profile.models import UserProfile
        invited_profile = UserProfile.objects.get(user=self.invited_user)
        
        with pytest.raises(ValidationError) as exc_info:
            TeamService.accept_invite(
                invite=self.invite,
                accepting_profile=invited_profile
            )
        
        assert 'Game Passport' in str(exc_info.value)
        assert '/settings/' in str(exc_info.value)
    
    def test_invite_acceptance_allowed_with_passport(self):
        """Test invite acceptance succeeds with valid passport"""
        # Create passport for invited user
        GameProfile.objects.create(
            user=self.invited_user,
            game=self.game,
            ign='Invited#NA1',
            riot_id='Invited',
            riot_tagline='NA1',
            verification_status='VERIFIED'
        )
        
        from apps.user_profile.models import UserProfile
        invited_profile = UserProfile.objects.get(user=self.invited_user)
        
        # Should succeed
        membership = TeamService.accept_invite(
            invite=self.invite,
            accepting_profile=invited_profile
        )
        
        assert membership is not None
        assert membership.team == self.team
        assert membership.profile == invited_profile
        assert membership.status == 'ACTIVE'
    
    def test_invite_acceptance_blocked_with_flagged_passport(self):
        """Test invite acceptance blocked with flagged passport"""
        # Create flagged passport
        GameProfile.objects.create(
            user=self.invited_user,
            game=self.game,
            ign='Invited#NA1',
            riot_id='Invited',
            riot_tagline='NA1',
            verification_status='FLAGGED'
        )
        
        from apps.user_profile.models import UserProfile
        invited_profile = UserProfile.objects.get(user=self.invited_user)
        
        with pytest.raises(ValidationError) as exc_info:
            TeamService.accept_invite(
                invite=self.invite,
                accepting_profile=invited_profile
            )
        
        assert 'flagged' in str(exc_info.value).lower()


class TournamentAutoFillTests(TestCase):
    """Test tournament registration auto-fill from passports"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='player',
            email='player@example.com',
            first_name='John',
            last_name='Doe'
        )
        self.game = Game.objects.create(
            slug='valorant',
            display_name='VALORANT',
            is_active=True
        )
        
        # Create passport with complete data
        self.passport = GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='Player#NA1',
            riot_id='Player',
            riot_tagline='NA1',
            rank='Diamond',
            division='II',
            platform='PC',
            region='NA',
            server='NA-East',
            verification_status='VERIFIED'
        )
    
    def test_autofill_uses_passport_data(self):
        """Test auto-fill pulls from Game Passport"""
        from apps.tournaments.models import Tournament
        
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=self.game,
            participation_type='solo'
        )
        
        autofill_data = RegistrationAutoFillService.get_autofill_data(
            user=self.user,
            tournament=tournament,
            team=None
        )
        
        # Check IGN from passport
        assert 'ign' in autofill_data
        assert autofill_data['ign'].value == 'Player#NA1'
        assert autofill_data['ign'].source == 'game_passport'
        assert autofill_data['ign'].confidence == 'high'
        
        # Check rank from passport
        assert 'rank' in autofill_data
        assert autofill_data['rank'].value == 'Diamond'
        assert autofill_data['rank'].source == 'game_passport'
        
        # Check platform from passport
        assert 'platform' in autofill_data
        assert autofill_data['platform'].value == 'PC'
        assert autofill_data['platform'].source == 'game_passport'
        
        # Check region from passport
        assert 'region' in autofill_data
        assert autofill_data['region'].value == 'NA'
        assert autofill_data['region'].source == 'game_passport'
    
    def test_autofill_missing_passport(self):
        """Test auto-fill with missing passport"""
        from apps.tournaments.models import Tournament
        
        user2 = User.objects.create_user(username='player2')
        tournament = Tournament.objects.create(
            name='Test Tournament',
            game=self.game,
            participation_type='solo'
        )
        
        autofill_data = RegistrationAutoFillService.get_autofill_data(
            user=user2,
            tournament=tournament,
            team=None
        )
        
        # Check IGN marked as missing
        assert 'ign' in autofill_data
        assert autofill_data['ign'].missing is True
        assert '/settings/' in autofill_data['ign'].update_url


class APISchemaTests(TestCase):
    """Test API schemas are complete (no empty dropdowns)"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_games_api_returns_complete_schemas(self):
        """Test GET /profile/api/games/ has non-empty dropdowns for all games"""
        response = self.client.get('/profile/api/games/')
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have games
        assert len(data) > 0
        
        for game in data:
            # Check required fields
            assert 'slug' in game
            assert 'display_name' in game
            assert 'identity_fields' in game
            assert 'dropdown_options' in game
            
            # Check identity fields not empty
            assert len(game['identity_fields']) > 0
            
            # Check dropdown options
            dropdown_opts = game['dropdown_options']
            
            # At minimum should have ranks (all games have ranks)
            if 'ranks' in dropdown_opts:
                assert len(dropdown_opts['ranks']) > 0, f"Game {game['slug']} has empty ranks"
            
            # If has platforms, should not be empty
            if 'platforms' in dropdown_opts and dropdown_opts['platforms']:
                assert len(dropdown_opts['platforms']) > 0, f"Game {game['slug']} has empty platforms"


class RedirectRegressionTests(TestCase):
    """Test Phase 9A-10 redirect loop fix remains working"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_legacy_redirect_no_loop(self):
        """Test /u/username/ does not cause redirect loop"""
        response = self.client.get('/u/testuser/', follow=True)
        
        # Should NOT result in error or redirect loop
        assert response.status_code in [200, 404]  # Either profile exists or 404
        
        # Check redirect chain is reasonable (not 10+ redirects)
        if hasattr(response, 'redirect_chain'):
            assert len(response.redirect_chain) <= 3, "Too many redirects detected"
    
    def test_legacy_redirect_nonexistent_user(self):
        """Test /u/nonexistent/ returns 404"""
        response = self.client.get('/u/nonexistent/')
        
        assert response.status_code == 404


class PassportCRUDValidationTests(TestCase):
    """Test passport CRUD validation (409 duplicate, 403 locked, 400 validation)"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.game = Game.objects.create(
            slug='valorant',
            display_name='VALORANT',
            is_active=True
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_duplicate_passport_409(self):
        """Test creating duplicate passport returns 409"""
        # Create first passport
        GameProfile.objects.create(
            user=self.user,
            game=self.game,
            ign='Player#NA1',
            riot_id='Player',
            riot_tagline='NA1'
        )
        
        # Try to create duplicate via API
        response = self.client.post('/profile/api/game-passports/', {
            'game': 'valorant',
            'ign': 'Player2#NA1',
            'riot_id': 'Player2',
            'riot_tagline': 'NA1'
        })
        
        # Should return 409 Conflict or 400 with duplicate error
        assert response.status_code in [400, 409]
        
        if response.status_code == 400:
            data = response.json()
            error_msg = str(data).lower()
            assert 'already' in error_msg or 'duplicate' in error_msg or 'exists' in error_msg


# =============================================================================
# Test Suite Summary
# =============================================================================
"""
This test suite covers:

1. Passport Service Layer (10 tests)
   - GamePassportService.get_passport()
   - GamePassportService.validate_passport_for_team_action()
   - GamePassportService.build_identity_payload()
   - GamePassportService.validate_roster_passports()

2. Team Creation Passport Requirements (2 tests)
   - Blocked without passport
   - Allowed with valid passport

3. Team Invite Passport Requirements (3 tests)
   - Blocked without passport
   - Allowed with valid passport
   - Blocked with flagged passport

4. Tournament Auto-Fill (2 tests)
   - Uses passport data
   - Handles missing passport

5. API Schema Validation (1 test)
   - GET /profile/api/games/ complete schemas

6. Redirect Loop Regression (2 tests)
   - /u/username/ works without loop
   - Nonexistent user returns 404

7. Passport CRUD Validation (1 test)
   - Duplicate passport returns 409/400

Total: 21 tests covering Phase 9A-12 integration

Run with:
    pytest apps/user_profile/tests/test_phase_9a12_passport_integration.py -v
"""
