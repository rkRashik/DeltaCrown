"""
Tournament Bounty model.

TOC Sprint 4 — S4-M1
PRD Reference: §4.10 (Custom Bounties & Special Prizes)

Non-placement prize allocations: MVP, stat leaders, community votes,
special achievements. Organizers define and assign bounties.
"""

import uuid

from django.conf import settings
from django.db import models


class TournamentBounty(models.Model):
    """
    Named, non-placement prize for a tournament.

    Source types:
        prize_pool — deducted from the main prize pool
        sponsor    — separately funded by a sponsor
        platform   — funded by DeltaCrown
    """

    TYPE_MVP = "mvp"
    TYPE_STAT_LEADER = "stat_leader"
    TYPE_COMMUNITY_VOTE = "community_vote"
    TYPE_SPECIAL_ACHIEVEMENT = "special_achievement"
    TYPE_CUSTOM = "custom"

    BOUNTY_TYPE_CHOICES = [
        (TYPE_MVP, "MVP"),
        (TYPE_STAT_LEADER, "Stat Leader"),
        (TYPE_COMMUNITY_VOTE, "Community Vote"),
        (TYPE_SPECIAL_ACHIEVEMENT, "Special Achievement"),
        (TYPE_CUSTOM, "Custom"),
    ]

    SOURCE_PRIZE_POOL = "prize_pool"
    SOURCE_SPONSOR = "sponsor"
    SOURCE_PLATFORM = "platform"

    SOURCE_CHOICES = [
        (SOURCE_PRIZE_POOL, "Prize Pool"),
        (SOURCE_SPONSOR, "Sponsor"),
        (SOURCE_PLATFORM, "Platform"),
    ]

    CLAIM_PENDING = "pending"
    CLAIM_CLAIMED = "claimed"
    CLAIM_PAID_OUT = "paid_out"

    CLAIM_STATUS_CHOICES = [
        (CLAIM_PENDING, "Pending"),
        (CLAIM_CLAIMED, "Claimed"),
        (CLAIM_PAID_OUT, "Paid Out"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    tournament = models.ForeignKey(
        "tournaments.Tournament",
        on_delete=models.CASCADE,
        related_name="bounties",
    )

    name = models.CharField(
        max_length=200,
        help_text='Bounty display name, e.g. "Tournament MVP".',
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Bounty criteria / description.",
    )
    bounty_type = models.CharField(
        max_length=30,
        choices=BOUNTY_TYPE_CHOICES,
        default=TYPE_CUSTOM,
    )

    prize_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Prize amount for this bounty.",
    )
    prize_currency = models.CharField(
        max_length=20,
        default="BDT",
        help_text="BDT or deltacoin.",
    )

    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_PRIZE_POOL,
    )
    sponsor_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Sponsor name if source == sponsor.",
    )

    is_assigned = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bounty_wins",
    )
    assigned_to_registration = models.ForeignKey(
        "tournaments.Registration",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bounty_awards",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bounties_assigned",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    assignment_reason = models.TextField(
        blank=True,
        default="",
        help_text="Justification for assigning.",
    )

    claim_status = models.CharField(
        max_length=20,
        choices=CLAIM_STATUS_CHOICES,
        default=CLAIM_PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "tournaments"
        ordering = ["-created_at"]
        verbose_name = "Tournament Bounty"
        verbose_name_plural = "Tournament Bounties"

    def __str__(self):
        return f"{self.name} ({self.tournament}) — {self.prize_amount} {self.prize_currency}"

    def assign(self, user, registration=None, assigned_by=None, reason=""):
        """Assign this bounty to a winner."""
        from django.utils import timezone

        self.is_assigned = True
        self.assigned_to = user
        self.assigned_to_registration = registration
        self.assigned_by = assigned_by
        self.assigned_at = timezone.now()
        self.assignment_reason = reason
        self.save(update_fields=[
            "is_assigned", "assigned_to", "assigned_to_registration",
            "assigned_by", "assigned_at", "assignment_reason",
        ])
