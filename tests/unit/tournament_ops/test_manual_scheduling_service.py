"""
Unit Tests for Manual Scheduling Service - Phase 7, Epic 7.2

Tests for ManualSchedulingService orchestration logic.

Test Coverage:
- Match listing with filters
- Manual assignment with conflict detection
- Bulk shift operations
- Time slot generation
- Soft validation (warnings not errors)
- Event publishing

Reference: Phase 7, Epic 7.2 - Manual Scheduling Tools
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from apps.tournament_ops.services.manual_scheduling_service import ManualSchedulingService
from apps.tournament_ops.dtos.scheduling import (
    MatchSchedulingItemDTO,
    SchedulingSlotDTO,
    SchedulingConflictDTO,
    BulkShiftResultDTO,
)


@pytest.fixture
def mock_adapter():
    """Create mock MatchSchedulingAdapter."""
    adapter = Mock()
    return adapter


@pytest.fixture
def service(mock_adapter):
    """Create ManualSchedulingService with mocked adapter."""
    return ManualSchedulingService(adapter=mock_adapter)


@pytest.fixture
def sample_match_dto():
    """Create sample MatchSchedulingItemDTO."""
    return MatchSchedulingItemDTO(
        match_id=101,
        tournament_id=1,
        tournament_name="Summer Championship",
        stage_id=10,
        stage_name="Finals",
        round_number=1,
        match_number=1,
        participant1_id=201,
        participant1_name="Team Alpha",
        participant2_id=202,
        participant2_name="Team Beta",
        scheduled_time=None,
        estimated_duration_minutes=60,
        state="pending",
        lobby_info={},
        conflicts=[],
        can_reschedule=True
    )


@pytest.fixture
def sample_conflict_dto():
    """Create sample SchedulingConflictDTO."""
    return SchedulingConflictDTO(
        conflict_type="team_conflict",
        severity="warning",
        message="Team Alpha has overlapping match at 2025-12-15 14:00:00",
        affected_match_ids=[101, 102],
        suggested_resolution="Reschedule to avoid overlap"
    )


class TestListMatchesForScheduling:
    """Tests for list_matches_for_scheduling method."""
    
    def test_list_all_matches(self, service, mock_adapter, sample_match_dto):
        """Test listing all matches without filters."""
        mock_adapter.get_matches_requiring_scheduling.return_value = [sample_match_dto]
        
        result = service.list_matches_for_scheduling()
        
        assert len(result) == 1
        assert result[0].match_id == 101
        mock_adapter.get_matches_requiring_scheduling.assert_called_once_with(
            tournament_id=None,
            stage_id=None,
            unscheduled_only=False
        )
    
    def test_list_matches_by_tournament(self, service, mock_adapter, sample_match_dto):
        """Test filtering matches by tournament_id."""
        mock_adapter.get_matches_requiring_scheduling.return_value = [sample_match_dto]
        
        result = service.list_matches_for_scheduling(tournament_id=1)
        
        assert len(result) == 1
        mock_adapter.get_matches_requiring_scheduling.assert_called_once_with(
            tournament_id=1,
            stage_id=None,
            unscheduled_only=False
        )
    
    def test_list_matches_by_stage(self, service, mock_adapter, sample_match_dto):
        """Test filtering matches by stage_id."""
        mock_adapter.get_matches_requiring_scheduling.return_value = [sample_match_dto]
        
        result = service.list_matches_for_scheduling(stage_id=10)
        
        assert len(result) == 1
        mock_adapter.get_matches_requiring_scheduling.assert_called_once_with(
            tournament_id=None,
            stage_id=10,
            unscheduled_only=False
        )
    
    def test_list_unscheduled_only(self, service, mock_adapter, sample_match_dto):
        """Test filtering for unscheduled matches only."""
        mock_adapter.get_matches_requiring_scheduling.return_value = [sample_match_dto]
        
        result = service.list_matches_for_scheduling(
            filters={'unscheduled_only': True}
        )
        
        assert len(result) == 1
        mock_adapter.get_matches_requiring_scheduling.assert_called_once_with(
            tournament_id=None,
            stage_id=None,
            unscheduled_only=True
        )
    
    def test_list_with_conflicts_only(self, service, mock_adapter):
        """Test filtering for matches with conflicts only."""
        match_with_conflict = MatchSchedulingItemDTO(
            match_id=101,
            tournament_id=1,
            tournament_name="Summer Championship",
            stage_id=10,
            stage_name="Finals",
            round_number=1,
            match_number=1,
            participant1_id=201,
            participant1_name="Team Alpha",
            participant2_id=202,
            participant2_name="Team Beta",
            scheduled_time=datetime.now(timezone.utc),
            estimated_duration_minutes=60,
            state="scheduled",
            lobby_info={},
            conflicts=["Team conflict detected"],
            can_reschedule=True
        )
        match_without_conflict = MatchSchedulingItemDTO(
            match_id=102,
            tournament_id=1,
            tournament_name="Summer Championship",
            stage_id=10,
            stage_name="Finals",
            round_number=1,
            match_number=2,
            participant1_id=203,
            participant1_name="Team Gamma",
            participant2_id=204,
            participant2_name="Team Delta",
            scheduled_time=None,
            estimated_duration_minutes=60,
            state="pending",
            lobby_info={},
            conflicts=[],
            can_reschedule=True
        )
        
        mock_adapter.get_matches_requiring_scheduling.return_value = [
            match_with_conflict,
            match_without_conflict
        ]
        
        result = service.list_matches_for_scheduling(
            filters={'with_conflicts': True}
        )
        
        assert len(result) == 1
        assert result[0].match_id == 101


class TestAssignMatch:
    """Tests for assign_match method."""
    
    @patch('apps.tournament_ops.services.manual_scheduling_service.datetime')
    def test_assign_match_first_time(
        self,
        mock_datetime,
        service,
        mock_adapter,
        sample_match_dto
    ):
        """Test assigning a match for the first time (no prior schedule)."""
        mock_datetime.utcnow.return_value = datetime(2025, 12, 10, 12, 0, 0)
        
        scheduled_time = datetime(2025, 12, 15, 14, 0, 0)
        
        # Mock adapter responses
        mock_adapter.get_matches_requiring_scheduling.return_value = [sample_match_dto]
        mock_adapter.get_conflicts_for_match.return_value = []
        
        updated_match = MatchSchedulingItemDTO(
            **{**sample_match_dto.__dict__, 'scheduled_time': scheduled_time}
        )
        mock_adapter.update_match_schedule.return_value = updated_match
        
        # Assign match
        with patch.object(service, '_publish_event') as mock_publish:
            result = service.assign_match(101, scheduled_time, 999)
        
        # Verify result
        assert result['match'].scheduled_time == scheduled_time
        assert result['was_rescheduled'] is False
        assert len(result['conflicts']) == 0
        
        # Verify adapter calls
        mock_adapter.update_match_schedule.assert_called_once_with(
            101, scheduled_time, 999
        )
        
        # Verify event published
        assert mock_publish.call_count == 1
        event = mock_publish.call_args[0][0]
        assert event.match_id == 101
    
    @patch('apps.tournament_ops.services.manual_scheduling_service.datetime')
    def test_reschedule_existing_match(
        self,
        mock_datetime,
        service,
        mock_adapter
    ):
        """Test rescheduling a match that already has a schedule."""
        mock_datetime.utcnow.return_value = datetime(2025, 12, 10, 12, 0, 0)
        
        old_time = datetime(2025, 12, 14, 10, 0, 0)
        new_time = datetime(2025, 12, 15, 14, 0, 0)
        
        # Match already has scheduled_time
        existing_match = MatchSchedulingItemDTO(
            match_id=101,
            tournament_id=1,
            tournament_name="Summer Championship",
            stage_id=10,
            stage_name="Finals",
            round_number=1,
            match_number=1,
            participant1_id=201,
            participant1_name="Team Alpha",
            participant2_id=202,
            participant2_name="Team Beta",
            scheduled_time=old_time,
            estimated_duration_minutes=60,
            state="scheduled",
            lobby_info={},
            conflicts=[],
            can_reschedule=True
        )
        
        mock_adapter.get_matches_requiring_scheduling.return_value = [existing_match]
        mock_adapter.get_conflicts_for_match.return_value = []
        
        updated_match = MatchSchedulingItemDTO(
            **{**existing_match.__dict__, 'scheduled_time': new_time}
        )
        mock_adapter.update_match_schedule.return_value = updated_match
        
        # Reschedule match
        with patch.object(service, '_publish_event') as mock_publish:
            result = service.assign_match(101, new_time, 999)
        
        # Verify it was detected as reschedule
        assert result['was_rescheduled'] is True
        assert result['match'].scheduled_time == new_time
        
        # Verify RescheduledEvent was published
        event = mock_publish.call_args[0][0]
        assert event.old_time == old_time
        assert event.new_time == new_time
    
    @patch('apps.tournament_ops.services.manual_scheduling_service.datetime')
    def test_assign_with_conflicts(
        self,
        mock_datetime,
        service,
        mock_adapter,
        sample_match_dto,
        sample_conflict_dto
    ):
        """Test assigning match with conflict detection (soft validation)."""
        mock_datetime.utcnow.return_value = datetime(2025, 12, 10, 12, 0, 0)
        
        scheduled_time = datetime(2025, 12, 15, 14, 0, 0)
        
        # Mock conflict detected
        mock_adapter.get_matches_requiring_scheduling.return_value = [sample_match_dto]
        mock_adapter.get_conflicts_for_match.return_value = [sample_conflict_dto]
        
        updated_match = MatchSchedulingItemDTO(
            **{**sample_match_dto.__dict__, 'scheduled_time': scheduled_time}
        )
        mock_adapter.update_match_schedule.return_value = updated_match
        
        # Assign match (should succeed despite conflict)
        with patch.object(service, '_publish_event') as mock_publish:
            result = service.assign_match(101, scheduled_time, 999)
        
        # Verify conflicts returned as warnings
        assert len(result['conflicts']) == 1
        assert result['conflicts'][0].severity == 'warning'
        assert result['conflicts'][0].conflict_type == 'team_conflict'
        
        # Verify assignment still succeeded
        assert result['match'].scheduled_time == scheduled_time
        
        # Verify conflict event published
        assert mock_publish.call_count == 2  # Conflict event + scheduling event
    
    def test_assign_match_not_found(self, service, mock_adapter):
        """Test assigning non-existent match raises ValueError."""
        mock_adapter.get_matches_requiring_scheduling.return_value = []
        
        scheduled_time = datetime(2025, 12, 15, 14, 0, 0)
        
        with pytest.raises(ValueError, match="Match 999 not found"):
            service.assign_match(999, scheduled_time, 888)


class TestBulkShiftMatches:
    """Tests for bulk_shift_matches method."""
    
    @patch('apps.tournament_ops.services.manual_scheduling_service.datetime')
    def test_bulk_shift_success(
        self,
        mock_datetime,
        service,
        mock_adapter
    ):
        """Test successful bulk shift of all matches in stage."""
        mock_datetime.utcnow.return_value = datetime(2025, 12, 10, 12, 0, 0)
        
        # Mock matches before shift
        match1 = MatchSchedulingItemDTO(
            match_id=101, tournament_id=1, tournament_name="Test",
            stage_id=10, stage_name="Finals", round_number=1, match_number=1,
            participant1_id=201, participant1_name="Team A",
            participant2_id=202, participant2_name="Team B",
            scheduled_time=datetime(2025, 12, 15, 10, 0, 0),
            estimated_duration_minutes=60, state="scheduled",
            lobby_info={}, conflicts=[], can_reschedule=True
        )
        
        mock_adapter.get_matches_requiring_scheduling.side_effect = [
            [match1],  # Before shift
            [match1]   # After shift (for conflict detection)
        ]
        
        # Mock successful bulk update
        mock_adapter.bulk_update_match_schedule.return_value = {
            'shifted_count': 1,
            'match_ids': [101]
        }
        
        mock_adapter.get_conflicts_for_match.return_value = []
        
        # Perform bulk shift
        with patch.object(service, '_publish_event') as mock_publish:
            result = service.bulk_shift_matches(10, 30, 999)
        
        # Verify result
        assert result.shifted_count == 1
        assert result.failed_count == 0
        assert len(result.failed_match_ids) == 0
        assert result.was_successful()
        
        # Verify event published
        mock_publish.assert_called_once()
        event = mock_publish.call_args[0][0]
        assert event.stage_id == 10
        assert event.delta_minutes == 30
    
    @patch('apps.tournament_ops.services.manual_scheduling_service.datetime')
    def test_bulk_shift_with_conflicts(
        self,
        mock_datetime,
        service,
        mock_adapter,
        sample_conflict_dto
    ):
        """Test bulk shift detecting conflicts after shift."""
        mock_datetime.utcnow.return_value = datetime(2025, 12, 10, 12, 0, 0)
        
        match1 = MatchSchedulingItemDTO(
            match_id=101, tournament_id=1, tournament_name="Test",
            stage_id=10, stage_name="Finals", round_number=1, match_number=1,
            participant1_id=201, participant1_name="Team A",
            participant2_id=202, participant2_name="Team B",
            scheduled_time=datetime(2025, 12, 15, 10, 0, 0),
            estimated_duration_minutes=60, state="scheduled",
            lobby_info={}, conflicts=[], can_reschedule=True
        )
        
        mock_adapter.get_matches_requiring_scheduling.side_effect = [
            [match1],  # Before
            [match1]   # After (with new time)
        ]
        
        mock_adapter.bulk_update_match_schedule.return_value = {
            'shifted_count': 1,
            'match_ids': [101]
        }
        
        # Conflict detected after shift
        mock_adapter.get_conflicts_for_match.return_value = [sample_conflict_dto]
        
        with patch.object(service, '_publish_event'):
            result = service.bulk_shift_matches(10, 30, 999)
        
        # Verify conflicts detected
        assert len(result.conflicts_detected) == 1
        assert result.has_conflicts()
    
    def test_bulk_shift_failure(self, service, mock_adapter):
        """Test bulk shift handling adapter failures."""
        match1 = MatchSchedulingItemDTO(
            match_id=101, tournament_id=1, tournament_name="Test",
            stage_id=10, stage_name="Finals", round_number=1, match_number=1,
            participant1_id=201, participant1_name="Team A",
            participant2_id=202, participant2_name="Team B",
            scheduled_time=datetime(2025, 12, 15, 10, 0, 0),
            estimated_duration_minutes=60, state="scheduled",
            lobby_info={}, conflicts=[], can_reschedule=True
        )
        
        mock_adapter.get_matches_requiring_scheduling.return_value = [match1]
        mock_adapter.bulk_update_match_schedule.side_effect = Exception("Database error")
        
        result = service.bulk_shift_matches(10, 30, 999)
        
        # Verify failure recorded
        assert result.shifted_count == 0
        assert result.failed_count == 1
        assert 101 in result.failed_match_ids
        assert "Database error" in result.error_messages[101]


class TestAutoGenerateSlots:
    """Tests for auto_generate_slots method."""
    
    def test_generate_slots_basic(self, service, mock_adapter):
        """Test basic slot generation."""
        start_date = datetime(2025, 12, 15, 9, 0, 0)
        end_date = datetime(2025, 12, 15, 12, 0, 0)
        
        mock_adapter.get_stage_time_window.return_value = {
            'start_date': start_date,
            'end_date': end_date,
            'blackout_periods': []
        }
        
        match1 = MatchSchedulingItemDTO(
            match_id=101, tournament_id=1, tournament_name="Test",
            stage_id=10, stage_name="Finals", round_number=1, match_number=1,
            participant1_id=201, participant1_name="Team A",
            participant2_id=202, participant2_name="Team B",
            scheduled_time=None,
            estimated_duration_minutes=60, state="pending",
            lobby_info={}, conflicts=[], can_reschedule=True
        )
        
        mock_adapter.get_matches_requiring_scheduling.return_value = [match1]
        
        slots = service.auto_generate_slots(10, slot_duration_minutes=60, interval_minutes=15)
        
        # Verify slots generated
        assert len(slots) > 0
        
        # Verify first slot
        first_slot = slots[0]
        assert first_slot.slot_start == start_date
        assert first_slot.duration_minutes == 60
        assert first_slot.is_available
    
    def test_generate_slots_with_blackout(self, service, mock_adapter):
        """Test slot generation respecting blackout periods."""
        start_date = datetime(2025, 12, 15, 9, 0, 0)
        end_date = datetime(2025, 12, 15, 18, 0, 0)
        
        blackout_start = datetime(2025, 12, 15, 12, 0, 0)
        blackout_end = datetime(2025, 12, 15, 13, 0, 0)
        
        mock_adapter.get_stage_time_window.return_value = {
            'start_date': start_date,
            'end_date': end_date,
            'blackout_periods': [{
                'start': blackout_start,
                'end': blackout_end
            }]
        }
        
        match1 = MatchSchedulingItemDTO(
            match_id=101, tournament_id=1, tournament_name="Test",
            stage_id=10, stage_name="Finals", round_number=1, match_number=1,
            participant1_id=None, participant1_name=None,
            participant2_id=None, participant2_name=None,
            scheduled_time=None,
            estimated_duration_minutes=60, state="pending",
            lobby_info={}, conflicts=[], can_reschedule=True
        )
        
        mock_adapter.get_matches_requiring_scheduling.return_value = [match1]
        
        slots = service.auto_generate_slots(10, slot_duration_minutes=60, interval_minutes=15)
        
        # Find slot overlapping with blackout
        blackout_slots = [
            s for s in slots
            if s.slot_start < blackout_end and s.slot_end > blackout_start
        ]
        
        # Verify blackout slots marked unavailable
        for slot in blackout_slots:
            assert not slot.is_available
            assert any('blackout' in c.lower() for c in slot.conflicts)
