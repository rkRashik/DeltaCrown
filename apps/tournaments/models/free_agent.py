"""
Free Agent Registration model.

TOC Sprint 3 — S3-M2
PRD Reference: §3.12 (Free Agent / LFG Pool)

Solo players register as Free Agents for team-based tournaments.
Organizers can assign free agents to mix teams or enable captain drafting.
"""

import uuid

from django.conf import settings
from django.db import models


class FreeAgentRegistration(models.Model):
    """
    A solo player's free-agent entry in a team-based tournament.

    Statuses:
        available  — in pool, unmatched
        drafted    — drafted by a captain (captain_draft mode)
        assigned   — assigned to a team by organizer
        self_formed — formed a team via self_form mode
        withdrawn  — player withdrew from FA pool
        expired    — deadline passed without match
    """

    STATUS_AVAILABLE = "available"
    STATUS_DRAFTED = "drafted"
    STATUS_ASSIGNED = "assigned"
    STATUS_SELF_FORMED = "self_formed"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_DRAFTED, "Drafted"),
        (STATUS_ASSIGNED, "Assigned"),
        (STATUS_SELF_FORMED, "Self-Formed"),
        (STATUS_WITHDRAWN, "Withdrawn"),
        (STATUS_EXPIRED, "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="free_agent_registrations",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="free_agent_registrations",
    )
    registration = models.ForeignKey(
        "tournaments.Registration",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="free_agent_source",
        help_text="Created once assigned to a team.",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_AVAILABLE,
        db_index=True,
    )

    preferred_role = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text='In-game role, e.g. "IGL", "Entry Fragger", "Support".',
    )
    rank_info = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text='Self-reported rank, e.g. "Diamond 3", "Heroic".',
    )
    bio = models.TextField(
        blank=True,
        default="",
        help_text="Short pitch text.",
    )
    availability_notes = models.TextField(
        blank=True,
        default="",
        help_text="Schedule constraints.",
    )
    game_id = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="In-game name / IGN.",
    )

    drafted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="drafted_free_agents",
        help_text="Captain who drafted this FA.",
    )
    assigned_to_team = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="free_agent_assignments",
        help_text="Team the FA was assigned to.",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tournaments"
        ordering = ["-created_at"]
        unique_together = [("tournament", "user")]
        verbose_name = "Free Agent Registration"
        verbose_name_plural = "Free Agent Registrations"

    def __str__(self):
        return f"FreeAgent({self.user}) in {self.tournament} [{self.status}]"

    @property
    def is_available(self):
        return self.status == self.STATUS_AVAILABLE

    def assign_to_team(self, team, assigned_by=None):
        """Assign this free agent to a team."""
        from django.utils import timezone

        self.status = self.STATUS_ASSIGNED
        self.assigned_to_team = team
        self.assigned_at = timezone.now()
        if assigned_by:
            self.drafted_by = assigned_by
        self.save(update_fields=["status", "assigned_to_team", "assigned_at", "drafted_by"])

    def withdraw(self):
        """Player withdraws from the free agent pool."""
        self.status = self.STATUS_WITHDRAWN
        self.save(update_fields=["status"])
