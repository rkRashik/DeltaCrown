"""MediaCleanupCandidate — tracks old game media files for safe deferred deletion.

When a Game or GameMapPool image field is replaced/cleared in Django admin,
the old Cloudinary asset is NOT auto-deleted (django-cloudinary-storage does not
do this without django-cleanup). Instead, a MediaCleanupCandidate row is created
so that:

  1. The old file is retained for at least RETENTION_HOURS (default 48).
  2. Before deletion, the cleanup service re-checks that no DB row still
     references the file.
  3. Deletion is logged and auditable.
"""

from django.db import models
from django.utils import timezone


RETENTION_HOURS_DEFAULT = 48


class MediaCleanupCandidate(models.Model):
    STORAGE_CLOUDINARY = "cloudinary"
    STORAGE_LOCAL = "local"
    STORAGE_CHOICES = [
        (STORAGE_CLOUDINARY, "Cloudinary"),
        (STORAGE_LOCAL, "Local filesystem"),
    ]

    REASON_REPLACED = "replaced"
    REASON_CLEARED = "cleared"
    REASON_CHOICES = [
        (REASON_REPLACED, "Field replaced with new file"),
        (REASON_CLEARED, "Field cleared (set to empty)"),
    ]

    STATUS_PENDING = "pending"
    STATUS_DELETED = "deleted"
    STATUS_SKIPPED = "skipped"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending — awaiting retention period"),
        (STATUS_DELETED, "Deleted from storage"),
        (STATUS_SKIPPED, "Skipped (still referenced or protected)"),
        (STATUS_FAILED, "Deletion failed"),
    ]

    file_name = models.CharField(
        max_length=500,
        db_index=True,
        help_text="Cloudinary public_id or local file path stored in the DB field.",
    )
    storage_type = models.CharField(
        max_length=20,
        choices=STORAGE_CHOICES,
        default=STORAGE_CLOUDINARY,
    )
    source_model = models.CharField(
        max_length=100,
        help_text="e.g. 'games.Game' or 'games.GameMapPool'",
    )
    source_object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="PK of the source model row.",
    )
    source_field = models.CharField(
        max_length=100,
        help_text="ImageField name, e.g. 'icon', 'card_image'.",
    )
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    eligible_after = models.DateTimeField(
        db_index=True,
        help_text="Deletion not attempted before this timestamp.",
    )
    deleted_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra context: old/new public_id, game name, etc.",
    )

    class Meta:
        db_table = "games_mediacleanupcandidate"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "eligible_after"]),
            models.Index(fields=["file_name"]),
        ]
        verbose_name = "Media Cleanup Candidate"
        verbose_name_plural = "Media Cleanup Candidates"

    def __str__(self):
        return f"{self.file_name} [{self.status}]"

    @property
    def is_eligible(self):
        return self.status == self.STATUS_PENDING and timezone.now() >= self.eligible_after

    @classmethod
    def create_for_field(
        cls,
        *,
        file_name: str,
        source_model: str,
        source_object_id: int,
        source_field: str,
        reason: str = REASON_REPLACED,
        retention_hours: int = RETENTION_HOURS_DEFAULT,
        storage_type: str = STORAGE_CLOUDINARY,
        metadata: dict | None = None,
    ) -> "MediaCleanupCandidate | None":
        """Create a candidate, deduplicating on file_name + pending status."""
        if not file_name:
            return None
        # Deduplicate: don't add a second pending row for the same file.
        if cls.objects.filter(file_name=file_name, status=cls.STATUS_PENDING).exists():
            return None
        return cls.objects.create(
            file_name=file_name,
            storage_type=storage_type,
            source_model=source_model,
            source_object_id=source_object_id,
            source_field=source_field,
            reason=reason,
            eligible_after=timezone.now() + timezone.timedelta(hours=retention_hours),
            metadata=metadata or {},
        )
