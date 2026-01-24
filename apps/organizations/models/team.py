"""
Team model for competitive esports squads.

A Team represents the competitive unit that registers for tournaments
and plays matches. Teams can be Independent (user-owned) or part of
an Organization (professional entity).
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify
from django.db.models import Q

from ..choices import TeamStatus

User = get_user_model()


class Team(models.Model):
    """
    Competitive unit that registers for tournaments and plays matches.
    
    Types:
    1. Organization Team: Owned by an Organization, managed by appointed Manager
    2. Independent Team: Owned by a single User (Captain/Owner)
    
    Constraints:
    - One User can own max 1 Independent Team per game title
    - One Organization can own unlimited Teams per game
    - Team names must be unique globally (slug uniqueness)
    - Must have EITHER organization OR owner (not both, not neither)
    
    Database Table: organizations_team
    """
    
    # Identity fields
    name = models.CharField(
        max_length=100,
        help_text="Team display name (e.g., 'Protocol V', 'Syntax FC')"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="URL-safe identifier (auto-generated from name)"
    )
    
    # Ownership (mutually exclusive: organization XOR owner)
    organization = models.ForeignKey(
        'Organization',
        on_delete=models.CASCADE,
        related_name='teams',
        null=True,
        blank=True,
        db_index=True,
        help_text="Owning organization (NULL if independent team)"
    )
    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_teams',
        null=True,
        blank=True,
        db_index=True,
        help_text="Owner user (NULL if organization-owned team)"
    )
    
    # Game context
    game_id = models.IntegerField(
        db_index=True,
        help_text="Game title ID (FK to games.Game - avoiding direct FK for now)"
    )
    region = models.CharField(
        max_length=50,
        help_text="Home region (e.g., 'Bangladesh', 'India') - identity, not server"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=TeamStatus.choices,
        default=TeamStatus.ACTIVE,
        db_index=True,
        help_text="Team lifecycle status"
    )
    
    # Branding assets
    logo = models.ImageField(
        upload_to='teams/logos/',
        null=True,
        blank=True,
        help_text="Team logo (or inherits from organization if enforce_brand=True)"
    )
    banner = models.ImageField(
        upload_to='teams/banners/',
        null=True,
        blank=True,
        help_text="Profile page header banner"
    )
    description = models.TextField(
        blank=True,
        help_text="Team bio/description"
    )
    
    # Tournament Operations Center (TOC) settings
    preferred_server = models.CharField(
        max_length=50,
        blank=True,
        help_text="TOC: Preferred game server (e.g., 'Singapore', 'Mumbai')"
    )
    emergency_contact_discord = models.CharField(
        max_length=50,
        blank=True,
        help_text="TOC: Discord handle for tournament emergencies"
    )
    emergency_contact_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="TOC: Phone number for tournament emergencies"
    )
    
    # Metadata
    is_temporary = models.BooleanField(
        default=False,
        help_text="Created during tournament registration (clean up after tournament)"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Team creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp"
    )
    
    class Meta:
        db_table = 'organizations_team'
        ordering = ['-created_at']
        
        constraints = [
            # Independent teams: One owner per game (can't own 2 Valorant teams)
            models.UniqueConstraint(
                fields=['owner', 'game_id'],
                condition=Q(owner__isnull=False, status=TeamStatus.ACTIVE),
                name='one_independent_team_per_game'
            ),
            # Must have either organization OR owner (not both, not neither)
            models.CheckConstraint(
                check=(
                    Q(organization__isnull=False, owner__isnull=True) | 
                    Q(organization__isnull=True, owner__isnull=False)
                ),
                name='team_has_organization_xor_owner'
            ),
        ]
        
        indexes = [
            models.Index(fields=['slug'], name='team_slug_idx'),
            models.Index(fields=['game_id', 'region'], name='team_game_region_idx'),
            models.Index(fields=['organization'], name='team_org_idx'),
            models.Index(fields=['status'], name='team_status_idx'),
            models.Index(fields=['owner', 'game_id'], name='team_owner_game_idx'),
        ]
        
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
    
    def __str__(self):
        """Return team name for admin display."""
        if self.organization:
            return f"{self.organization.name} - {self.name}"
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            
            # Ensure slug uniqueness
            while Team.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """
        Return canonical URL (organization-prefixed or independent).
        
        Examples:
        - Organization team: /orgs/syntax/teams/protocol-v/
        - Independent team: /teams/my-team-slug/
        
        Returns:
            str: Absolute URL path
        """
        if self.organization:
            return reverse('organizations:org_team_detail', kwargs={
                'org_slug': self.organization.slug,
                'team_slug': self.slug
            })
        else:
            return reverse('organizations:team_detail', kwargs={'slug': self.slug})
    
    def is_organization_team(self):
        """
        Check if team is owned by an organization.
        
        Returns:
            bool: True if organization-owned, False if independent
        """
        return self.organization is not None
    
    def get_effective_logo_url(self):
        """
        Return logo URL (team logo or inherited org logo).
        
        If organization enforces branding, returns organization logo.
        Otherwise returns team logo or default placeholder.
        
        Returns:
            str: Logo URL path
        """
        if self.organization and self.organization.enforce_brand:
            if self.organization.logo:
                return self.organization.logo.url
        
        if self.logo:
            return self.logo.url
        
        return '/static/images/default_team_logo.png'
    
    def can_user_manage(self, user):
        """
        Check if user has management permissions for this team.
        
        For organization teams: CEO or team Manager/Coach
        For independent teams: Owner only
        
        Args:
            user: User instance to check permissions for
            
        Returns:
            bool: True if user can manage team settings
        """
        if self.organization:
            # Organization team: CEO or Manager
            if user == self.organization.ceo:
                return True
            
            # Check if user is Manager or Coach of this team
            return self.memberships.filter(
                user=user,
                status='ACTIVE',
                role__in=['MANAGER', 'COACH']
            ).exists()
        else:
            # Independent team: Owner only
            return user == self.owner
