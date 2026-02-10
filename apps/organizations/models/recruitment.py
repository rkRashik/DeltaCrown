"""
Recruitment models — Job Post builder for team scouting.

RecruitmentPosition: Open roster slots a team is looking to fill.
RecruitmentRequirement: Structured requirements for applicants.

These power the Scouting Grounds "Job Post" builder in Manage HQ,
and feed the public "Join the Ranks" widget on the team detail page.
"""

from django.db import models


class RecruitmentPosition(models.Model):
    """
    An open position the team is actively recruiting for.

    Examples: "Entry Fragger", "IGL / Shot-Caller", "Flex Support",
              "Head Coach", "Analyst", "Content Creator".
    """

    class RoleCategory(models.TextChoices):
        FLEX = 'FLEX', 'Flex'
        IGL = 'IGL', 'IGL / Shot-Caller'
        ENTRY = 'ENTRY', 'Entry Fragger'
        SNIPER = 'SNIPER', 'Sniper / AWPer'
        SUPPORT = 'SUPPORT', 'Support'
        LURKER = 'LURKER', 'Lurker'
        CONTROLLER = 'CONTROLLER', 'Controller'
        SENTINEL = 'SENTINEL', 'Sentinel'
        DUELIST = 'DUELIST', 'Duelist'
        INITIATOR = 'INITIATOR', 'Initiator'
        TANK = 'TANK', 'Tank'
        DPS = 'DPS', 'DPS'
        HEALER = 'HEALER', 'Healer'
        COACH = 'COACH', 'Coach'
        ANALYST = 'ANALYST', 'Analyst'
        MANAGER = 'MANAGER', 'Manager'
        CONTENT = 'CONTENT', 'Content Creator'
        OTHER = 'OTHER', 'Other'

    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='recruitment_positions',
    )
    title = models.CharField(
        max_length=60,
        help_text='Position title (e.g. "Entry Fragger", "IGL")',
    )
    role_category = models.CharField(
        max_length=20,
        choices=RoleCategory.choices,
        default=RoleCategory.OTHER,
        blank=True,
        help_text='Standardized role category (Flex, IGL, Sniper…)',
    )
    rank_requirement = models.CharField(
        max_length=60,
        blank=True,
        default='',
        help_text='Minimum rank (e.g. "Immortal 3+", "Diamond+")',
    )
    region = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text='Region for this position (auto-filled from team, editable)',
    )
    platform = models.CharField(
        max_length=30,
        blank=True,
        default='',
        help_text='Platform for this position (auto-filled from team, editable)',
    )
    short_pitch = models.CharField(
        max_length=140,
        blank=True,
        default='',
        help_text='Short description / pitch for the listing (max 140 chars)',
    )
    cross_post_community = models.BooleanField(
        default=False,
        help_text='If True, this position is published to the global community feed',
    )
    description = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Brief description of the role',
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether this position is currently open',
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organizations_recruitment_position'
        ordering = ['sort_order', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['team', 'title'],
                condition=models.Q(is_active=True),
                name='unique_active_position_per_team',
            ),
        ]

    def __str__(self):
        status = '✓' if self.is_active else '✗'
        return f'{status} {self.title} — {self.team.name}'


class RecruitmentRequirement(models.Model):
    """
    A structured requirement for prospective team members.

    Examples:
        label="Minimum Rank"     value="Diamond+"
        label="Age"              value="16+"
        label="Language"         value="English / Spanish"
        label="Availability"     value="5+ evenings/week"
        label="Region"           value="NA East"
    """
    team = models.ForeignKey(
        'organizations.Team',
        on_delete=models.CASCADE,
        related_name='recruitment_requirements',
    )
    label = models.CharField(
        max_length=40,
        help_text='Requirement category (e.g. "Minimum Rank")',
    )
    value = models.CharField(
        max_length=100,
        help_text='Requirement detail (e.g. "Diamond+")',
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organizations_recruitment_requirement'
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return f'{self.label}: {self.value} — {self.team.name}'
