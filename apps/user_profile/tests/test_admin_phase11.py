"""
UP-PHASE11: Django Admin Tests

Tests verify admin panel configuration:
- Economy fields are readonly (prevent data corruption)
- public_id is visible and readonly
- Help text updated (no legacy references)
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.user_profile.admin.users import UserProfileAdmin
from apps.user_profile.models import UserProfile

User = get_user_model()

pytestmark = pytest.mark.django_db


class AdminReadonlyFieldsTestCase(TestCase):
    """
    Tests for admin panel readonly field configuration.
    Verifies economy fields cannot be edited.
    """
    
    def setUp(self):
        self.client = Client()
        
        # Create superuser
        self.admin_user = User.objects.create_superuser(
            username='admin_phase11',
            email='admin@example.com',
            password='admin123'
        )
        self.client.login(username='admin_phase11', password='admin123')
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser_admin',
            email='test@example.com',
            password='test123'
        )
        self.profile = self.user.profile
    
    def test_economy_fields_in_readonly_fields(self):
        """
        PHASE11-C: Economy fields are in readonly_fields list.
        Prevents admin from manually editing wallet balances.
        """
        admin_instance = UserProfileAdmin(UserProfile, None)
        readonly_fields = admin_instance.readonly_fields
        
        # Assert economy fields are readonly
        assert 'deltacoin_balance' in readonly_fields, \
            "deltacoin_balance must be readonly (economy-owned)"
        assert 'lifetime_earnings' in readonly_fields, \
            "lifetime_earnings must be readonly (economy-owned)"
        
        # Assert other critical fields remain readonly
        assert 'uuid' in readonly_fields
        assert 'public_id' in readonly_fields
        assert 'slug' in readonly_fields
    
    def test_economy_fields_not_editable_in_form(self):
        """
        PHASE11-C: Economy fields render as readonly in admin form.
        Verifies fields are disabled/not in input elements.
        """
        url = reverse('admin:user_profile_userprofile_change', args=[self.profile.pk])
        response = self.client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify deltacoin_balance is NOT an input field
        # (readonly fields render as text, not <input>)
        assert '<input' not in content or \
               'name="deltacoin_balance"' not in content, \
               "deltacoin_balance should not be an editable input"
        
        # Verify lifetime_earnings is NOT an input field
        assert '<input' not in content or \
               'name="lifetime_earnings"' not in content, \
               "lifetime_earnings should not be an editable input"
    
    def test_economy_fieldset_has_warning(self):
        """
        PHASE11-C: Economy fieldset displays warning about readonly nature.
        Prevents accidental edits by admins.
        """
        url = reverse('admin:user_profile_userprofile_change', args=[self.profile.pk])
        response = self.client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify warning message exists
        assert 'Economy' in content or '💰' in content, \
            "Economy fieldset should be visible"
        assert 'WARNING' in content or 'Read-Only' in content, \
            "Economy fieldset should have warning message"
        assert 'Economy app' in content or 'economy-owned' in content, \
            "Warning should explain economy app owns these fields"
    
    def test_gaming_fieldset_updated(self):
        """
        PHASE11-C: Gaming fieldset has updated help text (no legacy refs).
        Verifies old "game_profiles JSON" reference is removed.
        """
        admin_instance = UserProfileAdmin(UserProfile, None)
        fieldsets = admin_instance.fieldsets
        
        gaming_fieldset = None
        for name, options in fieldsets:
            if 'Gaming' in name or 'gaming' in name.lower():
                gaming_fieldset = options
                break
        
        assert gaming_fieldset is not None, "Gaming fieldset not found"
        
        description = gaming_fieldset.get('description', '')
        
        # Assert old reference removed
        assert 'game_profiles JSON' not in description, \
            "Old 'game_profiles JSON' reference should be removed"
        
        # Assert new reference exists
        assert 'Game Profile' in description or 'Passport' in description, \
            "New reference to Game Profile admin should exist"
    
    def test_public_id_visible_in_admin(self):
        """
        PHASE11-C: public_id is visible in admin form.
        Verifies public_id is in readonly_fields (visible).
        """
        admin_instance = UserProfileAdmin(UserProfile, None)
        readonly_fields = admin_instance.readonly_fields
        
        assert 'public_id' in readonly_fields, \
            "public_id must be in readonly_fields to be visible"
        
        # Verify it renders in the form
        url = reverse('admin:user_profile_userprofile_change', args=[self.profile.pk])
        response = self.client.get(url)
        
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        
        # Verify public_id field is rendered
        assert 'public_id' in content or 'Public ID' in content, \
            "public_id should be visible in admin form"
        assert str(self.profile.public_id) in content, \
            "Actual public_id value should be displayed"


class AdminFieldsetConfigTestCase(TestCase):
    """
    Tests for admin fieldset configuration and organization.
    """
    
    def test_economy_fieldset_title_indicates_readonly(self):
        """
        PHASE11-C: Economy fieldset title clearly indicates readonly nature.
        """
        admin_instance = UserProfileAdmin(UserProfile, None)
        fieldsets = admin_instance.fieldsets
        
        economy_fieldset_name = None
        for name, options in fieldsets:
            if 'deltacoin_balance' in options.get('fields', []):
                economy_fieldset_name = name
                break
        
        assert economy_fieldset_name is not None, "Economy fieldset not found"
        
        # Verify title indicates readonly
        assert 'Read-Only' in economy_fieldset_name or \
               'read-only' in economy_fieldset_name.lower() or \
               '💰' in economy_fieldset_name, \
               f"Economy fieldset title should indicate readonly: {economy_fieldset_name}"
    
    def test_gaming_fieldset_collapsed_by_default(self):
        """
        PHASE11-C: Gaming fieldset is collapsed (low priority).
        """
        admin_instance = UserProfileAdmin(UserProfile, None)
        fieldsets = admin_instance.fieldsets
        
        gaming_fieldset = None
        for name, options in fieldsets:
            if 'Gaming' in name or 'gaming' in name.lower():
                gaming_fieldset = options
                break
        
        assert gaming_fieldset is not None, "Gaming fieldset not found"
        
        classes = gaming_fieldset.get('classes', [])
        assert 'collapse' in classes, \
            "Gaming fieldset should have 'collapse' class (low priority)"
