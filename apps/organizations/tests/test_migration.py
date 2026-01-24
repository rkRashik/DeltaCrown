"""
Tests for TeamMigrationMap model.

Coverage:
- Migration map creation
- Legacy ID and vNext ID constraints
- Class methods: get_vnext_id, get_legacy_id, resolve_legacy_url
- Uniqueness constraints

Performance: This file should run in <2 seconds.
"""
import pytest
from django.db import IntegrityError

from apps.organizations.models import TeamMigrationMap
from apps.organizations.tests.factories import (
    TeamMigrationMapFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestTeamMigrationMap:
    """Test suite for TeamMigrationMap model."""
    
    def test_create_migration_map(self):
        """Test creating a migration map record."""
        migration = TeamMigrationMap.objects.create(
            legacy_team_id=12345,
            vnext_team_id=1,
            legacy_slug="legacy-team-slug",
        )
        
        assert migration.pk is not None
        assert migration.legacy_team_id == 12345
        assert migration.vnext_team_id == 1
        assert migration.legacy_slug == "legacy-team-slug"
    
    def test_unique_constraint_legacy_team_id(self):
        """Test that legacy_team_id must be unique."""
        TeamMigrationMapFactory.create(legacy_team_id=100)
        
        # Attempting to create second mapping with same legacy_team_id should fail
        with pytest.raises(IntegrityError):
            TeamMigrationMap.objects.create(
                legacy_team_id=100,  # Duplicate
                vnext_team_id=2,
                legacy_slug="different-slug",
            )
    
    def test_unique_constraint_vnext_team_id(self):
        """Test that vnext_team_id must be unique."""
        TeamMigrationMapFactory.create(vnext_team_id=1)
        
        # Attempting to create second mapping with same vnext_team_id should fail
        with pytest.raises(IntegrityError):
            TeamMigrationMap.objects.create(
                legacy_team_id=200,
                vnext_team_id=1,  # Duplicate
                legacy_slug="another-slug",
            )
    
    def test_legacy_slug_uniqueness(self):
        """Test that legacy_slug must be unique."""
        TeamMigrationMapFactory.create(legacy_slug="sentinels")
        
        # Attempting to create second mapping with same slug should fail
        with pytest.raises(IntegrityError):
            TeamMigrationMap.objects.create(
                legacy_team_id=300,
                vnext_team_id=3,
                legacy_slug="sentinels",  # Duplicate
            )
    
    def test_str_representation(self):
        """Test string representation of TeamMigrationMap."""
        migration = TeamMigrationMapFactory.create(
            legacy_team_id=456,
            vnext_team_id=789,
        )
        
        expected = "Legacy Team 456 → vNext Team 789"
        assert str(migration) == expected
    
    def test_get_vnext_id_found(self):
        """Test get_vnext_id() class method returns correct vNext ID."""
        migration = TeamMigrationMapFactory.create(
            legacy_team_id=12345,
            vnext_team_id=67890,
        )
        
        vnext_id = TeamMigrationMap.get_vnext_id(legacy_id=12345)
        
        assert vnext_id == 67890
    
    def test_get_vnext_id_not_found(self):
        """Test get_vnext_id() returns None when mapping doesn't exist."""
        vnext_id = TeamMigrationMap.get_vnext_id(legacy_id=99999)
        
        assert vnext_id is None
    
    def test_get_legacy_id_found(self):
        """Test get_legacy_id() class method returns correct legacy ID."""
        migration = TeamMigrationMapFactory.create(
            legacy_team_id=11111,
            vnext_team_id=22222,
        )
        
        legacy_id = TeamMigrationMap.get_legacy_id(vnext_id=22222)
        
        assert legacy_id == 11111
    
    def test_get_legacy_id_not_found(self):
        """Test get_legacy_id() returns None when mapping doesn't exist."""
        legacy_id = TeamMigrationMap.get_legacy_id(vnext_id=88888)
        
        assert legacy_id is None
    
    def test_resolve_legacy_url_found(self):
        """Test resolve_legacy_url() returns vNext team ID for legacy slug."""
        migration = TeamMigrationMapFactory.create(
            legacy_team_id=100,
            vnext_team_id=200,
            legacy_slug="cloud9-valorant",
        )
        
        vnext_id = TeamMigrationMap.resolve_legacy_url(legacy_slug="cloud9-valorant")
        
        assert vnext_id == 200
    
    def test_resolve_legacy_url_not_found(self):
        """Test resolve_legacy_url() returns None when slug doesn't exist."""
        vnext_id = TeamMigrationMap.resolve_legacy_url(legacy_slug="nonexistent-slug")
        
        assert vnext_id is None
    
    def test_verified_defaults_to_false(self):
        """Test that verified field defaults to False."""
        migration = TeamMigrationMapFactory.create()
        
        assert migration.verified is False
    
    def test_migrated_by_nullable(self):
        """Test that migrated_by field can be null."""
        migration = TeamMigrationMapFactory.create(migrated_by=None)
        
        assert migration.migrated_by is None
    
    def test_migrated_by_with_user(self):
        """Test setting migrated_by to a user."""
        user = UserFactory.create(username="admin")
        migration = TeamMigrationMapFactory.create(migrated_by=user)
        
        assert migration.migrated_by == user
    
    def test_migration_date_auto_set(self):
        """Test that migration_date is automatically set."""
        migration = TeamMigrationMapFactory.create()
        
        assert migration.migration_date is not None
    
    def test_verification_notes_nullable(self):
        """Test that verification_notes can be null."""
        migration = TeamMigrationMapFactory.create(verification_notes=None)
        
        assert migration.verification_notes is None
    
    def test_verification_notes_with_text(self):
        """Test setting verification_notes."""
        migration = TeamMigrationMapFactory.create(
            verified=True,
            verification_notes="Verified by manual inspection",
        )
        
        assert migration.verification_notes == "Verified by manual inspection"
    
    def test_bidirectional_lookup(self):
        """Test bidirectional lookup between legacy and vNext IDs."""
        migration = TeamMigrationMapFactory.create(
            legacy_team_id=555,
            vnext_team_id=999,
        )
        
        # Forward lookup
        vnext_id = TeamMigrationMap.get_vnext_id(legacy_id=555)
        assert vnext_id == 999
        
        # Reverse lookup
        legacy_id = TeamMigrationMap.get_legacy_id(vnext_id=999)
        assert legacy_id == 555
    
    def test_multiple_migrations_independent(self):
        """Test that multiple migration records are independent."""
        migration1 = TeamMigrationMapFactory.create(
            legacy_team_id=100,
            vnext_team_id=200,
            legacy_slug="team-a",
        )
        
        migration2 = TeamMigrationMapFactory.create(
            legacy_team_id=300,
            vnext_team_id=400,
            legacy_slug="team-b",
        )
        
        # Both lookups should work independently
        assert TeamMigrationMap.get_vnext_id(legacy_id=100) == 200
        assert TeamMigrationMap.get_vnext_id(legacy_id=300) == 400
        assert TeamMigrationMap.resolve_legacy_url(legacy_slug="team-a") == 200
        assert TeamMigrationMap.resolve_legacy_url(legacy_slug="team-b") == 400
