"""
Tests for MatchOpsAdapter - Phase 7, Epic 7.4

Reference: Phase 7, Epic 7.4 - Match Operations Command Center
"""

import pytest
from datetime import datetime
from django.contrib.auth import get_user_model

from apps.tournament_ops.adapters.match_ops_adapter import MatchOpsAdapter
from apps.tournaments.models import Tournament, Stage, Match, MatchOperationLog, MatchModeratorNote

User = get_user_model()


@pytest.fixture
def user(db):
    """Create test user."""
    return User.objects.create_user(username='testuser', password='testpass')


@pytest.fixture
def tournament(db):
    """Create test tournament."""
    return Tournament.objects.create(
        name='Test Tournament',
        max_participants=16,
        status='OPEN'
    )


@pytest.fixture
def stage(tournament):
    """Create test stage."""
    return Stage.objects.create(
        tournament=tournament,
        name='Test Stage',
        stage_type='SINGLE_ELIMINATION',
        bracket_size=8
    )


@pytest.fixture
def match(stage):
    """Create test match."""
    return Match.objects.create(
        stage=stage,
        round_number=1,
        match_number=1,
        status='PENDING'
    )


@pytest.fixture
def adapter():
    """MatchOpsAdapter instance."""
    return MatchOpsAdapter()


class TestGetMatchState:
    """Tests for get_match_state()."""
    
    def test_get_match_state(self, adapter, match):
        """Test get match state."""
        state = adapter.get_match_state(match.id)
        assert state == 'PENDING'
    
    def test_get_match_state_not_found(self, adapter):
        """Test match not found."""
        with pytest.raises(ValueError, match="Match .* not found"):
            adapter.get_match_state(99999)


class TestSetMatchState:
    """Tests for set_match_state()."""
    
    def test_set_match_state(self, adapter, match, user):
        """Test set match state."""
        adapter.set_match_state(match.id, 'LIVE', user.id)
        
        match.refresh_from_db()
        assert match.status == 'LIVE'
    
    def test_set_match_state_invalid(self, adapter, match, user):
        """Test invalid state."""
        with pytest.raises(ValueError, match="Invalid state"):
            adapter.set_match_state(match.id, 'INVALID', user.id)


class TestAddOperationLog:
    """Tests for add_operation_log()."""
    
    def test_add_operation_log(self, adapter, match, user):
        """Test add operation log."""
        dto = adapter.add_operation_log(
            match_id=match.id,
            operator_user_id=user.id,
            operation_type='LIVE',
            payload={'test': 'data'}
        )
        
        assert dto.log_id > 0
        assert dto.match_id == match.id
        assert dto.operation_type == 'LIVE'
        assert dto.payload == {'test': 'data'}
        
        # Verify DB
        log = MatchOperationLog.objects.get(id=dto.log_id)
        assert log.match_id == match.id


class TestListOperationLogs:
    """Tests for list_operation_logs()."""
    
    def test_list_operation_logs(self, adapter, match, user):
        """Test list operation logs."""
        # Create logs
        adapter.add_operation_log(match.id, user.id, 'LIVE')
        adapter.add_operation_log(match.id, user.id, 'PAUSED')
        
        logs = adapter.list_operation_logs(match.id, limit=10)
        
        assert len(logs) == 2
        # Ordered by created_at DESC
        assert logs[0].operation_type == 'PAUSED'
        assert logs[1].operation_type == 'LIVE'


class TestAddModeratorNote:
    """Tests for add_moderator_note()."""
    
    def test_add_moderator_note(self, adapter, match, user):
        """Test add moderator note."""
        dto = adapter.add_moderator_note(
            match_id=match.id,
            author_user_id=user.id,
            content='Test note content'
        )
        
        assert dto.note_id > 0
        assert dto.content == 'Test note content'
        
        # Verify DB
        note = MatchModeratorNote.objects.get(id=dto.note_id)
        assert note.content == 'Test note content'
    
    def test_add_moderator_note_empty_content(self, adapter, match, user):
        """Test empty content validation."""
        with pytest.raises(ValueError, match="cannot be empty"):
            adapter.add_moderator_note(match.id, user.id, '')


class TestListModeratorNotes:
    """Tests for list_moderator_notes()."""
    
    def test_list_moderator_notes(self, adapter, match, user):
        """Test list moderator notes."""
        adapter.add_moderator_note(match.id, user.id, 'Note 1')
        adapter.add_moderator_note(match.id, user.id, 'Note 2')
        
        notes = adapter.list_moderator_notes(match.id)
        
        assert len(notes) == 2
        # Ordered by created_at ASC
        assert notes[0].content == 'Note 1'
        assert notes[1].content == 'Note 2'


class TestOverrideMatchResult:
    """Tests for override_match_result()."""
    
    def test_override_match_result(self, adapter, match, user):
        """Test override match result."""
        # Set initial result
        match.result_data = {'winner': 'team1'}
        match.save()
        
        new_result = {'winner': 'team2', 'reason': 'correction'}
        result_dto = adapter.override_match_result(
            match_id=match.id,
            new_result_data=new_result,
            operator_user_id=user.id
        )
        
        assert result_dto.success is True
        assert result_dto.new_state == 'COMPLETED'
        
        # Verify match updated
        match.refresh_from_db()
        assert match.result_data == new_result
        assert match.status == 'COMPLETED'
        
        # Verify operation log created
        log = MatchOperationLog.objects.filter(match_id=match.id, operation_type='OVERRIDE_RESULT').first()
        assert log is not None
        assert log.payload['old_result'] == {'winner': 'team1'}


class TestCountModeratorNotes:
    """Tests for count_moderator_notes()."""
    
    def test_count_moderator_notes(self, adapter, match, user):
        """Test count moderator notes."""
        adapter.add_moderator_note(match.id, user.id, 'Note 1')
        adapter.add_moderator_note(match.id, user.id, 'Note 2')
        adapter.add_moderator_note(match.id, user.id, 'Note 3')
        
        count = adapter.count_moderator_notes(match.id)
        assert count == 3


class TestGetLastOperation:
    """Tests for get_last_operation()."""
    
    def test_get_last_operation(self, adapter, match, user):
        """Test get last operation."""
        adapter.add_operation_log(match.id, user.id, 'LIVE')
        adapter.add_operation_log(match.id, user.id, 'PAUSED')
        
        last_op = adapter.get_last_operation(match.id)
        
        assert last_op is not None
        assert last_op.operation_type == 'PAUSED'
    
    def test_get_last_operation_none(self, adapter, match):
        """Test no operations."""
        last_op = adapter.get_last_operation(match.id)
        assert last_op is None
