"""
Tests for OrganizationAdmin CEO field widget configuration.

Verifies that CEO field uses autocomplete (not raw_id) to show user-friendly labels.
"""

import pytest
from django.contrib.admin.sites import site

from apps.organizations.models import Organization


class TestOrganizationAdminCEOWidget:
    """Test CEO field uses autocomplete widget (no numeric ID prefix)."""
    
    def test_admin_uses_autocomplete_for_ceo(self):
        """OrganizationAdmin.autocomplete_fields contains 'ceo'."""
        admin_instance = site._registry[Organization]
        
        assert hasattr(admin_instance, 'autocomplete_fields'), \
            "OrganizationAdmin must define autocomplete_fields"
        
        assert 'ceo' in admin_instance.autocomplete_fields, \
            "CEO must be in autocomplete_fields to show user-friendly labels"
    
    def test_admin_does_not_use_raw_id_for_ceo(self):
        """OrganizationAdmin.raw_id_fields does NOT contain 'ceo'."""
        admin_instance = site._registry[Organization]
        
        # raw_id_fields may not exist (which is fine)
        if hasattr(admin_instance, 'raw_id_fields'):
            assert 'ceo' not in admin_instance.raw_id_fields, \
                "CEO must NOT be in raw_id_fields (shows numeric ID prefix)"
    
    def test_user_admin_has_search_fields_for_autocomplete(self):
        """UserAdmin has search_fields to enable autocomplete."""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user_admin = site._registry[User]
        
        assert hasattr(user_admin, 'search_fields'), \
            "UserAdmin must define search_fields for autocomplete to work"
        
        search_fields = user_admin.search_fields
        assert 'username' in search_fields or any('username' in field for field in search_fields), \
            "UserAdmin.search_fields must include username"
        
        # Should also have email for better search
        assert 'email' in search_fields or any('email' in field for field in search_fields), \
            "UserAdmin.search_fields should include email"
