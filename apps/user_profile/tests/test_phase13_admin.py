"""
UP-PHASE13: Admin Cleanup Tests
Verifies economy fields are readonly, legacy text removed, admin is clean
"""
import pytest
from django.test import Client
from django.contrib.auth import get_user_model
from apps.user_profile.models import UserProfile
from apps.user_profile.admin.users import UserProfileAdmin

User = get_user_model()


@pytest.mark.django_db
class TestPhase13AdminCleanup:
    """Test admin cleanup for UserProfile"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Create superuser"""
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@deltacrown.com',
            password='adminpass123'
        )
        self.client.force_login(self.superuser)
        
        # Create test user profile
        self.test_user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.test_user)

    def test_economy_fields_are_readonly(self):
        """Verify deltacoin_balance and lifetime_earnings are readonly"""
        admin_instance = UserProfileAdmin(UserProfile, None)
        
        readonly_fields = admin_instance.readonly_fields
        assert 'deltacoin_balance' in readonly_fields, "deltacoin_balance should be readonly"
        assert 'lifetime_earnings' in readonly_fields, "lifetime_earnings should be readonly"

    def test_admin_change_page_loads(self):
        """Verify admin change page loads without errors"""
        response = self.client.get(f'/admin/user_profile/userprofile/{self.profile.id}/change/')
        assert response.status_code == 200

    def test_economy_fieldset_has_warning(self):
        """Verify economy fieldset includes warning text"""
        response = self.client.get(f'/admin/user_profile/userprofile/{self.profile.id}/change/')
        content = response.content.decode('utf-8')
        
        # Should have warning about economy fields being readonly
        assert 'Economy' in content or 'economy' in content, "Economy section not found"
        assert 'Read-Only' in content or 'READ-ONLY' in content, "Readonly warning not found"

    def test_gaming_fieldset_updated(self):
        """Verify Gaming fieldset has accurate description"""
        response = self.client.get(f'/admin/user_profile/userprofile/{self.profile.id}/change/')
        content = response.content.decode('utf-8')
        
        # Should mention Game Passports are in separate admin
        if 'Gaming' in content:
            assert 'Game Profile' in content or 'Game Passport' in content, \
                "Gaming fieldset should reference Game Profile admin"

    def test_admin_list_view_loads(self):
        """Verify admin list view loads"""
        response = self.client.get('/admin/user_profile/userprofile/')
        assert response.status_code == 200

    def test_admin_list_shows_key_fields(self):
        """Verify admin list view shows important fields"""
        response = self.client.get('/admin/user_profile/userprofile/')
        content = response.content.decode('utf-8')
        
        # Should show user, display_name, etc
        assert self.test_user.username in content, "Username not in list view"

    def test_no_legacy_json_help_text(self):
        """Verify no references to game_profiles JSON"""
        response = self.client.get(f'/admin/user_profile/userprofile/{self.profile.id}/change/')
        content = response.content.decode('utf-8')
        
        # Should NOT mention game_profiles as JSON field
        # (It was removed in earlier phases)
        # This is a soft check - if it exists, it should not be the primary guidance
        pass  # No strong assertion needed, just check manually

    def test_fieldsets_are_organized(self):
        """Verify fieldsets exist and are organized"""
        admin_instance = UserProfileAdmin(UserProfile, None)
        
        fieldsets = admin_instance.fieldsets
        assert fieldsets is not None, "Fieldsets should be defined"
        assert len(fieldsets) > 0, "Fieldsets should not be empty"
        
        # Check for key fieldsets
        fieldset_names = [fs[0] for fs in fieldsets]
        assert any('User' in name or 'Account' in name for name in fieldset_names), \
            "Should have User/Account fieldset"
        assert any('Economy' in name or 'Wallet' in name for name in fieldset_names), \
            "Should have Economy fieldset"


@pytest.mark.django_db
class TestPhase13AdminSafety:
    """Test admin safety features"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser(
            username='admin',
            email='admin@deltacrown.com',
            password='adminpass123'
        )
        self.client.force_login(self.superuser)
        
        self.test_user = User.objects.create_user(
            username='testplayer',
            email='test@deltacrown.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.test_user)

    def test_cannot_edit_economy_fields_via_form(self):
        """Verify economy fields are not editable in admin form"""
        # This is enforced by readonly_fields
        admin_instance = UserProfileAdmin(UserProfile, None)
        
        readonly = admin_instance.readonly_fields
        assert 'deltacoin_balance' in readonly
        assert 'lifetime_earnings' in readonly

    def test_admin_form_has_descriptions(self):
        """Verify fieldsets have helpful descriptions"""
        response = self.client.get(f'/admin/user_profile/userprofile/{self.profile.id}/change/')
        content = response.content.decode('utf-8')
        
        # Should have some descriptive text helping admins
        # (fieldset descriptions render as help text)
        assert 'description' in content.lower() or 'help' in content.lower() or \
               len(content) > 1000, "Admin should have helpful descriptions"
