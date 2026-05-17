"""MaintenanceRunLog — audit trail for admin maintenance operations."""

from django.conf import settings
from django.db import models


class MaintenanceRunLog(models.Model):
    STATUS_SUCCESS = "success"
    STATUS_PARTIAL = "partial"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_PARTIAL, "Partial"),
        (STATUS_FAILED, "Failed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="maintenance_runs",
    )
    task_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "games_maintenancerunlog"
        ordering = ["-created_at"]
        verbose_name = "Maintenance Run Log"
        verbose_name_plural = "Maintenance Run Logs"
        permissions = [
            ("can_run_maintenance_tasks", "Can run system maintenance tasks"),
        ]

    def __str__(self):
        return f"{self.task_name} [{self.status}] at {self.created_at:%Y-%m-%d %H:%M}"
