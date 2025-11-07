"""
Custom model managers for DeltaCrown Tournament Engine.

Provides QuerySet managers for soft-deleted models.

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md#section-4.0
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md#ADR-003
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md#section-2

Architecture Decision Records:
- ADR-003: Soft Delete Strategy

Implementation Notes:
- SoftDeleteManager excludes soft-deleted objects by default
- Provides with_deleted() to include all objects
- Provides deleted_only() to query only deleted objects
"""

from django.db import models


class SoftDeleteQuerySet(models.QuerySet):
    """
    QuerySet that adds soft delete methods.

    Methods:
        soft_delete(user): Soft delete all objects in queryset
        restore(): Restore all soft-deleted objects in queryset
    """

    def soft_delete(self, user=None):
        """
        Soft delete all objects in this queryset.

        Args:
            user: User performing the deletion (optional)

        Returns:
            int: Number of objects deleted
        """
        from django.utils import timezone
        
        update_fields = {
            'is_deleted': True,
            'deleted_at': timezone.now(),
        }
        if user:
            update_fields['deleted_by'] = user
        
        return self.update(**update_fields)

    def restore(self):
        """
        Restore all soft-deleted objects in this queryset.

        Returns:
            int: Number of objects restored
        """
        return self.update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None
        )


class SoftDeleteManager(models.Manager):
    """
    Manager that excludes soft-deleted objects by default.

    By default, queries using this manager will only return objects
    where is_deleted=False. Use with_deleted() or deleted_only() to
    include deleted objects.

    Methods:
        get_queryset(): Returns queryset excluding soft-deleted objects
        with_deleted(): Returns queryset including all objects
        deleted_only(): Returns queryset of only soft-deleted objects

    Usage:
        class MyModel(SoftDeleteModel):
            objects = SoftDeleteManager()

        MyModel.objects.all()  # Excludes deleted
        MyModel.objects.with_deleted()  # Includes deleted
        MyModel.objects.deleted_only()  # Only deleted

    Source: ADR-003 (Soft Delete Strategy)
    """

    def get_queryset(self):
        """
        Return queryset excluding soft-deleted objects.

        Returns:
            SoftDeleteQuerySet: QuerySet with is_deleted=False filter
        """
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def with_deleted(self):
        """
        Return queryset including all objects (including soft-deleted).

        Returns:
            SoftDeleteQuerySet: QuerySet with no deletion filter
        """
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """
        Return queryset of only soft-deleted objects.

        Returns:
            SoftDeleteQuerySet: QuerySet with is_deleted=True filter
        """
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=True)
