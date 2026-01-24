"""
Organization model for professional esports brands.

An Organization represents a verified business entity that can own
multiple teams across different games (e.g., SYNTAX, Cloud9 Bangladesh).
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.text import slugify

User = get_user_model()


class Organization(models.Model):
    """
    Verified business entity owning multiple esports teams.
    
    Organizations enable professional workflows:
    - Multi-team management (Main + Academy rosters)
    - Master Wallet for prize money consolidation
    - Brand inheritance (logo, colors, sponsors)
    - Revenue splits via Smart Contracts
    - Verified Org Badge for credibility
    
    Lifecycle:
    - Created by Users wanting to manage professional operations
    - Can acquire existing Independent Teams
    - Cannot be deleted while owning active teams
    - Maintains historical trophy room aggregating team achievements
    
    Database Table: organizations_organization
    """
    
    # Identity fields
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Organization legal/brand name (e.g., 'SYNTAX', 'Cloud9 Bangladesh')"
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="URL-safe identifier (auto-generated from name)"
    )
    
    # Ownership
    ceo = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='owned_organizations',
        db_index=True,
        help_text="Organization owner (full control)"
    )
    
    # Verification status
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Verified Org Badge status (granted by platform admins)"
    )
    verification_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date verification was granted"
    )
    
    # Branding assets
    logo = models.ImageField(
        upload_to='organizations/logos/',
        null=True,
        blank=True,
        help_text="Organization logo (inherited by teams if enforce_brand=True)"
    )
    badge = models.ImageField(
        upload_to='organizations/badges/',
        null=True,
        blank=True,
        help_text="Verified badge overlay"
    )
    banner = models.ImageField(
        upload_to='organizations/banners/',
        null=True,
        blank=True,
        help_text="Profile page header banner"
    )
    
    # Description and social links
    description = models.TextField(
        blank=True,
        help_text="Organization bio/mission statement"
    )
    website = models.URLField(
        blank=True,
        help_text="Official organization website"
    )
    twitter = models.CharField(
        max_length=50,
        blank=True,
        help_text="Twitter handle (without @)"
    )
    
    # Financial configuration
    master_wallet_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Prize money destination (FK to economy.Wallet - Phase 3)"
    )
    revenue_split_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Smart contract revenue splits (e.g., {'team': 70, 'org': 30})"
    )
    
    # Brand enforcement
    enforce_brand = models.BooleanField(
        default=False,
        help_text="Force teams to use organization logo (disable custom team logos)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Organization creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp"
    )
    
    class Meta:
        db_table = 'organizations_organization'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug'], name='org_slug_idx'),
            models.Index(fields=['ceo'], name='org_ceo_idx'),
            models.Index(fields=['is_verified'], name='org_verified_idx'),
        ]
        verbose_name = 'Organization'
        verbose_name_plural = 'Organizations'
    
    def __str__(self):
        """Return organization name for admin display."""
        verified_badge = '✓' if self.is_verified else ''
        return f"{self.name} {verified_badge}".strip()
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """
        Return canonical URL for organization profile.
        
        Example: /orgs/syntax/
        """
        return reverse('organizations:organization_detail', kwargs={'org_slug': self.slug})
    
    def get_active_teams(self):
        """
        Return queryset of active teams (excludes deleted/temporary).
        
        Returns:
            QuerySet[Team]: Active teams owned by this organization
        """
        return self.teams.filter(status='ACTIVE', is_temporary=False)
    
    def can_user_manage(self, user):
        """
        Check if user has management permissions for this organization.
        
        Args:
            user: User instance to check permissions for
            
        Returns:
            bool: True if user is CEO or platform staff
        """
        return user == self.ceo or user.is_staff


class OrganizationMembership(models.Model):
    """
    Organization-level staff assignments (CEO, Managers, Scouts).
    
    Separate from team-level memberships. Organization staff can have
    cross-team permissions (e.g., Scouts view all teams' player stats).
    
    Database Table: organizations_org_membership
    """
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='staff_memberships',
        help_text="Organization this staff member belongs to"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organization_memberships',
        help_text="User with organization-level access"
    )
    role = models.CharField(
        max_length=20,
        choices=[
            ('CEO', 'CEO (Owner)'),
            ('MANAGER', 'Manager'),
            ('SCOUT', 'Scout'),
            ('ANALYST', 'Analyst'),
        ],
        help_text="Organization-level role"
    )
    permissions = models.JSONField(
        default=dict,
        blank=True,
        help_text="Custom permission overrides (e.g., {'can_create_teams': True})"
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date user joined organization staff"
    )
    
    class Meta:
        db_table = 'organizations_org_membership'
        unique_together = [['organization', 'user']]
        indexes = [
            models.Index(fields=['organization', 'role'], name='orgmem_org_role_idx'),
            models.Index(fields=['user'], name='orgmem_user_idx'),
        ]
        verbose_name = 'Organization Membership'
        verbose_name_plural = 'Organization Memberships'
    
    def __str__(self):
        """Return human-readable membership representation."""
        return f"{self.user.username} - {self.role} at {self.organization.name}"
