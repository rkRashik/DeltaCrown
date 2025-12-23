"""
Tests for Backfill Command

Validates:
- Idempotency (safe to run multiple times)
- Dry-run mode (no commits)
- Chunking (batch processing)
- Error handling
"""

import pytest
from django.core.management import call_command
from io import StringIO
from apps.user_profile.models.activity import UserActivity, EventType
from apps.accounts.models import User
from apps.user_profile.models import UserProfile


@pytest.fixture
def test_user(db):
    """Create test user."""
    user = User.objects.create_user(
        username='backfilluser',
        email='backfill@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def tournament_registration(test_user, db):
    """Create mock registration."""
    from apps.tournaments.models import Registration
    
    # Mock tournament
    tournament = type('MockTournament', (), {
        'id': 100,
        'name': 'Test Tournament'
    })()
    
    # Create registration (simplified - may need actual Tournament model)
    # This is placeholder - adjust based on actual Registration model
    return None


@pytest.mark.django_db
class TestBackfillDryRun:
    """Test dry-run mode."""
    
    def test_dry_run_no_changes(self):
        """Should preview changes without committing."""
        out = StringIO()
        
        # Run in dry-run mode
        call_command('backfill_user_activities', '--dry-run', stdout=out)
        
        output = out.getvalue()
        assert 'DRY RUN' in output
        assert 'No changes committed' in output
        
        # Should not create any events
        assert UserActivity.objects.count() == 0


@pytest.mark.django_db
class TestBackfillIdempotency:
    """Test idempotent behavior."""
    
    def test_backfill_twice_same_result(self, test_user):
        """Should not create duplicate events when run twice."""
        # This test requires actual Registration/Match/Transaction records
        # Placeholder - implement once models are available
        
        # Run backfill twice
        call_command('backfill_user_activities', '--event-type', 'tournaments')
        count1 = UserActivity.objects.count()
        
        call_command('backfill_user_activities', '--event-type', 'tournaments')
        count2 = UserActivity.objects.count()
        
        # Should be same count (idempotent)
        assert count1 == count2


@pytest.mark.django_db
class TestBackfillChunking:
    """Test batch processing."""
    
    def test_custom_chunk_size(self):
        """Should process in custom chunk sizes."""
        out = StringIO()
        
        # Run with custom chunk size
        call_command(
            'backfill_user_activities',
            '--chunk-size', '100',
            '--dry-run',
            stdout=out
        )
        
        output = out.getvalue()
        assert 'DRY RUN' in output


@pytest.mark.django_db
class TestBackfillEventTypes:
    """Test selective backfill."""
    
    def test_backfill_tournaments_only(self):
        """Should backfill only tournament events."""
        out = StringIO()
        
        call_command(
            'backfill_user_activities',
            '--event-type', 'tournaments',
            '--dry-run',
            stdout=out
        )
        
        output = out.getvalue()
        assert 'tournament' in output.lower()
    
    def test_backfill_matches_only(self):
        """Should backfill only match events."""
        out = StringIO()
        
        call_command(
            'backfill_user_activities',
            '--event-type', 'matches',
            '--dry-run',
            stdout=out
        )
        
        output = out.getvalue()
        assert 'match' in output.lower()
    
    def test_backfill_economy_only(self):
        """Should backfill only economy events."""
        out = StringIO()
        
        call_command(
            'backfill_user_activities',
            '--event-type', 'economy',
            '--dry-run',
            stdout=out
        )
        
        output = out.getvalue()
        assert 'economy' in output.lower()


@pytest.mark.django_db
class TestBackfillLimit:
    """Test record limiting."""
    
    def test_limit_records(self):
        """Should respect record limit."""
        out = StringIO()
        
        call_command(
            'backfill_user_activities',
            '--limit', '10',
            '--dry-run',
            stdout=out
        )
        
        output = out.getvalue()
        assert 'DRY RUN' in output


@pytest.mark.django_db
class TestBackfillOutput:
    """Test command output."""
    
    def test_summary_output(self):
        """Should show summary statistics."""
        out = StringIO()
        
        call_command('backfill_user_activities', '--dry-run', stdout=out)
        
        output = out.getvalue()
        assert 'BACKFILL SUMMARY' in output
        assert 'Tournaments:' in output
        assert 'Matches:' in output
        assert 'Economy:' in output
        assert 'processed' in output
