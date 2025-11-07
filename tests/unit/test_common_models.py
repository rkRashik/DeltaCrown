"""
Unit tests for common app base models and managers.

Tests SoftDeleteModel, TimestampedModel, and SoftDeleteManager.

Source Documents:
- Documents/ExecutionPlan/00_MASTER_EXECUTION_PLAN.md#phase-1-module-1.1
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md#section-4-testing-standards
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#ADR-003

Test Coverage Requirements:
- Soft delete functionality (delete, restore)
- Timestamp auto-population (created_at, updated_at)
- Audit field tracking (deleted_by)
- Manager methods (get_queryset, with_deleted, deleted_only)
- QuerySet methods (soft_delete, restore)

Target: >80% code coverage
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

from apps.common.managers import SoftDeleteManager
from apps.common.models import SoftDeleteModel, TimestampedModel

User = get_user_model()


# Test models for testing abstract base classes
# Note: Using underscore prefix to prevent pytest from collecting these as test classes
class __TestSoftDeleteModel(SoftDeleteModel):
    """Concrete model for testing SoftDeleteModel."""
    
    name = models.CharField(max_length=100)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        app_label = 'common'


class __TestTimestampedModel(TimestampedModel):
    """Concrete model for testing TimestampedModel."""
    
    name = models.CharField(max_length=100)
    
    class Meta:
        app_label = 'common'


class __TestCombinedModel(SoftDeleteModel, TimestampedModel):
    """Concrete model for testing combined mixins."""
    
    name = models.CharField(max_length=100)
    
    objects = SoftDeleteManager()
    all_objects = models.Manager()
    
    class Meta:
        app_label = 'common'


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.mark.django_db
class _TestSoftDeleteModelFeatures:
    """Test suite for SoftDeleteModel functionality."""
    
    def test_soft_delete_model_has_required_fields(self):
        """Test that SoftDeleteModel has is_deleted, deleted_at, deleted_by fields."""
        model = __TestSoftDeleteModel(name='Test')
        
        assert hasattr(model, 'is_deleted')
        assert hasattr(model, 'deleted_at')
        assert hasattr(model, 'deleted_by')
    
    def test_new_instance_not_deleted_by_default(self):
        """Test that new instances have is_deleted=False by default."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        
        assert model.is_deleted is False
        assert model.deleted_at is None
        assert model.deleted_by is None
    
    def test_soft_delete_sets_is_deleted_flag(self, user):
        """Test that soft_delete() sets is_deleted to True."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        
        model.soft_delete(user=user)
        
        assert model.is_deleted is True
    
    def test_soft_delete_sets_deleted_at_timestamp(self, user):
        """Test that soft_delete() sets deleted_at to current time."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        
        before = timezone.now()
        model.soft_delete(user=user)
        after = timezone.now()
        
        assert model.deleted_at is not None
        assert before <= model.deleted_at <= after
    
    def test_soft_delete_sets_deleted_by_user(self, user):
        """Test that soft_delete() records the deleting user."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        
        model.soft_delete(user=user)
        
        assert model.deleted_by == user
    
    def test_soft_delete_without_user_still_works(self):
        """Test that soft_delete() works without providing a user."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        
        model.soft_delete()
        
        assert model.is_deleted is True
        assert model.deleted_at is not None
        assert model.deleted_by is None
    
    def test_soft_delete_persists_to_database(self, user):
        """Test that soft_delete() saves changes to database."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        
        model.soft_delete(user=user)
        
        # Refresh from database
        model_from_db = _TestSoftDeleteModel.all_objects.get(pk=model.pk)
        assert model_from_db.is_deleted is True
        assert model_from_db.deleted_at is not None
        assert model_from_db.deleted_by == user
    
    def test_restore_clears_is_deleted_flag(self, user):
        """Test that restore() sets is_deleted back to False."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        model.soft_delete(user=user)
        
        model.restore()
        
        assert model.is_deleted is False
    
    def test_restore_clears_deleted_at(self, user):
        """Test that restore() clears deleted_at timestamp."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        model.soft_delete(user=user)
        
        model.restore()
        
        assert model.deleted_at is None
    
    def test_restore_clears_deleted_by(self, user):
        """Test that restore() clears deleted_by user."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        model.soft_delete(user=user)
        
        model.restore()
        
        assert model.deleted_by is None
    
    def test_restore_persists_to_database(self, user):
        """Test that restore() saves changes to database."""
        model = _TestSoftDeleteModel.objects.create(name='Test')
        model.soft_delete(user=user)
        
        model.restore()
        
        # Refresh from database
        model_from_db = _TestSoftDeleteModel.all_objects.get(pk=model.pk)
        assert model_from_db.is_deleted is False
        assert model_from_db.deleted_at is None
        assert model_from_db.deleted_by is None


@pytest.mark.django_db
class TestSoftDeleteManager:
    """Test suite for SoftDeleteManager functionality."""
    
    def test_default_queryset_excludes_deleted_objects(self, user):
        """Test that default queryset excludes soft-deleted objects."""
        active = _TestSoftDeleteModel.objects.create(name='Active')
        deleted = _TestSoftDeleteModel.objects.create(name='Deleted')
        deleted.soft_delete(user=user)
        
        queryset = _TestSoftDeleteModel.objects.all()
        
        assert active in queryset
        assert deleted not in queryset
    
    def test_default_queryset_count_excludes_deleted(self, user):
        """Test that count() on default queryset excludes deleted objects."""
        _TestSoftDeleteModel.objects.create(name='Active 1')
        _TestSoftDeleteModel.objects.create(name='Active 2')
        deleted = _TestSoftDeleteModel.objects.create(name='Deleted')
        deleted.soft_delete(user=user)
        
        assert _TestSoftDeleteModel.objects.count() == 2
    
    def test_with_deleted_includes_all_objects(self, user):
        """Test that with_deleted() includes both active and deleted objects."""
        active = _TestSoftDeleteModel.objects.create(name='Active')
        deleted = _TestSoftDeleteModel.objects.create(name='Deleted')
        deleted.soft_delete(user=user)
        
        queryset = _TestSoftDeleteModel.objects.with_deleted()
        
        assert active in queryset
        assert deleted in queryset
    
    def test_with_deleted_count_includes_all(self, user):
        """Test that count() on with_deleted() includes all objects."""
        _TestSoftDeleteModel.objects.create(name='Active 1')
        _TestSoftDeleteModel.objects.create(name='Active 2')
        deleted = _TestSoftDeleteModel.objects.create(name='Deleted')
        deleted.soft_delete(user=user)
        
        assert _TestSoftDeleteModel.objects.with_deleted().count() == 3
    
    def test_deleted_only_excludes_active_objects(self, user):
        """Test that deleted_only() excludes active objects."""
        active = _TestSoftDeleteModel.objects.create(name='Active')
        deleted = _TestSoftDeleteModel.objects.create(name='Deleted')
        deleted.soft_delete(user=user)
        
        queryset = _TestSoftDeleteModel.objects.deleted_only()
        
        assert active not in queryset
        assert deleted in queryset
    
    def test_deleted_only_count_only_deleted(self, user):
        """Test that count() on deleted_only() only counts deleted objects."""
        _TestSoftDeleteModel.objects.create(name='Active 1')
        _TestSoftDeleteModel.objects.create(name='Active 2')
        deleted = _TestSoftDeleteModel.objects.create(name='Deleted')
        deleted.soft_delete(user=user)
        
        assert _TestSoftDeleteModel.objects.deleted_only().count() == 1
    
    def test_queryset_soft_delete_method_deletes_all(self, user):
        """Test that QuerySet.soft_delete() soft-deletes all objects in queryset."""
        _TestSoftDeleteModel.objects.create(name='Item 1')
        _TestSoftDeleteModel.objects.create(name='Item 2')
        _TestSoftDeleteModel.objects.create(name='Item 3')
        
        _TestSoftDeleteModel.objects.all().soft_delete(user=user)
        
        assert _TestSoftDeleteModel.objects.count() == 0
        assert _TestSoftDeleteModel.objects.with_deleted().count() == 3
    
    def test_queryset_soft_delete_returns_count(self, user):
        """Test that QuerySet.soft_delete() returns number of deleted objects."""
        _TestSoftDeleteModel.objects.create(name='Item 1')
        _TestSoftDeleteModel.objects.create(name='Item 2')
        
        count = _TestSoftDeleteModel.objects.all().soft_delete(user=user)
        
        assert count == 2
    
    def test_queryset_restore_method_restores_all(self, user):
        """Test that QuerySet.restore() restores all soft-deleted objects."""
        item1 = _TestSoftDeleteModel.objects.create(name='Item 1')
        item2 = _TestSoftDeleteModel.objects.create(name='Item 2')
        item1.soft_delete(user=user)
        item2.soft_delete(user=user)
        
        _TestSoftDeleteModel.objects.deleted_only().restore()
        
        assert _TestSoftDeleteModel.objects.count() == 2
        assert _TestSoftDeleteModel.objects.deleted_only().count() == 0
    
    def test_queryset_restore_returns_count(self, user):
        """Test that QuerySet.restore() returns number of restored objects."""
        item1 = _TestSoftDeleteModel.objects.create(name='Item 1')
        item2 = _TestSoftDeleteModel.objects.create(name='Item 2')
        item1.soft_delete(user=user)
        item2.soft_delete(user=user)
        
        count = _TestSoftDeleteModel.objects.deleted_only().restore()
        
        assert count == 2


@pytest.mark.django_db
class _TestTimestampedModelFeatures:
    """Test suite for TimestampedModel functionality."""
    
    def test_timestamped_model_has_required_fields(self):
        """Test that TimestampedModel has created_at and updated_at fields."""
        model = _TestTimestampedModel(name='Test')
        
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'updated_at')
    
    def test_created_at_set_on_creation(self):
        """Test that created_at is automatically set when object is created."""
        before = timezone.now()
        model = _TestTimestampedModel.objects.create(name='Test')
        after = timezone.now()
        
        assert model.created_at is not None
        assert before <= model.created_at <= after
    
    def test_updated_at_set_on_creation(self):
        """Test that updated_at is automatically set when object is created."""
        before = timezone.now()
        model = _TestTimestampedModel.objects.create(name='Test')
        after = timezone.now()
        
        assert model.updated_at is not None
        assert before <= model.updated_at <= after
    
    def test_created_at_does_not_change_on_update(self):
        """Test that created_at remains unchanged when object is updated."""
        model = _TestTimestampedModel.objects.create(name='Original')
        original_created_at = model.created_at
        
        # Update the object
        model.name = 'Updated'
        model.save()
        
        assert model.created_at == original_created_at
    
    def test_updated_at_changes_on_update(self):
        """Test that updated_at is updated when object is modified."""
        model = _TestTimestampedModel.objects.create(name='Original')
        original_updated_at = model.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        # Update the object
        model.name = 'Updated'
        model.save()
        
        assert model.updated_at > original_updated_at


@pytest.mark.django_db
class _TestCombinedModelFeatures:
    """Test suite for combined SoftDeleteModel + TimestampedModel."""
    
    def test_combined_model_has_all_fields(self):
        """Test that combined model has fields from both mixins."""
        model = _TestCombinedModel(name='Test')
        
        # SoftDeleteModel fields
        assert hasattr(model, 'is_deleted')
        assert hasattr(model, 'deleted_at')
        assert hasattr(model, 'deleted_by')
        
        # TimestampedModel fields
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'updated_at')
    
    def test_timestamps_work_with_soft_delete(self, user):
        """Test that timestamps are properly maintained during soft delete."""
        model = _TestCombinedModel.objects.create(name='Test')
        original_created_at = model.created_at
        original_updated_at = model.updated_at
        
        # Small delay
        import time
        time.sleep(0.01)
        
        model.soft_delete(user=user)
        
        # created_at should not change
        assert model.created_at == original_created_at
        
        # updated_at should be updated
        assert model.updated_at > original_updated_at
    
    def test_manager_works_with_combined_model(self, user):
        """Test that SoftDeleteManager works correctly with combined model."""
        active = _TestCombinedModel.objects.create(name='Active')
        deleted = _TestCombinedModel.objects.create(name='Deleted')
        deleted.soft_delete(user=user)
        
        # Default queryset excludes deleted
        assert _TestCombinedModel.objects.count() == 1
        assert active in _TestCombinedModel.objects.all()
        assert deleted not in _TestCombinedModel.objects.all()
        
        # with_deleted includes all
        assert _TestCombinedModel.objects.with_deleted().count() == 2
        
        # deleted_only shows only deleted
        assert _TestCombinedModel.objects.deleted_only().count() == 1
