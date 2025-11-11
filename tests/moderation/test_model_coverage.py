"""
Test Model Coverage - Phase 8 Hardening

Quick unit tests for model validation methods and repr to boost coverage from 80% → ≥90%.
Tests clean() validation, __str__() repr, and helper methods.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.moderation.models import ModerationSanction, ModerationAudit, AbuseReport


@pytest.mark.django_db
class TestModerationSanctionModel:
    """Test ModerationSanction model methods."""
    
    def test_clean_validates_tournament_scope_requires_scope_id(self):
        """Test clean() requires scope_id when scope=tournament."""
        sanction = ModerationSanction(
            subject_profile_id=1,
            type='ban',
            scope='tournament',
            scope_id=None,  # Missing
            reason_code='test',
        )
        
        with pytest.raises(ValidationError, match="scope_id required"):
            sanction.clean()
    
    def test_clean_validates_ends_at_after_starts_at(self):
        """Test clean() validates ends_at > starts_at."""
        now = timezone.now()
        past = now - timedelta(hours=1)
        
        sanction = ModerationSanction(
            subject_profile_id=1,
            type='ban',
            scope='global',
            reason_code='test',
            starts_at=now,
            ends_at=past,  # Invalid
        )
        
        with pytest.raises(ValidationError, match="ends_at must be after starts_at"):
            sanction.clean()
    
    def test_clean_passes_for_valid_sanction(self):
        """Test clean() passes for valid sanction."""
        sanction = ModerationSanction(
            subject_profile_id=1,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        # Should not raise
        sanction.clean()
    
    def test_is_active_returns_true_for_active_sanction(self):
        """Test is_active() returns True for active sanction."""
        now = timezone.now()
        sanction = ModerationSanction.objects.create(
            subject_profile_id=1,
            type='ban',
            scope='global',
            reason_code='test',
            starts_at=now - timedelta(hours=1),
            ends_at=now + timedelta(hours=1),
        )
        
        assert sanction.is_active() is True
    
    def test_is_active_returns_false_for_revoked_sanction(self):
        """Test is_active() returns False for revoked sanction."""
        sanction = ModerationSanction.objects.create(
            subject_profile_id=1,
            type='ban',
            scope='global',
            reason_code='test',
            revoked_at=timezone.now(),
        )
        
        assert sanction.is_active() is False
    
    def test_is_active_returns_false_for_expired_sanction(self):
        """Test is_active() returns False for expired sanction."""
        now = timezone.now()
        sanction = ModerationSanction.objects.create(
            subject_profile_id=1,
            type='ban',
            scope='global',
            reason_code='test',
            starts_at=now - timedelta(days=2),
            ends_at=now - timedelta(days=1),  # Expired
        )
        
        assert sanction.is_active() is False
    
    def test_str_repr(self):
        """Test __str__() representation."""
        sanction = ModerationSanction.objects.create(
            subject_profile_id=123,
            type='ban',
            scope='global',
            reason_code='test',
        )
        
        assert str(sanction) == "ban:global for profile#123"


@pytest.mark.django_db
class TestModerationAuditModel:
    """Test ModerationAudit model methods."""
    
    def test_str_repr_with_actor(self):
        """Test __str__() representation with actor."""
        audit = ModerationAudit.objects.create(
            event='sanction_created',
            actor_id=9000,
            subject_profile_id=123,
            ref_type='sanction',
            ref_id=456,
        )
        
        assert str(audit) == "sanction_created by actor#9000 on sanction#456"
    
    def test_str_repr_without_actor(self):
        """Test __str__() representation without actor (system)."""
        audit = ModerationAudit.objects.create(
            event='sanction_created',
            actor_id=None,
            subject_profile_id=123,
            ref_type='sanction',
            ref_id=456,
        )
        
        assert str(audit) == "sanction_created by system on sanction#456"


@pytest.mark.django_db
class TestAbuseReportModel:
    """Test AbuseReport model methods."""
    
    def test_clean_validates_priority_bounds_low(self):
        """Test clean() validates priority >= 0."""
        report = AbuseReport(
            reporter_profile_id=1,
            category='test',
            ref_type='test',
            ref_id=1,
            priority=-1,  # Invalid
        )
        
        with pytest.raises(ValidationError, match="priority must be between 0 and 5"):
            report.clean()
    
    def test_clean_validates_priority_bounds_high(self):
        """Test clean() validates priority <= 5."""
        report = AbuseReport(
            reporter_profile_id=1,
            category='test',
            ref_type='test',
            ref_id=1,
            priority=6,  # Invalid
        )
        
        with pytest.raises(ValidationError, match="priority must be between 0 and 5"):
            report.clean()
    
    def test_clean_passes_for_valid_priority(self):
        """Test clean() passes for valid priority."""
        report = AbuseReport(
            reporter_profile_id=1,
            category='test',
            ref_type='test',
            ref_id=1,
            priority=3,
        )
        
        # Should not raise
        report.clean()
    
    def test_can_transition_to_valid(self):
        """Test can_transition_to() for valid transitions."""
        report = AbuseReport.objects.create(
            reporter_profile_id=1,
            category='test',
            ref_type='test',
            ref_id=1,
            state='open',
        )
        
        assert report.can_transition_to('triaged') is True
        assert report.can_transition_to('resolved') is False
        assert report.can_transition_to('rejected') is False
    
    def test_can_transition_to_from_triaged(self):
        """Test can_transition_to() from triaged state."""
        report = AbuseReport.objects.create(
            reporter_profile_id=1,
            category='test',
            ref_type='test',
            ref_id=1,
            state='triaged',
        )
        
        assert report.can_transition_to('resolved') is True
        assert report.can_transition_to('rejected') is True
        assert report.can_transition_to('open') is False
    
    def test_can_transition_to_from_terminal(self):
        """Test can_transition_to() from terminal states."""
        report = AbuseReport.objects.create(
            reporter_profile_id=1,
            category='test',
            ref_type='test',
            ref_id=1,
            state='resolved',
        )
        
        assert report.can_transition_to('open') is False
        assert report.can_transition_to('triaged') is False
        assert report.can_transition_to('rejected') is False
    
    def test_str_repr(self):
        """Test __str__() representation."""
        report = AbuseReport.objects.create(
            reporter_profile_id=1,
            category='harassment',
            ref_type='chat_message',
            ref_id=500,
            state='open',
        )
        
        assert f"Report#{report.id}" in str(report)
        assert "(open)" in str(report)
        assert "harassment" in str(report)
        assert "chat_message#500" in str(report)
