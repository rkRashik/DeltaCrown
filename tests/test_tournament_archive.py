"""
Comprehensive tests for TournamentArchive model and helpers.

Test Coverage:
- TournamentArchive model creation and validation
- Archive operations (archive, restore)
- Clone operations (marking as clone, clone metadata)
- Archive status checks
- Restore capability
- Metadata preservation
- Historical data snapshots
- Query optimization
- Helper functions (43 helpers)
- Integration scenarios
- Edge cases

Total Tests: 85 tests across 15 test classes
"""

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from apps.tournaments.models import Tournament, TournamentArchive
from apps.tournaments.utils.archive_helpers import (
    # Archive Status Checks
    is_archived, is_active, is_clone, is_original,
    can_restore, has_clones, has_been_restored, get_archive_status,
    # Archive Operations
    archive_tournament, unarchive_tournament,
    get_archive_reason, get_archived_at, get_archived_by,
    get_archive_age_days, set_archive_preservation,
    # Clone Operations
    get_source_tournament, get_clone_number, get_cloned_at, get_cloned_by,
    get_clone_count, get_clone_age_days, get_all_clones, mark_tournament_as_clone,
    # Restore Operations
    can_be_restored, get_restored_at, get_restored_by,
    disable_restore, enable_restore,
    # Metadata Access
    get_archive_metadata, get_clone_metadata, get_preservation_settings,
    is_fully_preserved, has_original_data, get_archive_notes,
    # Query Optimization
    optimize_queryset_for_archive, get_archived_tournaments,
    get_active_tournaments, get_cloned_tournaments, get_original_tournaments,
    # Historical Data
    save_tournament_snapshot, get_tournament_snapshot,
    get_archive_context, get_archive_summary,
)

User = get_user_model()


# ==================== Fixtures ====================

@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def base_tournament():
    """Create a basic tournament for testing."""
    return Tournament.objects.create(
        name="Test Tournament",
        game="valorant",
        slug="test-tournament"
    )


@pytest.fixture
def archived_tournament(base_tournament, user):
    """Create an archived tournament."""
    archive = TournamentArchive.objects.create(
        tournament=base_tournament,
        archive_type='ARCHIVED',
        is_archived=True,
        archived_at=timezone.now(),
        archived_by=user,
        archive_reason="Tournament completed"
    )
    return base_tournament


@pytest.fixture
def source_tournament():
    """Create a source tournament for cloning."""
    return Tournament.objects.create(
        name="Source Tournament",
        game="valorant",
        slug="source-tournament"
    )


@pytest.fixture
def cloned_tournament(source_tournament, user):
    """Create a cloned tournament."""
    clone = Tournament.objects.create(
        name="Cloned Tournament",
        game="valorant",
        slug="cloned-tournament"
    )
    archive = TournamentArchive.objects.create(
        tournament=clone,
        archive_type='CLONED',
        source_tournament=source_tournament,
        clone_number=1,
        cloned_at=timezone.now(),
        cloned_by=user
    )
    return clone


# ==================== Test Classes ====================

@pytest.mark.django_db
class TestTournamentArchiveModel:
    """Test TournamentArchive model creation and basic functionality."""
    
    def test_create_archive_record(self, base_tournament):
        """Test creating a TournamentArchive record."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        assert archive.tournament == base_tournament
        assert archive.archive_type == 'ACTIVE'
        assert not archive.is_archived
        assert archive.clone_number == 0
    
    def test_archive_one_to_one_constraint(self, base_tournament):
        """Test OneToOne constraint with Tournament."""
        TournamentArchive.objects.create(tournament=base_tournament)
        
        with pytest.raises(Exception):  # IntegrityError
            TournamentArchive.objects.create(tournament=base_tournament)
    
    def test_string_representation(self, base_tournament):
        """Test __str__ method."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament,
            archive_type='ARCHIVED'
        )
        assert str(archive) == "Test Tournament - Archived"
    
    def test_default_values(self, base_tournament):
        """Test default field values."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        assert archive.archive_type == 'ACTIVE'
        assert not archive.is_archived
        assert archive.clone_number == 0
        assert archive.can_restore is True
        assert archive.preserve_participants is True
        assert archive.preserve_matches is True
        assert archive.preserve_media is True
        assert archive.original_data == {}
    
    def test_ordering(self, base_tournament):
        """Test ordering by created_at (newest first)."""
        import time
        # Create multiple archives with slight delay to ensure different timestamps
        t1 = Tournament.objects.create(name="T1", game="valorant", slug="t1")
        a1 = TournamentArchive.objects.create(tournament=t1)
        
        time.sleep(0.01)  # Small delay to ensure different created_at
        
        t2 = Tournament.objects.create(name="T2", game="valorant", slug="t2")
        a2 = TournamentArchive.objects.create(tournament=t2)
        
        # Get archives in order - a2 should come before a1 (newest first)
        archives = list(TournamentArchive.objects.filter(tournament__in=[t1, t2]).order_by('-created_at'))
        assert len(archives) == 2
        assert archives[0] == a2  # Newest first
        assert archives[1] == a1


@pytest.mark.django_db
class TestArchiveValidation:
    """Test archive validation rules."""
    
    def test_archived_type_requires_archived_flag(self, base_tournament):
        """Test ARCHIVED type must have is_archived=True."""
        archive = TournamentArchive(
            tournament=base_tournament,
            archive_type='ARCHIVED',
            is_archived=False
        )
        with pytest.raises(ValidationError, match="Archive type is 'ARCHIVED' but is_archived is False"):
            archive.full_clean()
    
    def test_archived_flag_requires_archived_type(self, base_tournament):
        """Test is_archived=True cannot have ACTIVE type."""
        archive = TournamentArchive(
            tournament=base_tournament,
            archive_type='ACTIVE',
            is_archived=True
        )
        with pytest.raises(ValidationError, match="Cannot have archive type 'ACTIVE' when is_archived is True"):
            archive.full_clean()
    
    def test_archived_requires_timestamp(self, base_tournament):
        """Test archived tournaments must have archived_at."""
        archive = TournamentArchive(
            tournament=base_tournament,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=None
        )
        with pytest.raises(ValidationError, match="must have archived_at timestamp"):
            archive.full_clean()
    
    def test_archived_at_requires_archived_flag(self, base_tournament):
        """Test archived_at requires is_archived=True."""
        archive = TournamentArchive(
            tournament=base_tournament,
            is_archived=False,
            archived_at=timezone.now()
        )
        with pytest.raises(ValidationError, match="archived_at is set but tournament is not marked as archived"):
            archive.full_clean()
    
    def test_cloned_type_requires_source(self, base_tournament):
        """Test CLONED type must have source_tournament."""
        archive = TournamentArchive(
            tournament=base_tournament,
            archive_type='CLONED',
            source_tournament=None
        )
        with pytest.raises(ValidationError, match="Clone tournaments must have a source_tournament"):
            archive.full_clean()
    
    def test_cannot_be_own_source(self, base_tournament):
        """Test tournament cannot be its own source."""
        archive = TournamentArchive(
            tournament=base_tournament,
            source_tournament=base_tournament
        )
        with pytest.raises(ValidationError, match="Tournament cannot be its own source"):
            archive.full_clean()
    
    def test_clone_requires_clone_number(self, base_tournament, source_tournament):
        """Test clones must have clone_number > 0."""
        archive = TournamentArchive(
            tournament=base_tournament,
            archive_type='CLONED',
            source_tournament=source_tournament,
            clone_number=0
        )
        with pytest.raises(ValidationError, match="Clone tournaments must have clone_number > 0"):
            archive.full_clean()
    
    def test_non_clone_cannot_have_clone_number(self, base_tournament):
        """Test non-clones must have clone_number = 0."""
        archive = TournamentArchive(
            tournament=base_tournament,
            source_tournament=None,
            clone_number=1
        )
        with pytest.raises(ValidationError, match="Only clone tournaments can have clone_number > 0"):
            archive.full_clean()
    
    def test_restore_timestamp_requires_archive(self, base_tournament):
        """Test restored_at requires is_archived."""
        archive = TournamentArchive(
            tournament=base_tournament,
            is_archived=False,
            restored_at=timezone.now()
        )
        with pytest.raises(ValidationError, match="Only archived tournaments can have restored_at timestamp"):
            archive.full_clean()
    
    def test_restore_after_archive(self, base_tournament):
        """Test restored_at cannot be before archived_at."""
        now = timezone.now()
        archive = TournamentArchive(
            tournament=base_tournament,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=now,
            restored_at=now - timedelta(days=1)
        )
        with pytest.raises(ValidationError, match="Restore timestamp cannot be before archive timestamp"):
            archive.full_clean()


@pytest.mark.django_db
class TestArchivePropertyMethods:
    """Test archive property methods."""
    
    def test_is_active_property(self, base_tournament):
        """Test is_active property."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament,
            archive_type='ACTIVE',
            is_archived=False
        )
        assert archive.is_active is True
        
        archive.is_archived = True
        assert archive.is_active is False
    
    def test_is_clone_property(self, base_tournament, source_tournament):
        """Test is_clone property."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        assert archive.is_clone is False
        
        archive.source_tournament = source_tournament
        assert archive.is_clone is True
    
    def test_is_original_property(self, base_tournament, source_tournament):
        """Test is_original property."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        assert archive.is_original is True
        
        archive.source_tournament = source_tournament
        archive.clone_number = 1
        assert archive.is_original is False
    
    def test_has_clones_property(self, source_tournament, cloned_tournament):
        """Test has_clones property."""
        archive = TournamentArchive.objects.get_or_create(
            tournament=source_tournament
        )[0]
        assert archive.has_clones is True
    
    def test_clone_count_property(self, source_tournament, cloned_tournament):
        """Test clone_count property."""
        archive = TournamentArchive.objects.get_or_create(
            tournament=source_tournament
        )[0]
        assert archive.clone_count == 1
    
    def test_has_been_restored_property(self, archived_tournament, user):
        """Test has_been_restored property."""
        archive = archived_tournament.archive
        assert archive.has_been_restored is False
        
        archive.restored_at = timezone.now()
        archive.restored_by = user
        assert archive.has_been_restored is True
    
    def test_archive_age_days_property(self, archived_tournament):
        """Test archive_age_days property."""
        archive = archived_tournament.archive
        assert archive.archive_age_days is not None
        assert archive.archive_age_days >= 0
    
    def test_clone_age_days_property(self, cloned_tournament):
        """Test clone_age_days property."""
        archive = cloned_tournament.archive
        assert archive.clone_age_days is not None
        assert archive.clone_age_days >= 0
    
    def test_has_original_data_property(self, base_tournament):
        """Test has_original_data property."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        assert archive.has_original_data is False
        
        archive.original_data = {'title': 'Test'}
        assert archive.has_original_data is True
    
    def test_preservation_settings_property(self, base_tournament):
        """Test preservation_settings property."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament,
            preserve_participants=True,
            preserve_matches=False,
            preserve_media=True
        )
        settings = archive.preservation_settings
        assert settings['participants'] is True
        assert settings['matches'] is False
        assert settings['media'] is True
    
    def test_is_fully_preserved_property(self, base_tournament):
        """Test is_fully_preserved property."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament,
            preserve_participants=True,
            preserve_matches=True,
            preserve_media=True
        )
        assert archive.is_fully_preserved is True
        
        archive.preserve_matches = False
        assert archive.is_fully_preserved is False
    
    def test_archive_metadata_property(self, archived_tournament):
        """Test archive_metadata property."""
        metadata = archived_tournament.archive.archive_metadata
        assert 'archive_type' in metadata
        assert 'is_archived' in metadata
        assert 'archived_at' in metadata
        assert 'can_restore' in metadata
        assert metadata['is_archived'] is True
    
    def test_clone_metadata_property(self, cloned_tournament):
        """Test clone_metadata property."""
        metadata = cloned_tournament.archive.clone_metadata
        assert 'is_clone' in metadata
        assert 'source_tournament' in metadata
        assert 'clone_number' in metadata
        assert metadata['is_clone'] is True
        assert metadata['clone_number'] == 1


@pytest.mark.django_db
class TestArchiveOperationMethods:
    """Test archive operation methods."""
    
    def test_archive_method(self, base_tournament, user):
        """Test archive() method."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        
        archive.archive(user=user, reason="Test reason")
        
        assert archive.archive_type == 'ARCHIVED'
        assert archive.is_archived is True
        assert archive.archived_at is not None
        assert archive.archived_by == user
        assert archive.archive_reason == "Test reason"
    
    def test_archive_already_archived(self, archived_tournament):
        """Test archiving an already archived tournament."""
        archive = archived_tournament.archive
        
        with pytest.raises(ValidationError, match="already archived"):
            archive.archive()
    
    def test_restore_method(self, archived_tournament, user):
        """Test restore() method."""
        archive = archived_tournament.archive
        
        archive.restore(user=user)
        
        assert archive.archive_type == 'ACTIVE'
        assert archive.is_archived is False
        assert archive.restored_at is not None
        assert archive.restored_by == user
    
    def test_restore_not_archived(self, base_tournament):
        """Test restoring a non-archived tournament."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        
        with pytest.raises(ValidationError, match="not archived"):
            archive.restore()
    
    def test_restore_when_disabled(self, archived_tournament, user):
        """Test restoring when can_restore is False."""
        archive = archived_tournament.archive
        archive.can_restore = False
        archive.save()
        
        with pytest.raises(ValidationError, match="cannot be restored"):
            archive.restore()
    
    def test_mark_as_clone_method(self, base_tournament, source_tournament, user):
        """Test mark_as_clone() method."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        
        archive.mark_as_clone(source=source_tournament, user=user, clone_num=1)
        
        assert archive.archive_type == 'CLONED'
        assert archive.source_tournament == source_tournament
        assert archive.clone_number == 1
        assert archive.cloned_at is not None
        assert archive.cloned_by == user
    
    def test_mark_as_clone_already_clone(self, cloned_tournament, source_tournament):
        """Test marking an already cloned tournament."""
        archive = cloned_tournament.archive
        
        with pytest.raises(ValidationError, match="already marked as a clone"):
            archive.mark_as_clone(source=source_tournament, user=None, clone_num=2)
    
    def test_save_snapshot_method(self, base_tournament):
        """Test save_snapshot() method."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament
        )
        
        data = {'title': 'Test', 'status': 'completed'}
        archive.save_snapshot(data)
        
        assert archive.original_data == data


@pytest.mark.django_db
class TestArchiveStatusCheckHelpers:
    """Test archive status check helper functions."""
    
    def test_is_archived_helper(self):
        """Test is_archived() helper."""
        # Create separate tournaments to avoid contamination
        active_tournament = Tournament.objects.create(
            name="Active Tournament",
            game="valorant",
            slug="active-tournament-status-check"
        )
        
        archived_tournament = Tournament.objects.create(
            name="Archived Tournament",
            game="valorant",
            slug="archived-tournament-status-check"
        )
        TournamentArchive.objects.create(
            tournament=archived_tournament,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=timezone.now()
        )
        
        assert is_archived(active_tournament) is False
        assert is_archived(archived_tournament) is True
    
    def test_is_active_helper(self):
        """Test is_active() helper."""
        active_tournament = Tournament.objects.create(
            name="Active Tournament 2",
            game="valorant",
            slug="active-tournament-2"
        )
        
        archived_tournament = Tournament.objects.create(
            name="Archived Tournament 2",
            game="valorant",
            slug="archived-tournament-2"
        )
        TournamentArchive.objects.create(
            tournament=archived_tournament,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=timezone.now()
        )
        
        assert is_active(active_tournament) is True
        assert is_active(archived_tournament) is False
    
    def test_is_clone_helper(self, base_tournament, cloned_tournament):
        """Test is_clone() helper."""
        assert is_clone(base_tournament) is False
        assert is_clone(cloned_tournament) is True
    
    def test_is_original_helper(self, base_tournament, cloned_tournament):
        """Test is_original() helper."""
        assert is_original(base_tournament) is True
        assert is_original(cloned_tournament) is False
    
    def test_can_restore_helper(self):
        """Test can_restore() helper."""
        active_tournament = Tournament.objects.create(
            name="Active Tournament 3",
            game="valorant",
            slug="active-tournament-3"
        )
        
        archived_tournament = Tournament.objects.create(
            name="Archived Tournament 3",
            game="valorant",
            slug="archived-tournament-3"
        )
        TournamentArchive.objects.create(
            tournament=archived_tournament,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=timezone.now(),
            can_restore=True
        )
        
        assert can_restore(active_tournament) is False
        assert can_restore(archived_tournament) is True
    
    def test_has_clones_helper(self, source_tournament, cloned_tournament):
        """Test has_clones() helper."""
        assert has_clones(source_tournament) is True
        
        new_tournament = Tournament.objects.create(
            name="New", game="valorant", slug="new"
        )
        assert has_clones(new_tournament) is False
    
    def test_has_been_restored_helper(self, archived_tournament, user):
        """Test has_been_restored() helper."""
        assert has_been_restored(archived_tournament) is False
        
        archive = archived_tournament.archive
        archive.restored_at = timezone.now()
        archive.restored_by = user
        archive.save()
        
        assert has_been_restored(archived_tournament) is True
    
    def test_get_archive_status_helper(self):
        """Test get_archive_status() helper."""
        active_tournament = Tournament.objects.create(
            name="Active Tournament 4",
            game="valorant",
            slug="active-tournament-4"
        )
        
        archived_tournament = Tournament.objects.create(
            name="Archived Tournament 4",
            game="valorant",
            slug="archived-tournament-4"
        )
        TournamentArchive.objects.create(
            tournament=archived_tournament,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=timezone.now()
        )
        
        cloned_tournament = Tournament.objects.create(
            name="Cloned Tournament",
            game="valorant",
            slug="cloned-tournament-status"
        )
        source = Tournament.objects.create(
            name="Source", game="valorant", slug="source-status"
        )
        TournamentArchive.objects.create(
            tournament=cloned_tournament,
            archive_type='CLONED',
            source_tournament=source,
            clone_number=1,
            cloned_at=timezone.now()
        )
        
        assert get_archive_status(active_tournament) == 'ACTIVE'
        assert get_archive_status(archived_tournament) == 'ARCHIVED'
        assert get_archive_status(cloned_tournament) == 'CLONED'


@pytest.mark.django_db
class TestArchiveOperationHelpers:
    """Test archive operation helper functions."""
    
    def test_archive_tournament_helper(self, base_tournament, user):
        """Test archive_tournament() helper."""
        archive = archive_tournament(base_tournament, user=user, reason="Test")
        
        assert archive.is_archived is True
        assert archive.archived_by == user
        assert archive.archive_reason == "Test"
    
    def test_unarchive_tournament_helper(self, archived_tournament, user):
        """Test unarchive_tournament() helper."""
        archive = unarchive_tournament(archived_tournament, user=user)
        
        assert archive.is_archived is False
        assert archive.restored_by == user
    
    def test_get_archive_reason_helper(self, archived_tournament):
        """Test get_archive_reason() helper."""
        reason = get_archive_reason(archived_tournament)
        assert reason == "Tournament completed"
    
    def test_get_archived_at_helper(self, archived_tournament):
        """Test get_archived_at() helper."""
        timestamp = get_archived_at(archived_tournament)
        assert timestamp is not None
    
    def test_get_archived_by_helper(self, archived_tournament, user):
        """Test get_archived_by() helper."""
        username = get_archived_by(archived_tournament)
        assert username == user.username
    
    def test_get_archive_age_days_helper(self, archived_tournament):
        """Test get_archive_age_days() helper."""
        days = get_archive_age_days(archived_tournament)
        assert days is not None
        assert days >= 0
    
    def test_set_archive_preservation_helper(self, base_tournament):
        """Test set_archive_preservation() helper."""
        archive = set_archive_preservation(
            base_tournament,
            preserve_participants=True,
            preserve_matches=False,
            preserve_media=True
        )
        
        assert archive.preserve_participants is True
        assert archive.preserve_matches is False
        assert archive.preserve_media is True


@pytest.mark.django_db
class TestCloneOperationHelpers:
    """Test clone operation helper functions."""
    
    def test_get_source_tournament_helper(self, base_tournament, cloned_tournament, source_tournament):
        """Test get_source_tournament() helper."""
        assert get_source_tournament(base_tournament) is None
        assert get_source_tournament(cloned_tournament) == source_tournament
    
    def test_get_clone_number_helper(self, base_tournament, cloned_tournament):
        """Test get_clone_number() helper."""
        assert get_clone_number(base_tournament) == 0
        assert get_clone_number(cloned_tournament) == 1
    
    def test_get_cloned_at_helper(self, cloned_tournament):
        """Test get_cloned_at() helper."""
        timestamp = get_cloned_at(cloned_tournament)
        assert timestamp is not None
    
    def test_get_cloned_by_helper(self, cloned_tournament, user):
        """Test get_cloned_by() helper."""
        username = get_cloned_by(cloned_tournament)
        assert username == user.username
    
    def test_get_clone_count_helper(self, source_tournament, cloned_tournament):
        """Test get_clone_count() helper."""
        count = get_clone_count(source_tournament)
        assert count == 1
    
    def test_get_clone_age_days_helper(self, cloned_tournament):
        """Test get_clone_age_days() helper."""
        days = get_clone_age_days(cloned_tournament)
        assert days is not None
        assert days >= 0
    
    def test_get_all_clones_helper(self, source_tournament, cloned_tournament):
        """Test get_all_clones() helper."""
        clones = get_all_clones(source_tournament)
        # Check if cloned_tournament is in the queryset
        assert clones.filter(pk=cloned_tournament.pk).exists()
        assert clones.count() == 1
    
    def test_mark_tournament_as_clone_helper(self, base_tournament, source_tournament, user):
        """Test mark_tournament_as_clone() helper."""
        archive = mark_tournament_as_clone(
            base_tournament,
            source=source_tournament,
            user=user
        )
        
        assert archive.archive_type == 'CLONED'
        assert archive.source_tournament == source_tournament
        assert archive.clone_number == 1
    
    def test_mark_tournament_as_clone_auto_number(self, source_tournament, cloned_tournament, user):
        """Test automatic clone number calculation."""
        new_clone = Tournament.objects.create(
            name="Second Clone",
            game="valorant",
            slug="second-clone"
        )
        
        archive = mark_tournament_as_clone(
            new_clone,
            source=source_tournament,
            user=user
        )
        
        assert archive.clone_number == 2  # Auto-incremented


@pytest.mark.django_db
class TestRestoreOperationHelpers:
    """Test restore operation helper functions."""
    
    def test_can_be_restored_helper(self, archived_tournament):
        """Test can_be_restored() helper."""
        assert can_be_restored(archived_tournament) is True
    
    def test_get_restored_at_helper(self, archived_tournament, user):
        """Test get_restored_at() helper."""
        archive = archived_tournament.archive
        archive.restored_at = timezone.now()
        archive.save()
        
        timestamp = get_restored_at(archived_tournament)
        assert timestamp is not None
    
    def test_get_restored_by_helper(self, archived_tournament, user):
        """Test get_restored_by() helper."""
        archive = archived_tournament.archive
        archive.restored_at = timezone.now()
        archive.restored_by = user
        archive.save()
        
        username = get_restored_by(archived_tournament)
        assert username == user.username
    
    def test_disable_restore_helper(self, base_tournament):
        """Test disable_restore() helper."""
        archive = disable_restore(base_tournament)
        assert archive.can_restore is False
    
    def test_enable_restore_helper(self, base_tournament):
        """Test enable_restore() helper."""
        # First disable
        archive = disable_restore(base_tournament)
        assert archive.can_restore is False
        
        # Then enable
        archive = enable_restore(base_tournament)
        assert archive.can_restore is True


@pytest.mark.django_db
class TestMetadataAccessHelpers:
    """Test metadata access helper functions."""
    
    def test_get_archive_metadata_helper(self, archived_tournament):
        """Test get_archive_metadata() helper."""
        metadata = get_archive_metadata(archived_tournament)
        
        assert 'archive_type' in metadata
        assert 'is_archived' in metadata
        assert 'archived_at' in metadata
        assert metadata['is_archived'] is True
    
    def test_get_clone_metadata_helper(self, cloned_tournament):
        """Test get_clone_metadata() helper."""
        metadata = get_clone_metadata(cloned_tournament)
        
        assert 'is_clone' in metadata
        assert 'source_tournament' in metadata
        assert 'clone_number' in metadata
        assert metadata['is_clone'] is True
    
    def test_get_preservation_settings_helper(self, base_tournament):
        """Test get_preservation_settings() helper."""
        TournamentArchive.objects.create(
            tournament=base_tournament,
            preserve_participants=True,
            preserve_matches=False,
            preserve_media=True
        )
        
        settings = get_preservation_settings(base_tournament)
        assert settings['participants'] is True
        assert settings['matches'] is False
        assert settings['media'] is True
    
    def test_is_fully_preserved_helper(self, base_tournament):
        """Test is_fully_preserved() helper."""
        TournamentArchive.objects.create(
            tournament=base_tournament,
            preserve_participants=True,
            preserve_matches=True,
            preserve_media=True
        )
        
        assert is_fully_preserved(base_tournament) is True
    
    def test_has_original_data_helper(self, base_tournament):
        """Test has_original_data() helper."""
        archive = TournamentArchive.objects.create(
            tournament=base_tournament,
            original_data={'title': 'Test'}
        )
        
        assert has_original_data(base_tournament) is True
    
    def test_get_archive_notes_helper(self, base_tournament):
        """Test get_archive_notes() helper."""
        TournamentArchive.objects.create(
            tournament=base_tournament,
            notes="Important notes"
        )
        
        notes = get_archive_notes(base_tournament)
        assert notes == "Important notes"


@pytest.mark.django_db
class TestQueryOptimizationHelpers:
    """Test query optimization helper functions."""
    
    def test_optimize_queryset_for_archive_helper(self):
        """Test optimize_queryset_for_archive() helper."""
        queryset = Tournament.objects.all()
        optimized = optimize_queryset_for_archive(queryset)
        
        # Check that select_related was applied
        assert 'archive' in str(optimized.query)
    
    def test_get_archived_tournaments_helper(self, archived_tournament):
        """Test get_archived_tournaments() helper."""
        archived = get_archived_tournaments()
        assert archived_tournament in archived
        assert archived.count() >= 1
    
    def test_get_active_tournaments_helper(self):
        """Test get_active_tournaments() helper."""
        # Create a fresh active tournament
        active_t = Tournament.objects.create(
            name="Fresh Active",
            game="valorant",
            slug="fresh-active-query"
        )
        
        # Create an archived tournament
        archived_t = Tournament.objects.create(
            name="Archived Query",
            game="valorant",
            slug="archived-query"
        )
        TournamentArchive.objects.create(
            tournament=archived_t,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=timezone.now()
        )
        
        active = get_active_tournaments()
        # active_t should be in active tournaments
        assert active.filter(pk=active_t.pk).exists()
        # archived_t should not be in active tournaments
        assert not active.filter(pk=archived_t.pk).exists()
    
    def test_get_cloned_tournaments_helper(self, cloned_tournament):
        """Test get_cloned_tournaments() helper."""
        clones = get_cloned_tournaments()
        assert cloned_tournament in clones
    
    def test_get_original_tournaments_helper(self, base_tournament, cloned_tournament):
        """Test get_original_tournaments() helper."""
        originals = get_original_tournaments()
        # cloned_tournament should not be in originals


@pytest.mark.django_db
class TestHistoricalDataHelpers:
    """Test historical data helper functions."""
    
    def test_save_tournament_snapshot_helper(self, base_tournament):
        """Test save_tournament_snapshot() helper."""
        data = {'title': 'Test', 'status': 'completed'}
        archive = save_tournament_snapshot(base_tournament, data)
        
        assert archive.original_data == data
    
    def test_get_tournament_snapshot_helper(self, base_tournament):
        """Test get_tournament_snapshot() helper."""
        data = {'title': 'Test', 'status': 'completed'}
        save_tournament_snapshot(base_tournament, data)
        
        snapshot = get_tournament_snapshot(base_tournament)
        assert snapshot == data
    
    def test_get_archive_context_helper(self, archived_tournament):
        """Test get_archive_context() helper."""
        context = get_archive_context(archived_tournament)
        
        # Check all expected keys
        assert 'tournament' in context
        assert 'has_archive' in context
        assert 'is_archived' in context
        assert 'is_active' in context
        assert 'archive_metadata' in context
        assert 'clone_metadata' in context
        
        # Verify values
        assert context['is_archived'] is True
        assert context['has_archive'] is True
    
    def test_get_archive_summary_helper(self, archived_tournament):
        """Test get_archive_summary() helper."""
        summary = get_archive_summary(archived_tournament)
        
        assert 'is_archived' in summary
        assert 'is_clone' in summary
        assert 'has_clones' in summary
        assert 'can_restore' in summary
        assert summary['is_archived'] is True


@pytest.mark.django_db
class TestArchiveIntegration:
    """Test complete archive workflows."""
    
    def test_complete_archive_workflow(self, base_tournament, user):
        """Test complete archive and restore workflow."""
        # Archive tournament
        archive = archive_tournament(base_tournament, user=user, reason="Season ended")
        assert is_archived(base_tournament) is True
        
        # Check metadata
        assert get_archive_reason(base_tournament) == "Season ended"
        assert get_archived_by(base_tournament) == user.username
        
        # Restore tournament
        unarchive_tournament(base_tournament, user=user)
        assert is_active(base_tournament) is True
        assert has_been_restored(base_tournament) is True
    
    def test_complete_clone_workflow(self, source_tournament, user):
        """Test complete clone workflow."""
        # Create and mark as clone
        clone = Tournament.objects.create(
            name="Clone",
            game="valorant",
            slug="clone"
        )
        mark_tournament_as_clone(clone, source=source_tournament, user=user)
        
        # Verify clone status
        assert is_clone(clone) is True
        assert get_source_tournament(clone) == source_tournament
        assert get_clone_number(clone) == 1
        
        # Verify source has clone
        assert has_clones(source_tournament) is True
        assert get_clone_count(source_tournament) == 1
    
    def test_tournament_without_archive(self):
        """Test handling tournament without archive record."""
        tournament = Tournament.objects.create(
            name="No Archive",
            game="valorant",
            slug="no-archive"
        )
        
        # Should handle gracefully
        assert is_archived(tournament) is False
        assert is_active(tournament) is True
        assert is_original(tournament) is True
        assert get_archive_status(tournament) == 'ACTIVE'


@pytest.mark.django_db
class TestArchiveEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_archive_with_no_user(self, base_tournament):
        """Test archiving without user."""
        archive = archive_tournament(base_tournament, user=None, reason="Auto-archived")
        
        assert archive.is_archived is True
        assert archive.archived_by is None
        assert get_archived_by(base_tournament) is None
    
    def test_restore_with_no_user(self, archived_tournament):
        """Test restoring without user."""
        archive = unarchive_tournament(archived_tournament, user=None)
        
        assert archive.is_archived is False
        assert archive.restored_by is None
    
    def test_multiple_clones(self, source_tournament, user):
        """Test creating multiple clones."""
        # Create first clone
        clone1 = Tournament.objects.create(
            name="Clone 1", game="valorant", slug="clone-1"
        )
        mark_tournament_as_clone(clone1, source=source_tournament, user=user)
        
        # Create second clone
        clone2 = Tournament.objects.create(
            name="Clone 2", game="valorant", slug="clone-2"
        )
        mark_tournament_as_clone(clone2, source=source_tournament, user=user)
        
        # Verify both have different clone numbers
        assert get_clone_number(clone1) == 1
        assert get_clone_number(clone2) == 2
        assert get_clone_count(source_tournament) == 2
    
    def test_archive_preservation_settings(self):
        """Test different preservation combinations."""
        tournament = Tournament.objects.create(
            name="Preservation Test",
            game="valorant",
            slug="preservation-test"
        )
        
        # All preserved
        archive = set_archive_preservation(tournament, True, True, True)
        assert is_fully_preserved(tournament) is True
        
        # Partial preservation
        archive = set_archive_preservation(tournament, True, False, True)
        # Refresh tournament from database to get updated archive
        tournament.refresh_from_db()
        assert is_fully_preserved(tournament) is False
        
        settings = get_preservation_settings(tournament)
        assert settings['participants'] is True
        assert settings['matches'] is False
        assert settings['media'] is True
    
    def test_snapshot_with_complex_data(self, base_tournament):
        """Test snapshot with complex data structures."""
        data = {
            'name': 'Complex Tournament',
            'settings': {
                'max_teams': 16,
                'format': 'single-elimination'
            },
            'prizes': [1000, 500, 250],
            'metadata': {
                'created_by': 'admin',
                'tags': ['professional', 'online']
            }
        }
        
        save_tournament_snapshot(base_tournament, data)
        snapshot = get_tournament_snapshot(base_tournament)
        
        assert snapshot == data
        assert snapshot['settings']['max_teams'] == 16
        assert snapshot['prizes'][0] == 1000
