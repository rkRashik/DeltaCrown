"""
Team Journey milestones — owner/staff-curated timeline entries.

TeamJourneyMilestone represents a curated milestone that team staff
define and control. These are separate from the auto-generated
TeamActivityLog entries and provide full editorial control over
what appears in the public "The Journey" timeline.

Max 5 entries shown on the public detail page (most recent first).
"""

from django.conf import settings
from django.db import models


class TeamJourneyMilestone(models.Model):
    """
    A curated journey milestone for the team's public timeline.
    
    Unlike auto-generated TeamActivityLog entries, these are fully
    controlled by team owners/staff and have custom titles, descriptions,
    and display dates.
    """

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='journey_milestones',
        db_index=True,
    )
    title = models.CharField(
        max_length=120,
        help_text='Milestone headline (e.g., "Qualified for Ascension Pacific")',
    )
    description = models.TextField(
        blank=True,
        default='',
        max_length=500,
        help_text='Optional details about this milestone (max 500 chars)',
    )
    milestone_date = models.DateField(
        help_text='When this milestone occurred',
    )
    is_visible = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this milestone appears on the public detail page',
    )
    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text='Lower values appear first (0 = auto-sort by date)',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organizations_journey_milestone'
        ordering = ['-milestone_date', '-created_at']
        verbose_name = 'Journey Milestone'
        verbose_name_plural = 'Journey Milestones'

    def __str__(self):
        return f"{self.team.name} — {self.title} ({self.milestone_date})"
