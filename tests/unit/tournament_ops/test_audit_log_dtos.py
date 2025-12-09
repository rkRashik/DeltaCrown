"""
Unit Tests for Audit Log DTOs

Phase 7, Epic 7.5: Audit Log System
Tests for AuditLogDTO, AuditLogFilterDTO, and AuditLogExportDTO.
"""

import pytest
from datetime import datetime, timedelta
from apps.tournament_ops.dtos import (
    AuditLogDTO,
    AuditLogFilterDTO,
    AuditLogExportDTO,
)


class TestAuditLogDTO:
    """Tests for AuditLogDTO."""
    
    def test_create_audit_log_dto(self):
        """Test creating audit log DTO with all fields."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="result_finalized",
            timestamp=now,
            metadata={"submission_id": 99},
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            tournament_id=10,
            match_id=42,
            before_state={"status": "PENDING"},
            after_state={"status": "FINALIZED"},
            correlation_id="abc-123"
        )
        
        assert dto.log_id == 1
        assert dto.user_id == 5
        assert dto.username == "admin"
        assert dto.action == "result_finalized"
        assert dto.timestamp == now
        assert dto.metadata == {"submission_id": 99}
        assert dto.tournament_id == 10
        assert dto.match_id == 42
        assert dto.before_state == {"status": "PENDING"}
        assert dto.after_state == {"status": "FINALIZED"}
    
    def test_audit_log_dto_with_minimal_fields(self):
        """Test creating audit log DTO with required fields only."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=None,  # System action
            username=None,
            action="system_cleanup",
            timestamp=now
        )
        
        assert dto.log_id == 1
        assert dto.user_id is None
        assert dto.username is None
        assert dto.action == "system_cleanup"
        assert dto.metadata is None
        assert dto.before_state is None
        assert dto.after_state is None
    
    def test_audit_log_dto_validate_success(self):
        """Test DTO validation passes for valid data."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="result_finalized",
            timestamp=now,
            tournament_id=10
        )
        
        # Should not raise
        dto.validate()
    
    def test_audit_log_dto_validate_missing_action(self):
        """Test DTO validation fails for missing action."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="",  # Invalid
            timestamp=now
        )
        
        with pytest.raises(ValueError, match="Action is required"):
            dto.validate()
    
    def test_audit_log_dto_validate_invalid_ids(self):
        """Test DTO validation fails for invalid IDs."""
        now = datetime.now()
        
        # Invalid log_id
        dto = AuditLogDTO(
            log_id=-1,
            user_id=5,
            username="admin",
            action="test",
            timestamp=now
        )
        with pytest.raises(ValueError, match="log_id must be positive"):
            dto.validate()
        
        # Invalid user_id
        dto = AuditLogDTO(
            log_id=1,
            user_id=-1,
            username="admin",
            action="test",
            timestamp=now
        )
        with pytest.raises(ValueError, match="user_id must be positive"):
            dto.validate()
        
        # Invalid tournament_id
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="test",
            timestamp=now,
            tournament_id=-1
        )
        with pytest.raises(ValueError, match="tournament_id must be positive"):
            dto.validate()
    
    def test_has_state_change_true(self):
        """Test has_state_change returns True when both states present."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="result_finalized",
            timestamp=now,
            before_state={"status": "PENDING"},
            after_state={"status": "FINALIZED"}
        )
        
        assert dto.has_state_change() is True
    
    def test_has_state_change_false(self):
        """Test has_state_change returns False when states missing."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="staff_assigned",
            timestamp=now
        )
        
        assert dto.has_state_change() is False
    
    def test_get_changed_fields(self):
        """Test get_changed_fields returns changed field names."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="match_rescheduled",
            timestamp=now,
            before_state={"scheduled_time": "2025-12-10T10:00:00Z", "status": "PENDING"},
            after_state={"scheduled_time": "2025-12-10T14:00:00Z", "status": "PENDING"}
        )
        
        changed = dto.get_changed_fields()
        assert "scheduled_time" in changed
        assert "status" not in changed  # Status didn't change
    
    def test_get_changed_fields_no_state(self):
        """Test get_changed_fields returns empty list when no state."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="staff_assigned",
            timestamp=now
        )
        
        assert dto.get_changed_fields() == []
    
    def test_to_dict(self):
        """Test to_dict method converts DTO to dictionary."""
        now = datetime.now()
        dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="result_finalized",
            timestamp=now,
            tournament_id=10
        )
        
        result = dto.to_dict()
        assert isinstance(result, dict)
        assert result['log_id'] == 1
        assert result['user_id'] == 5
        assert result['action'] == "result_finalized"


class TestAuditLogFilterDTO:
    """Tests for AuditLogFilterDTO."""
    
    def test_create_filter_dto_with_all_params(self):
        """Test creating filter DTO with all parameters."""
        start = datetime.now()
        end = start + timedelta(days=7)
        
        filters = AuditLogFilterDTO(
            user_id=5,
            action="result_finalized",
            action_prefix="result_",
            tournament_id=10,
            match_id=42,
            start_date=start,
            end_date=end,
            has_state_change=True,
            correlation_id="abc-123",
            limit=50,
            offset=10,
            order_by="-timestamp"
        )
        
        assert filters.user_id == 5
        assert filters.action == "result_finalized"
        assert filters.action_prefix == "result_"
        assert filters.tournament_id == 10
        assert filters.match_id == 42
        assert filters.start_date == start
        assert filters.end_date == end
        assert filters.has_state_change is True
        assert filters.limit == 50
        assert filters.offset == 10
    
    def test_filter_dto_defaults(self):
        """Test filter DTO uses correct defaults."""
        filters = AuditLogFilterDTO()
        
        assert filters.limit == 100
        assert filters.offset == 0
        assert filters.order_by == '-timestamp'
        assert filters.user_id is None
        assert filters.action is None
    
    def test_filter_dto_validate_success(self):
        """Test filter validation passes for valid params."""
        filters = AuditLogFilterDTO(
            tournament_id=10,
            limit=50,
            offset=0
        )
        
        # Should not raise
        filters.validate()
    
    def test_filter_dto_validate_negative_limit(self):
        """Test validation fails for negative limit."""
        filters = AuditLogFilterDTO(limit=-1)
        
        with pytest.raises(ValueError, match="limit must be non-negative"):
            filters.validate()
    
    def test_filter_dto_validate_negative_offset(self):
        """Test validation fails for negative offset."""
        filters = AuditLogFilterDTO(offset=-1)
        
        with pytest.raises(ValueError, match="offset must be non-negative"):
            filters.validate()
    
    def test_filter_dto_validate_limit_too_large(self):
        """Test validation fails for limit > 1000."""
        filters = AuditLogFilterDTO(limit=1001)
        
        with pytest.raises(ValueError, match="limit cannot exceed 1000"):
            filters.validate()
    
    def test_filter_dto_validate_date_range(self):
        """Test validation fails when start_date > end_date."""
        start = datetime.now()
        end = start - timedelta(days=1)  # End before start
        
        filters = AuditLogFilterDTO(start_date=start, end_date=end)
        
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            filters.validate()
    
    def test_filter_dto_validate_order_by(self):
        """Test validation fails for invalid order_by."""
        filters = AuditLogFilterDTO(order_by="invalid_field")
        
        with pytest.raises(ValueError, match="order_by must be one of"):
            filters.validate()


class TestAuditLogExportDTO:
    """Tests for AuditLogExportDTO."""
    
    def test_create_export_dto_from_audit_log_dto(self):
        """Test creating export DTO from audit log DTO."""
        now = datetime.now()
        audit_dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="result_finalized",
            timestamp=now,
            tournament_id=10,
            match_id=42,
            before_state={"status": "PENDING"},
            after_state={"status": "FINALIZED"},
            metadata={"submission_id": 99},
            ip_address="192.168.1.1"
        )
        
        export_dto = AuditLogExportDTO.from_audit_log_dto(audit_dto)
        
        assert export_dto.log_id == 1
        assert export_dto.username == "admin"
        assert export_dto.action == "result_finalized"
        assert export_dto.timestamp == now.isoformat()
        assert export_dto.tournament_id == 10
        assert export_dto.match_id == 42
        assert export_dto.ip_address == "192.168.1.1"
        assert '"status": "PENDING"' in export_dto.before_state_json
        assert '"status": "FINALIZED"' in export_dto.after_state_json
        assert export_dto.changed_fields == "status"
    
    def test_export_dto_to_csv_row(self):
        """Test converting export DTO to CSV row dictionary."""
        now = datetime.now()
        audit_dto = AuditLogDTO(
            log_id=1,
            user_id=5,
            username="admin",
            action="result_finalized",
            timestamp=now,
            tournament_id=10
        )
        
        export_dto = AuditLogExportDTO.from_audit_log_dto(audit_dto)
        csv_row = export_dto.to_csv_row()
        
        assert isinstance(csv_row, dict)
        assert csv_row['Log ID'] == 1
        assert csv_row['User'] == "admin"
        assert csv_row['Action'] == "result_finalized"
        assert csv_row['Tournament ID'] == 10
    
    def test_export_dto_system_action(self):
        """Test export DTO for system action (no user)."""
        now = datetime.now()
        audit_dto = AuditLogDTO(
            log_id=1,
            user_id=None,
            username=None,
            action="system_cleanup",
            timestamp=now
        )
        
        export_dto = AuditLogExportDTO.from_audit_log_dto(audit_dto)
        
        assert export_dto.username == "SYSTEM"


# Run with: pytest tests/unit/tournament_ops/test_audit_log_dtos.py -v
