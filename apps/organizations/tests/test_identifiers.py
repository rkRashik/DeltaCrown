"""
Tests for Organization modern identifiers (UUID and Public ID).

Verifies that uuid and public_id fields are properly generated, unique,
and collision-safe.
"""

import pytest
from django.db import IntegrityError
from django.contrib.auth import get_user_model

from apps.organizations.models import Organization
from apps.organizations.utils.ids import (
    generate_public_id,
    generate_team_public_id,
    is_valid_public_id_format,
)

User = get_user_model()


@pytest.mark.django_db
class TestOrganizationIdentifiers:
    """Test Organization UUID and public_id generation."""
    
    def test_creating_organization_generates_uuid(self):
        """New organizations automatically get a UUID."""
        user = User.objects.create_user(username='testceo', email='ceo@test.com', password='testpass')
        
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=user
        )
        
        assert org.uuid is not None
        assert str(org.uuid)  # Valid UUID format
    
    def test_creating_organization_generates_public_id(self):
        """New organizations automatically get a public_id."""
        user = User.objects.create_user(username='testceo', email='ceo@test.com', password='testpass')
        
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=user
        )
        
        assert org.public_id is not None
        assert org.public_id.startswith('ORG_')
        assert len(org.public_id) == 14  # ORG_ (4) + 10 chars
    
    def test_public_id_is_unique(self):
        """Each organization gets a unique public_id."""
        user = User.objects.create_user(username='testceo', email='ceo@test.com', password='testpass')
        
        org1 = Organization.objects.create(
            name='Org 1',
            slug='org-1',
            ceo=user
        )
        
        org2 = Organization.objects.create(
            name='Org 2',
            slug='org-2',
            ceo=user
        )
        
        assert org1.public_id != org2.public_id
    
    def test_uuid_is_unique(self):
        """Each organization gets a unique UUID."""
        user = User.objects.create_user(username='testceo', email='ceo@test.com', password='testpass')
        
        org1 = Organization.objects.create(
            name='Org 1',
            slug='org-1',
            ceo=user
        )
        
        org2 = Organization.objects.create(
            name='Org 2',
            slug='org-2',
            ceo=user
        )
        
        assert org1.uuid != org2.uuid
    
    def test_cannot_create_duplicate_public_id(self):
        """Database enforces public_id uniqueness."""
        user = User.objects.create_user(username='testceo', email='ceo@test.com', password='testpass')
        
        org1 = Organization.objects.create(
            name='Org 1',
            slug='org-1',
            ceo=user
        )
        
        # Try to create another org with same public_id
        with pytest.raises(IntegrityError):
            Organization.objects.create(
                name='Org 2',
                slug='org-2',
                ceo=user,
                public_id=org1.public_id  # Duplicate!
            )
    
    def test_multiple_organizations_have_distinct_identifiers(self):
        """Creating 100 organizations should generate 100 unique IDs."""
        user = User.objects.create_user(username='testceo', email='ceo@test.com', password='testpass')
        
        # Create multiple organizations
        orgs = []
        for i in range(20):  # Use 20 for speed (collision probability still ~0)
            org = Organization.objects.create(
                name=f'Org {i}',
                slug=f'org-{i}',
                ceo=user
            )
            orgs.append(org)
        
        # Collect all public_ids and uuids
        public_ids = [org.public_id for org in orgs]
        uuids = [org.uuid for org in orgs]
        
        # Check all unique
        assert len(set(public_ids)) == len(public_ids), "Duplicate public_ids found"
        assert len(set(uuids)) == len(uuids), "Duplicate UUIDs found"


class TestPublicIDGenerator:
    """Test public_id generation utility functions."""
    
    def test_generate_public_id_format(self):
        """Generated IDs match expected format."""
        public_id = generate_public_id(prefix="ORG", length=10)
        
        assert public_id.startswith("ORG_")
        assert len(public_id) == 14  # ORG_ (4) + 10 chars
    
    def test_generate_public_id_uses_base32_alphabet(self):
        """Generated IDs only use Base32 characters (no 0/O/1/I/L)."""
        # Generate many IDs to test randomness
        for _ in range(100):
            public_id = generate_public_id(prefix="ORG", length=10)
            random_part = public_id.split("_")[1]
            
            # Check no confusable characters
            assert '0' not in random_part
            assert 'O' not in random_part
            assert '1' not in random_part
            assert 'I' not in random_part
            assert 'L' not in random_part
            
            # Check only valid Base32
            for char in random_part:
                assert char.isupper() or char.isdigit()
                if char.isdigit():
                    assert char in '23456789'
    
    def test_generate_team_public_id(self):
        """Team-specific generator uses TEAM prefix."""
        team_id = generate_team_public_id(length=10)
        
        assert team_id.startswith("TEAM_")
        assert len(team_id) == 15  # TEAM_ (5) + 10 chars
    
    def test_generate_public_id_collision_probability_low(self):
        """Generating many IDs should produce all unique values."""
        ids = set()
        for _ in range(1000):
            public_id = generate_public_id(prefix="TEST", length=10)
            ids.add(public_id)
        
        # All should be unique (collision probability: ~1 in 3.6 quadrillion)
        assert len(ids) == 1000
    
    def test_is_valid_public_id_format_accepts_valid(self):
        """Validation accepts correctly formatted IDs."""
        assert is_valid_public_id_format("ORG_A7K2N9Q5B3") is True
        assert is_valid_public_id_format("ORG_XYZ23456AB") is True
    
    def test_is_valid_public_id_format_rejects_invalid(self):
        """Validation rejects incorrectly formatted IDs."""
        assert is_valid_public_id_format("ORG_123") is False  # Too short
        assert is_valid_public_id_format("ORG_A7K2N9Q5B3X") is False  # Too long
        assert is_valid_public_id_format("TEAM_A7K2N9Q5B3") is False  # Wrong prefix
        assert is_valid_public_id_format("ORG_A7K2N9Q5B0") is False  # Contains 0
        assert is_valid_public_id_format("ORG_A7K2N9Q5BO") is False  # Contains O
        assert is_valid_public_id_format("ORG-A7K2N9Q5B3") is False  # Wrong separator
        assert is_valid_public_id_format("") is False  # Empty
        assert is_valid_public_id_format(None) is False  # None


@pytest.mark.django_db
class TestAdminPublicIDDisplay:
    """Test that admin shows public_id correctly."""
    
    def test_admin_includes_public_id_field(self):
        """OrganizationAdmin fieldsets include public_id."""
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization
        
        admin_instance = OrganizationAdmin(Organization, None)
        
        # Collect all fields from fieldsets
        all_fields = []
        for fieldset in admin_instance.fieldsets:
            all_fields.extend(fieldset[1]['fields'])
        
        assert 'public_id' in all_fields
    
    def test_admin_readonly_fields_includes_public_id(self):
        """public_id should be read-only in admin."""
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization
        
        admin_instance = OrganizationAdmin(Organization, None)
        
        assert 'public_id' in admin_instance.readonly_fields
    
    def test_admin_does_not_show_twitter(self):
        """Admin must NOT display twitter field."""
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization
        
        admin_instance = OrganizationAdmin(Organization, None)
        
        # Collect all fields from fieldsets
        all_fields = []
        for fieldset in admin_instance.fieldsets:
            all_fields.extend(fieldset[1]['fields'])
        
        assert 'twitter' not in all_fields
    
    def test_admin_list_display_shows_public_id(self):
        """Admin list view displays public_id."""
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization
        
        admin_instance = OrganizationAdmin(Organization, None)
        
        # Should have public_id_display method in list_display
        assert 'public_id_display' in admin_instance.list_display


@pytest.mark.django_db
class TestBackfillMigration:
    """Test that existing organizations get backfilled with identifiers."""
    
    def test_organization_without_public_id_gets_generated_on_save(self):
        """Saving an org without public_id triggers generation."""
        user = User.objects.create_user(username='testceo', email='ceo@test.com', password='testpass')
        
        # Create org with explicit None for public_id (simulates migration state)
        org = Organization(
            name='Legacy Org',
            slug='legacy-org',
            ceo=user,
            public_id=None,
            uuid=None
        )
        org.save()
        
        # After save, identifiers should be generated
        assert org.public_id is not None
        assert org.public_id.startswith('ORG_')
        assert org.uuid is not None
