"""
Tests for Game Profiles Admin (UP-ADMIN-03)
"""

import pytest
import json
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.contrib.admin.sites import AdminSite
from apps.user_profile.models import UserProfile, UserAuditEvent
from apps.user_profile.admin import UserProfileAdmin
from apps.user_profile.admin.game_profiles_field import GameProfilesField
from django.core.exceptions import ValidationError

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )


@pytest.fixture
def test_user(db):
    """Create test user with profile"""
    user = User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='test123'
    )
    profile = UserProfile.objects.create(
        user=user,
        display_name='Test User',
        game_profiles=[]
    )
    return user, profile


@pytest.fixture
def profile_admin():
    """Create UserProfileAdmin instance"""
    return UserProfileAdmin(UserProfile, AdminSite())


class TestGameProfilesField:
    """Test custom field validation"""
    
    def test_field_validates_valid_json(self):
        """Valid game profiles JSON passes validation"""
        field = GameProfilesField()
        valid_data = [
            {
                "game": "valorant",
                "ign": "Player#TAG",
                "rank": "Immortal",
                "verified": False
            }
        ]
        
        result = field.to_python(json.dumps(valid_data))
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]['game'] == 'valorant'
        assert result[0]['ign'] == 'Player#TAG'
        assert 'updated_at' in result[0]
    
    def test_field_rejects_invalid_json(self):
        """Invalid JSON raises ValidationError"""
        field = GameProfilesField()
        
        with pytest.raises(ValidationError, match="Invalid JSON"):
            field.to_python('{ invalid json')
    
    def test_field_rejects_non_list(self):
        """Non-list JSON raises ValidationError"""
        field = GameProfilesField()
        
        with pytest.raises(ValidationError, match="must be a JSON array"):
            field.to_python('{"game": "valorant"}')
    
    def test_field_rejects_missing_required_fields(self):
        """Missing required fields raises ValidationError"""
        field = GameProfilesField()
        
        # Missing 'ign'
        with pytest.raises(ValidationError, match="missing required 'ign'"):
            field.to_python('[{"game": "valorant"}]')
        
        # Missing 'game'
        with pytest.raises(ValidationError, match="missing required 'game'"):
            field.to_python('[{"ign": "Player#TAG"}]')
    
    def test_field_normalizes_data(self):
        """Field normalizes and adds default values"""
        field = GameProfilesField()
        
        data = [{
            "game": "VALORANT",  # uppercase
            "ign": "Player#TAG",
            # verified missing - should default to False
        }]
        
        result = field.to_python(data)
        assert result[0]['game'] == 'valorant'  # lowercased
        assert result[0]['verified'] is False
        assert 'updated_at' in result[0]


@pytest.mark.django_db
class TestUserProfileAdmin:
    """Test admin interface for game profiles"""
    
    def test_admin_form_loads_without_errors(self, profile_admin, test_user):
        """Admin form loads for profile with game_profiles"""
        user, profile = test_user
        profile.game_profiles = [
            {
                "game": "valorant",
                "ign": "Player#TAG",
                "rank": "Diamond",
                "verified": False
            }
        ]
        profile.save()
        
        # Get form
        form_class = profile_admin.get_form(None, obj=profile)
        form = form_class(instance=profile)
        
        # Should have game_profiles field
        assert 'game_profiles' in form.fields
        
        # Field should be our custom field
        assert isinstance(form.fields['game_profiles'], GameProfilesField)
    
    def test_admin_save_creates_audit_event(self, profile_admin, admin_user, test_user):
        """Saving game_profiles in admin creates audit event"""
        user, profile = test_user
        profile.game_profiles = [{"game": "lol", "ign": "OldName#123"}]
        profile.save()
        
        # Get initial audit count
        initial_count = UserAuditEvent.objects.filter(
            object_type='UserProfile',
            object_id=profile.id
        ).count()
        
        # Simulate admin change
        factory = RequestFactory()
        request = factory.post('/admin/user_profile/userprofile/')
        request.user = admin_user
        
        # Modify game_profiles
        profile.game_profiles = [
            {"game": "lol", "ign": "NewName#456", "verified": True}
        ]
        
        # Get form and save
        form_class = profile_admin.get_form(request, obj=profile)
        form = form_class(instance=profile, data={
            'game_profiles': json.dumps(profile.game_profiles),
            'display_name': profile.display_name,
            'user': profile.user.id,
        })
        
        if form.is_valid():
            profile_admin.save_model(request, profile, form, change=True)
        
        # Check audit event created
        new_count = UserAuditEvent.objects.filter(
            object_type='UserProfile',
            object_id=profile.id
        ).count()
        
        assert new_count > initial_count, "Audit event should be created"
        
        # Verify audit event details
        audit = UserAuditEvent.objects.filter(
            object_type='UserProfile',
            object_id=profile.id
        ).latest('timestamp')
        
        assert audit.actor_user_id == admin_user.id
        assert audit.field_name == 'game_profiles'
        assert 'NewName#456' in str(audit.new_value)
    
    def test_normalize_action_validates_profiles(self, profile_admin, admin_user, test_user):
        """Admin action normalizes and validates game profiles"""
        user, profile = test_user
        
        # Set malformed data directly (bypass validation)
        profile.game_profiles = [
            {
                "game": "VALORANT",  # Uppercase - should normalize
                "ign": "Player#TAG",
                "verified": "false",  # String instead of bool
            }
        ]
        profile.save(update_fields=['game_profiles'])
        
        # Create mock request
        factory = RequestFactory()
        request = factory.post('/admin/user_profile/userprofile/')
        request.user = admin_user
        request._messages = []  # Mock messages framework
        
        # Run action
        queryset = UserProfile.objects.filter(id=profile.id)
        profile_admin.normalize_game_profiles(request, queryset)
        
        # Reload profile
        profile.refresh_from_db()
        
        # Check normalization
        assert profile.game_profiles[0]['game'] == 'valorant'  # lowercased
        assert profile.game_profiles[0]['verified'] is False  # converted to bool
        assert 'updated_at' in profile.game_profiles[0]  # added
    
    def test_form_rejects_duplicate_games(self, profile_admin, test_user):
        """Form validation rejects duplicate game entries"""
        user, profile = test_user
        
        # Get form
        form_class = profile_admin.get_form(None, obj=profile)
        
        # Try to submit duplicate games
        duplicate_data = [
            {"game": "valorant", "ign": "Player1#TAG"},
            {"game": "valorant", "ign": "Player2#TAG"},  # Duplicate!
        ]
        
        form = form_class(instance=profile, data={
            'game_profiles': json.dumps(duplicate_data),
            'display_name': profile.display_name,
            'user': profile.user.id,
        })
        
        assert not form.is_valid()
        assert 'game_profiles' in form.errors
        assert 'Duplicate' in str(form.errors['game_profiles'])


class TestUserProfileAdminListDisplay:
    """Tests for UP-ADMIN-04: List display methods"""
    
    def test_games_count_with_no_games(self, profile_admin, test_user):
        """Test games_count returns 0 when no games"""
        user, profile = test_user
        profile.game_profiles = None
        profile.save()
        
        count = profile_admin.games_count(profile)
        
        assert count == 0
    
    def test_games_count_with_games(self, profile_admin, test_user):
        """Test games_count returns correct count"""
        user, profile = test_user
        profile.game_profiles = [
            {'game': 'valorant', 'ign': 'TestVLR'},
            {'game': 'lol', 'ign': 'TestLOL'},
            {'game': 'csgo', 'ign': 'TestCS'}
        ]
        profile.save()
        
        count = profile_admin.games_count(profile)
        
        assert count == 3
    
    def test_games_summary_with_no_games(self, profile_admin, test_user):
        """Test games_summary shows 'No games' when empty"""
        user, profile = test_user
        profile.game_profiles = None
        profile.save()
        
        summary = profile_admin.games_summary(profile)
        
        assert 'No games' in summary
    
    def test_games_summary_with_three_or_less_games(self, profile_admin, test_user):
        """Test games_summary shows all games when 3 or less"""
        user, profile = test_user
        profile.game_profiles = [
            {'game': 'valorant', 'ign': 'TestVLR'},
            {'game': 'lol', 'ign': 'TestLOL'}
        ]
        profile.save()
        
        summary = profile_admin.games_summary(profile)
        
        assert 'VALORANT' in summary
        assert 'LOL' in summary
        assert '+' not in summary  # No "+N more"
    
    def test_games_summary_with_more_than_three_games(self, profile_admin, test_user):
        """Test games_summary shows first 3 plus count when >3"""
        user, profile = test_user
        profile.game_profiles = [
            {'game': 'valorant', 'ign': 'TestVLR'},
            {'game': 'lol', 'ign': 'TestLOL'},
            {'game': 'csgo', 'ign': 'TestCS'},
            {'game': 'dota2', 'ign': 'TestDOTA'},
            {'game': 'apex', 'ign': 'TestAPEX'}
        ]
        profile.save()
        
        summary = profile_admin.games_summary(profile)
        
        assert 'VALORANT' in summary
        assert 'LOL' in summary
        assert 'CSGO' in summary
        assert '+2 more' in summary


class TestUserProfileAdminActions:
    """Tests for UP-ADMIN-04: Admin action audit trail"""
    
    def test_normalize_game_profiles_creates_audit_events(self, profile_admin, admin_user, test_user):
        """Test normalize_game_profiles creates UserAuditEvent for each change"""
        user, profile = test_user
        profile.game_profiles = [
            {'game': 'Valorant', 'ign': 'TestVLR'}  # Needs normalization (uppercase V)
        ]
        profile.save()
        
        # Create mock request
        factory = RequestFactory()
        request = factory.post('/admin/user_profile/userprofile/')
        request.user = admin_user
        
        # Execute action
        queryset = UserProfile.objects.filter(id=profile.id)
        profile_admin.normalize_game_profiles(request, queryset)
        
        # Check audit event created
        audit_events = UserAuditEvent.objects.filter(
            profile=profile,
            field_name='game_profiles',
            actor_user_id=admin_user.id
        )
        
        assert audit_events.exists(), "Audit event not created"
        
        # Verify event contains old and new values
        event = audit_events.first()
        assert event.old_value is not None
        assert event.new_value is not None

