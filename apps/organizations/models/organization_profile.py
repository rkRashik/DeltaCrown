"""
OrganizationProfile model for extended organization metadata.

This model stores additional organization information that doesn't
belong in the core Organization model, keeping it clean and focused.
"""

from django.db import models


class OrganizationProfile(models.Model):
    """
    Extended metadata for organizations.
    
    Stores additional information from the organization creation wizard
    that doesn't fit in the core Organization model.
    
    Database Table: organizations_organizationprofile
    """
    
    organization = models.OneToOneField(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='profile',
        primary_key=True,
        help_text="Organization this profile belongs to"
    )
    
    # Operations fields (Step 2)
    founded_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Year organization was founded"
    )
    organization_type = models.CharField(
        max_length=20,
        choices=[
            ('club', 'Esports Club (Casual)'),
            ('pro', 'Pro Organization'),
            ('guild', 'Community Guild'),
        ],
        default='club',
        help_text="Organization classification"
    )
    hq_city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City where organization is based"
    )
    hq_address = models.TextField(
        blank=True,
        help_text="Full headquarters address (for Pro orgs)"
    )
    business_email = models.EmailField(
        blank=True,
        help_text="Official business email (for Pro orgs)"
    )
    trade_license = models.CharField(
        max_length=100,
        blank=True,
        help_text="Trade license / BIN / TIN number"
    )
    
    # Social links (Step 2)
    discord_link = models.URLField(
        blank=True,
        help_text="Discord community invite link"
    )
    instagram = models.CharField(
        max_length=100,
        blank=True,
        help_text="Instagram handle or URL"
    )
    facebook = models.URLField(
        blank=True,
        help_text="Facebook page URL"
    )
    youtube = models.URLField(
        blank=True,
        help_text="YouTube channel URL"
    )
    
    # Location (Step 2)
    region_code = models.CharField(
        max_length=3,
        default='BD',
        help_text="ISO country code (e.g., BD, US, SG)"
    )
    
    # Treasury fields (Step 3)
    currency = models.CharField(
        max_length=3,
        default='BDT',
        help_text="Primary ledger currency (BDT, USD, etc.)"
    )
    payout_method = models.CharField(
        max_length=20,
        choices=[
            ('mobile', 'Mobile Banking'),
            ('bank', 'Bank Transfer'),
        ],
        default='mobile',
        help_text="Primary payout method for prize money"
    )
    
    # Branding (Step 4)
    brand_color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Primary brand color (hex code, e.g., #FFD700)"
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Profile creation timestamp"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last modification timestamp"
    )
    
    class Meta:
        db_table = 'organizations_organizationprofile'
        verbose_name = 'Organization Profile'
        verbose_name_plural = 'Organization Profiles'
    
    def __str__(self):
        """Return organization name for admin display."""
        return f"{self.organization.name} Profile"
