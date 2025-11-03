from __future__ import annotations

import os
import uuid
from django.db import models
from django.conf import settings


def evidence_upload_path(instance: "MatchDisputeEvidence", filename: str) -> str:
    base, ext = os.path.splitext(filename or "")
    safe_ext = (ext or "").lower()[:8]
    uid = uuid.uuid4().hex
    return f"evidence/{instance.dispute_id}/{uid}{safe_ext}"


class MatchDisputeEvidence(models.Model):
    dispute = models.ForeignKey(
        "tournaments.MatchDispute",
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    file = models.FileField(upload_to=evidence_upload_path)
    content_type = models.CharField(max_length=64, blank=True, default="")
    size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_evidence",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Evidence #{self.id} for dispute {self.dispute_id}"

