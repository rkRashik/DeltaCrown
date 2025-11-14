"""
Base abstract models and mixins for DeltaCrown Tournament Engine.

This module provides:
- SoftDeleteModel: Soft deletion support with audit trail
- TimestampedModel: Automatic created_at/updated_at tracking
- Audit mixins for tracking changes

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md#section-4.0-base-mixins
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md#ADR-003
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md#section-1

Architecture Decision Records:
- ADR-003: Soft Delete Strategy (Flag-based with audit trail)

Implementation Notes:
- Uses Django's abstract base classes for mixins
- SoftDeleteModel includes is_deleted, deleted_at, deleted_by
- TimestampedModel includes created_at, updated_at with auto_now
- Custom managers handle soft-deleted objects automatically
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class SoftDeleteModel(models.Model):
    """
    Abstract base model for soft deletion support.

    Provides soft delete functionality where records are flagged as deleted
    rather than being removed from the database. Maintains audit trail with
    deletion timestamp and user.

    Fields:
        is_deleted (bool): Flag indicating if record is soft-deleted
        deleted_at (datetime): Timestamp when record was deleted
        deleted_by (ForeignKey): User who performed the deletion

    Methods:
        soft_delete(user): Mark record as deleted
        restore(): Restore soft-deleted record

    Usage:
        class MyModel(SoftDeleteModel):
            name = models.CharField(max_length=100)

        obj.soft_delete(user=request.user)
        obj.restore()

    Source: ADR-003 (Soft Delete Strategy)
    """

    is_deleted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Flag indicating if this record has been soft-deleted"
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this record was deleted"
    )
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_deletions',
        help_text="User who deleted this record"
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        """
        Mark this record as soft-deleted.

        Args:
            user: User performing the deletion (optional)

        Returns:
            None

        Side Effects:
            - Sets is_deleted to True
            - Sets deleted_at to current timestamp
            - Sets deleted_by to provided user
            - Saves the instance
        """
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def restore(self):
        """
        Restore a soft-deleted record.

        Returns:
            None

        Side Effects:
            - Sets is_deleted to False
            - Clears deleted_at
            - Clears deleted_by
            - Saves the instance
        """
        self.is_deleted = False
        self.deleted_at = None
        self.deleted_by = None
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])


class TimestampedModel(models.Model):
    """
    Abstract base model for automatic timestamp tracking.

    Automatically tracks creation and modification timestamps.

    Fields:
        created_at (datetime): Timestamp when record was created
        updated_at (datetime): Timestamp when record was last updated

    Usage:
        class MyModel(TimestampedModel):
            name = models.CharField(max_length=100)

    Source: PART_3.1_DATABASE_DESIGN_ERD.md#section-4.0
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this record was last updated"
    )

    class Meta:
        abstract = True
