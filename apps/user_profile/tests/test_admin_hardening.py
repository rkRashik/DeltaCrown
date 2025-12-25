"""
Admin Hardening Tests - Production Grade

Tests for:
1. Game Passport models appear in /admin/user_profile/
2. UserProfile admin does NOT show Legacy Privacy Flags fieldset
3. GameProfile change page loads without errors
4. GameProfileAlias admin is read-only
5. GameProfileConfig singleton behavior
"""
import pytest
from django.contrib.auth import get_user_model
from django.contrib.admin.sites import site as admin_site
from django.test import Client, TestCase
from django.urls import reverse

from apps.user_profile.models import (
    UserProfile,
    GameProfile,
    GameProfileAlias,
    GameProfileConfig,
)
# Admin classes are registered via decorators, we just need to check admin_site
from django.contrib.admin.sites import site as admin_site

User = get_user_model()


@pytest.mark.django_db
class TestAdminRegistration:
    """Test that all Game Passport models are properly registered"""
    
    def test_gameprofile_registered_in_admin(self):
        """GameProfile should be registered and visible in admin"""
        assert GameProfile in admin_site._registry
    
    def test_gameprofilealias_registered_in_admin(self):
        """GameProfileAlias should be registered and visible in admin"""
        assert GameProfileAlias in admin_site._registry
    
    def test_gameprofileconfig_registered_in_admin(self):
        """GameProfileConfig should be registered and visible in admin"""
        assert GameProfileConfig in admin_site._registry
    
    def test_userprofile_registered_in_admin(self):
        """UserProfile should be registered with correct admin"""
        assert UserProfile in admin_site._registry


@pytest.mark.django_db
class TestUserProfileAdminCleanup:
    """Test that legacy privacy flags fieldset has been removed"""
    
    def test_legacy_privacy_fieldset_removed(self):
        """UserProfileAdmin should NOT have 'Privacy (Legacy Booleans' fieldset"""
        admin_instance = admin_site._registry[UserProfile]
        fieldsets = admin_instance.fieldsets
        
        # Check that no fieldset contains "Legacy" privacy flags
        for fieldset_name, fieldset_data in fieldsets:
            assert 'Legacy' not in fieldset_name or 'Privacy' not in fieldset_name, \
                f"Found legacy privacy fieldset: {fieldset_name}"
    
    def test_legacy_privacy_fields_not_in_fieldsets(self):
        """Legacy privacy boolean fields should not be in any fieldset"""
        admin_instance = admin_site._registry[UserProfile]
        fieldsets = admin_instance.fieldsets
        
        legacy_fields = [
            'is_private', 'show_email', 'show_phone', 'show_socials',
            'show_address', 'show_age', 'show_gender', 'show_country', 'show_real_name'
        ]
        
        # Collect all fields from all fieldsets
        all_fields = []
        for fieldset_name, fieldset_data in fieldsets:
            if 'fields' in fieldset_data:
                all_fields.extend(fieldset_data['fields'])
        
        # Check that legacy fields are NOT in fieldsets
        for legacy_field in legacy_fields:
            assert legacy_field not in all_fields, \
                f"Legacy privacy field '{legacy_field}' should not be in UserProfile admin fieldsets"


@pytest.mark.django_db
class TestAdminPages:
    """Test that admin pages load without errors"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create admin user and test data"""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.client = Client()
        self.client.force_login(self.admin_user)
        
        # Create test user with profile
        self.test_user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='pass123'
        )
        self.profile = UserProfile.objects.get(user=self.test_user)
    
    def test_userprofile_admin_index_loads(self):
        """Admin index for user_profile app should load"""
        url = reverse('admin:app_list', args=['user_profile'])
        response = self.client.get(url)
        assert response.status_code == 200
    
    def test_userprofile_admin_changelist_loads(self):
        """UserProfile changelist should load"""
        url = reverse('admin:user_profile_userprofile_changelist')
        response = self.client.get(url)
        assert response.status_code == 200
    
    def test_userprofile_admin_change_page_loads(self):
        """UserProfile change page should load without Legacy Privacy fieldset"""
        url = reverse('admin:user_profile_userprofile_change', args=[self.profile.pk])
        response = self.client.get(url)
        assert response.status_code == 200
        
        # Check that Legacy Privacy text is NOT in the page
        content = response.content.decode('utf-8')
        assert 'Privacy (Legacy Booleans' not in content, \
            "Legacy Privacy Flags fieldset should be removed"
    
    def test_gameprofile_admin_changelist_loads(self):
        """GameProfile changelist should load"""
        url = reverse('admin:user_profile_gameprofile_changelist')
        response = self.client.get(url)
        assert response.status_code == 200
    
    def test_gameprofile_admin_change_page_loads(self):
        """GameProfile change page should load"""
        # Create a game passport
        passport = GameProfile.objects.create(
            user=self.test_user,
            game='valorant',
            in_game_name='TestPlayer#VAL',
            visibility='PUBLIC'
        )
        
        url = reverse('admin:user_profile_gameprofile_change', args=[passport.pk])
        response = self.client.get(url)
        assert response.status_code == 200
    
    def test_gameprofilealias_admin_changelist_loads(self):
        """GameProfileAlias changelist should load"""
        url = reverse('admin:user_profile_gameprofilealias_changelist')
        response = self.client.get(url)
        assert response.status_code == 200
    
    def test_gameprofileconfig_admin_loads(self):
        """GameProfileConfig admin should load (singleton)"""
        # Create config if doesn't exist
        config, created = GameProfileConfig.objects.get_or_create(
            pk=1,
            defaults={'cooldown_days': 30}
        )
        
        url = reverse('admin:user_profile_gameprofileconfig_change', args=[config.pk])
        response = self.client.get(url)
        assert response.status_code == 200


@pytest.mark.django_db
class TestGameProfileAliasAdminPermissions:
    """Test that GameProfileAlias admin is properly read-only"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create admin user"""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_instance = admin_site._registry[GameProfileAlias]
        self.request = type('Request', (), {'user': self.admin_user})()
    
    def test_gameprofilealias_no_add_permission(self):
        """Aliases should not be manually creatable"""
        assert not self.admin_instance.has_add_permission(self.request)
    
    def test_gameprofilealias_no_change_permission(self):
        """Aliases should not be editable"""
        assert not self.admin_instance.has_change_permission(self.request)
    
    def test_gameprofilealias_delete_requires_superuser(self):
        """Aliases can only be deleted by superuser"""
        assert self.admin_instance.has_delete_permission(self.request)
        
        # Regular staff should not be able to delete
        regular_staff = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='pass123',
            is_staff=True,
            is_superuser=False
        )
        staff_request = type('Request', (), {'user': regular_staff})()
        assert not self.admin_instance.has_delete_permission(staff_request)


@pytest.mark.django_db
class TestGameProfileConfigSingleton:
    """Test GameProfileConfig singleton behavior"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Create admin user"""
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.admin_instance = admin_site._registry[GameProfileConfig]
        self.request = type('Request', (), {'user': self.admin_user})()
    
    def test_config_no_add_after_creation(self):
        """Cannot create new config if one exists"""
        # Create config
        GameProfileConfig.objects.create(pk=1, cooldown_days=30)
        
        # Should not allow add
        assert not self.admin_instance.has_add_permission(self.request)
    
    def test_config_no_delete_permission(self):
        """Config should not be deletable"""
        assert not self.admin_instance.has_delete_permission(self.request)
    
    def test_config_queryset_only_singleton(self):
        """Queryset should only show singleton config"""
        # Create config
        config = GameProfileConfig.objects.create(pk=1, cooldown_days=30)
        
        qs = self.admin_instance.get_queryset(self.request)
        assert qs.count() == 1
        assert qs.first().pk == 1
