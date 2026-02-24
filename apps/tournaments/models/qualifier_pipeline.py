"""
Qualifier Pipeline models for multi-wave tournament qualifiers.

TOC Sprint 5 — S5-M1, S5-M2, S5-M3
PRD Reference: §5.11 (Multi-Wave Qualifier Pipelines)

Links multiple tournament stages with automatic promotion rules,
enabling open qualifiers → regional finals → grand finals pipelines.
"""

import uuid

from django.db import models


class QualifierPipeline(models.Model):
    """
    A multi-stage qualifier pipeline linking tournament stages
    with automatic promotion rules.

    Statuses:
        draft     — pipeline configured, not active
        active    — pipeline running, stages in progress
        completed — all stages finished, final participants determined
        cancelled — pipeline cancelled
    """

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="qualifier_pipelines",
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Qualifier Pipeline"
        verbose_name_plural = "Qualifier Pipelines"

    def __str__(self):
        return f"{self.name} ({self.tournament})"


class PipelineStage(models.Model):
    """
    A single stage within a qualifier pipeline.
    Each stage links to a TournamentStage and defines
    the format and capacity for that wave.
    """

    FORMAT_CHOICES = [
        ("single_elimination", "Single Elimination"),
        ("double_elimination", "Double Elimination"),
        ("round_robin", "Round Robin"),
        ("swiss", "Swiss"),
        ("group_playoff", "Group Stage + Playoff"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pipeline = models.ForeignKey(
        QualifierPipeline,
        on_delete=models.CASCADE,
        related_name="stages",
    )
    tournament_stage = models.ForeignKey(
        "tournaments.TournamentStage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pipeline_stages",
    )
    name = models.CharField(max_length=200)
    format = models.CharField(max_length=30, choices=FORMAT_CHOICES)
    max_teams = models.PositiveIntegerField(default=0, help_text="0 = unlimited")
    order = models.PositiveIntegerField(
        default=0,
        help_text="Stage order within pipeline (0 = first).",
    )

    class Meta:
        ordering = ["order"]
        verbose_name = "Pipeline Stage"
        verbose_name_plural = "Pipeline Stages"
        unique_together = [("pipeline", "order")]

    def __str__(self):
        return f"{self.pipeline.name} → Stage {self.order}: {self.name}"


class PromotionRule(models.Model):
    """
    Defines how participants advance from one pipeline stage to the next.

    Criteria:
        top_n           — Top N by placement
        top_n_per_group — Top N from each group
        points_threshold — Minimum points to advance
        manual          — Organizer manually selects
    """

    CRITERIA_CHOICES = [
        ("top_n", "Top N"),
        ("top_n_per_group", "Top N per Group"),
        ("points_threshold", "Points Threshold"),
        ("manual", "Manual Selection"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    from_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.CASCADE,
        related_name="promotion_rules_out",
    )
    to_stage = models.ForeignKey(
        PipelineStage,
        on_delete=models.CASCADE,
        related_name="promotion_rules_in",
    )
    criteria = models.CharField(max_length=30, choices=CRITERIA_CHOICES)
    value = models.PositiveIntegerField(
        default=1,
        help_text="N for top_n/top_n_per_group, min points for threshold.",
    )
    auto_promote = models.BooleanField(
        default=False,
        help_text="Automatically promote when stage completes.",
    )

    class Meta:
        ordering = ["from_stage__order"]
        verbose_name = "Promotion Rule"
        verbose_name_plural = "Promotion Rules"

    def __str__(self):
        return f"{self.from_stage.name} → {self.to_stage.name} ({self.criteria})"
