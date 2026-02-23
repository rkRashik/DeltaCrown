"""
Tournament Sponsor Model — Hub Resources Module

Allows organizers to showcase sponsors within the Hub, providing premium
real estate for brand visibility. Sponsors are displayed in tier order
(Title → Gold → Silver → Bronze → Partner).

Created: February 2026
"""

from django.db import models
from apps.common.models import TimestampedModel


class TournamentSponsor(TimestampedModel):
    """
    Tournament sponsor with tier-based display.

    Sponsors are shown in the Hub Resources tab and optionally as
    banners in the sidebar or overview tab. Each sponsor belongs to
    a single tournament and has a display tier that controls sizing
    and prominence.

    Attributes:
        tournament: FK to the Tournament
        name: Sponsor display name
        tier: Display tier (title/gold/silver/bronze/partner)
        logo: Sponsor logo image
        website_url: Sponsor website link
        banner_image: Optional wide banner for premium placements
        description: Short blurb shown on hover/expand
        display_order: Manual sort within same tier
        is_active: Soft toggle for visibility
    """

    TIER_TITLE = 'title'
    TIER_GOLD = 'gold'
    TIER_SILVER = 'silver'
    TIER_BRONZE = 'bronze'
    TIER_PARTNER = 'partner'

    TIER_CHOICES = [
        (TIER_TITLE, 'Title Sponsor'),
        (TIER_GOLD, 'Gold Sponsor'),
        (TIER_SILVER, 'Silver Sponsor'),
        (TIER_BRONZE, 'Bronze Sponsor'),
        (TIER_PARTNER, 'Partner'),
    ]

    tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='sponsors',
        help_text='Tournament this sponsor is associated with',
    )
    name = models.CharField(
        max_length=200,
        help_text='Sponsor brand name',
    )
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default=TIER_PARTNER,
        db_index=True,
        help_text='Sponsor tier — controls display size and prominence',
    )
    logo = models.ImageField(
        upload_to='tournaments/sponsors/',
        null=True,
        blank=True,
        help_text='Sponsor logo (square or landscape, min 200×200)',
    )
    website_url = models.URLField(
        blank=True,
        default='',
        help_text='Sponsor website URL (opens in new tab)',
    )
    banner_image = models.ImageField(
        upload_to='tournaments/sponsors/banners/',
        null=True,
        blank=True,
        help_text='Wide banner image for premium placements (16:9 or 4:1)',
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text='Short description shown on hover or under the logo',
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text='Sort order within same tier (lower = first)',
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this sponsor is visible in the Hub',
    )

    class Meta:
        db_table = 'tournaments_sponsor'
        ordering = ['tier', 'display_order', 'name']
        verbose_name = 'Tournament Sponsor'
        verbose_name_plural = 'Tournament Sponsors'
        indexes = [
            models.Index(fields=['tournament', 'tier', 'display_order'], name='idx_sponsor_t_tier_order'),
            models.Index(fields=['tournament', 'is_active'], name='idx_sponsor_t_active'),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()}) — {self.tournament.name}"

    @property
    def logo_url(self):
        """Return logo URL or a placeholder."""
        if self.logo:
            return self.logo.url
        return ''

    @property
    def banner_url(self):
        """Return banner URL if exists."""
        if self.banner_image:
            return self.banner_image.url
        return ''
