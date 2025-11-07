"""
Unit tests for common app base models and managers.

Tests SoftDeleteModel, TimestampedModel, and SoftDeleteManager without requiring database.

Source Documents:
- Documents/ExecutionPlan/00_MASTER_EXECUTION_PLAN.md#phase-1-module-1.1
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md#section-4-testing-standards
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#ADR-003

Test Coverage Requirements:
- Soft delete functionality (delete, restore)
- Timestamp auto-population (created_at, updated_at)
- Audit field tracking (deleted_by)
- Manager methods (get_queryset, with_deleted, deleted_only)

Target: >80% code coverage
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from django.utils import timezone

from apps.common.managers import SoftDeleteManager, SoftDeleteQuerySet
from apps.common.models import SoftDeleteModel, TimestampedModel


class TestSoftDeleteModelFeatures:
    """Test suite for SoftDeleteModel functionality."""
    
    def test_soft_delete_model_has_required_fields(self):
        """Test that SoftDeleteModel has is_deleted, deleted_at, deleted_by fields."""
        # Create a mock instance
        instance = SoftDeleteModel()
        
        assert hasattr(instance, 'is_deleted')
        assert hasattr(instance, 'deleted_at')
        assert hasattr(instance, 'deleted_by_id')
    
    @patch.object(SoftDeleteModel, 'save')
    def test_soft_delete_sets_is_deleted_flag(self, mock_save):
        """Test that soft_delete() sets is_deleted to True."""
        instance = SoftDeleteModel()
        instance.is_deleted = False
        
        instance.soft_delete()
        
        assert instance.is_deleted is True
        mock_save.assert_called_once()
    
    @patch.object(SoftDeleteModel, 'save')
    def test_soft_delete_sets_deleted_at_timestamp(self, mock_save):
        """Test that soft_delete() sets deleted_at to current time."""
        instance = SoftDeleteModel()
        instance.deleted_at = None
        
        before = timezone.now()
        instance.soft_delete()
        after = timezone.now()
        
        assert instance.deleted_at is not None
        assert before <= instance.deleted_at <= after
        mock_save.assert_called_once_with(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])
    
    @patch.object(SoftDeleteModel, 'save')
    def test_soft_delete_sets_deleted_by_user(self, mock_save):
        """Test that soft_delete() records the deleting user."""
        instance = SoftDeleteModel()
        instance.deleted_by = None
        user = Mock(id=1)
        
        instance.soft_delete(user=user)
        
        assert instance.deleted_by == user
        mock_save.assert_called_once()
    
    @patch.object(SoftDeleteModel, 'save')
    def test_soft_delete_without_user_still_works(self, mock_save):
        """Test that soft_delete() works without providing a user."""
        instance = SoftDeleteModel()
        
        instance.soft_delete()
        
        assert instance.is_deleted is True
        assert instance.deleted_at is not None
        assert instance.deleted_by is None
        mock_save.assert_called_once()
    
    @patch.object(SoftDeleteModel, 'save')
    def test_restore_clears_is_deleted_flag(self, mock_save):
        """Test that restore() sets is_deleted back to False."""
        instance = SoftDeleteModel()
        instance.is_deleted = True
        
        instance.restore()
        
        assert instance.is_deleted is False
        mock_save.assert_called_once()
    
    @patch.object(SoftDeleteModel, 'save')
    def test_restore_clears_deleted_at(self, mock_save):
        """Test that restore() clears deleted_at timestamp."""
        instance = SoftDeleteModel()
        instance.deleted_at = timezone.now()
        
        instance.restore()
        
        assert instance.deleted_at is None
        mock_save.assert_called_once()
    
    @patch.object(SoftDeleteModel, 'save')
    def test_restore_clears_deleted_by(self, mock_save):
        """Test that restore() clears deleted_by user."""
        instance = SoftDeleteModel()
        instance.deleted_by = Mock(id=1)
        
        instance.restore()
        
        assert instance.deleted_by is None
        mock_save.assert_called_once_with(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class TestSoftDeleteManager:
    """Test suite for SoftDeleteManager functionality."""
    
    def test_get_queryset_filters_deleted_objects(self):
        """Test that default queryset excludes soft-deleted objects."""
        manager = SoftDeleteManager()
        manager.model = Mock()
        manager._db = 'default'
        
        with patch.object(SoftDeleteQuerySet, 'filter') as mock_filter:
            queryset = manager.get_queryset()
            
            # Verify filter was called with is_deleted=False
            mock_filter.assert_called_once_with(is_deleted=False)
    
    def test_with_deleted_returns_all_objects(self):
        """Test that with_deleted() includes all objects."""
        manager = SoftDeleteManager()
        manager.model = Mock()
        manager._db = 'default'
        
        queryset = manager.with_deleted()
        
        assert isinstance(queryset, SoftDeleteQuerySet)
    
    def test_deleted_only_filters_deleted_objects(self):
        """Test that deleted_only() only returns deleted objects."""
        manager = SoftDeleteManager()
        manager.model = Mock()
        manager._db = 'default'
        
        with patch.object(SoftDeleteQuerySet, 'filter') as mock_filter:
            queryset = manager.deleted_only()
            
            # Verify filter was called with is_deleted=True
            mock_filter.assert_called_once_with(is_deleted=True)


class TestSoftDeleteQuerySet:
    """Test suite for SoftDeleteQuerySet functionality."""
    
    def test_queryset_soft_delete_updates_is_deleted(self):
        """Test that QuerySet.soft_delete() updates is_deleted flag."""
        qs = SoftDeleteQuerySet(model=Mock())
        
        with patch.object(qs, 'update', return_value=5) as mock_update:
            count = qs.soft_delete()
            
            assert count == 5
            # Verify update was called with correct fields
            call_args = mock_update.call_args[1]
            assert call_args['is_deleted'] is True
            assert 'deleted_at' in call_args
    
    def test_queryset_soft_delete_with_user(self):
        """Test that QuerySet.soft_delete() records deleting user."""
        qs = SoftDeleteQuerySet(model=Mock())
        user = Mock(id=1)
        
        with patch.object(qs, 'update', return_value=3) as mock_update:
            count = qs.soft_delete(user=user)
            
            assert count == 3
            call_args = mock_update.call_args[1]
            assert call_args['deleted_by'] == user
    
    def test_queryset_restore_clears_fields(self):
        """Test that QuerySet.restore() clears deletion fields."""
        qs = SoftDeleteQuerySet(model=Mock())
        
        with patch.object(qs, 'update', return_value=2) as mock_update:
            count = qs.restore()
            
            assert count == 2
            mock_update.assert_called_once_with(
                is_deleted=False,
                deleted_at=None,
                deleted_by=None
            )


class TestTimestampedModelFeatures:
    """Test suite for TimestampedModel functionality."""
    
    def test_timestamped_model_has_required_fields(self):
        """Test that TimestampedModel has created_at and updated_at fields."""
        instance = TimestampedModel()
        
        assert hasattr(instance, 'created_at')
        assert hasattr(instance, 'updated_at')


class TestCombinedModelFeatures:
    """Test suite for combined SoftDeleteModel + TimestampedModel."""
    
    def test_combined_model_has_all_fields(self):
        """Test that combined model has fields from both mixins."""
        # Create a class that uses both mixins
        class CombinedModel(SoftDeleteModel, TimestampedModel):
            pass
        
        instance = CombinedModel()
        
        # SoftDeleteModel fields
        assert hasattr(instance, 'is_deleted')
        assert hasattr(instance, 'deleted_at')
        assert hasattr(instance, 'deleted_by_id')
        
        # TimestampedModel fields
        assert hasattr(instance, 'created_at')
        assert hasattr(instance, 'updated_at')
    
    @patch.object(SoftDeleteModel, 'save')
    def test_soft_delete_works_with_combined_model(self, mock_save):
        """Test that soft_delete() works with combined model."""
        class CombinedModel(SoftDeleteModel, TimestampedModel):
            pass
        
        instance = CombinedModel()
        instance.is_deleted = False
        
        instance.soft_delete()
        
        assert instance.is_deleted is True
        assert instance.deleted_at is not None
        mock_save.assert_called_once()


# Run coverage check
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=apps.common', '--cov-report=term-missing'])
