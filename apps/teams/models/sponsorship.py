"""
Team Sponsorship Models
Handles sponsor relationships, merchandise, and team promotions
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, URLValidator
from django.utils import timezone
from django.utils.text import slugify
from decimal import Decimal


class TeamSponsor(models.Model):
    """
    Represents a sponsor relationship with a team
    """
    
    TIER_CHOICES = [
        ('platinum', 'Platinum'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('partner', 'Partner'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Relationships
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='sponsors',
        help_text='Team receiving sponsorship'
    )
    
    # Sponsor Information
    sponsor_name = models.CharField(max_length=200)
    sponsor_logo = models.ImageField(
        upload_to='sponsors/logos/',
        blank=True,
        null=True,
        help_text="Sponsor logo image"
    )
    sponsor_logo_url = models.URLField(
        blank=True,
        validators=[URLValidator()],
        help_text="External URL for sponsor logo (if not uploaded)"
    )
    sponsor_link = models.URLField(
        validators=[URLValidator()],
        help_text="Link to sponsor website"
    )
    sponsor_tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        default='bronze'
    )
    
    # Contact Information
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    
    # Duration & Status
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    is_active = models.BooleanField(default=False)
    
    # Financial
    deal_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        blank=True,
        null=True,
        help_text="Sponsorship deal value"
    )
    currency = models.CharField(max_length=3, default='USD')
    
    # Analytics
    click_count = models.PositiveIntegerField(default=0)
    impression_count = models.PositiveIntegerField(default=0)
    
    # Additional Details
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about the sponsorship"
    )
    benefits = models.TextField(
        blank=True,
        help_text="Benefits provided to sponsor"
    )
    
    # Display Settings
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Order in which sponsors are displayed (lower = first)"
    )
    show_on_profile = models.BooleanField(
        default=True,
        help_text="Display sponsor on team profile"
    )
    show_on_jerseys = models.BooleanField(
        default=False,
        help_text="Display sponsor logo on team jerseys"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_sponsors'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['team', 'display_order', '-start_date']
        indexes = [
            models.Index(fields=['team', 'status']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]
        verbose_name = 'Team Sponsor'
        verbose_name_plural = 'Team Sponsors'
    
    def __str__(self):
        return f"{self.sponsor_name} - {self.team.name} ({self.get_sponsor_tier_display()})"
    
    def save(self, *args, **kwargs):
        """Auto-update is_active based on dates and status"""
        if self.status == 'active':
            today = timezone.now().date()
            if self.start_date <= today <= self.end_date:
                self.is_active = True
            else:
                self.is_active = False
        else:
            self.is_active = False
        
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if sponsorship has expired"""
        return timezone.now().date() > self.end_date
    
    def days_remaining(self):
        """Calculate days remaining in sponsorship"""
        if self.is_expired():
            return 0
        return (self.end_date - timezone.now().date()).days
    
    def increment_clicks(self):
        """Increment click counter"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    def increment_impressions(self):
        """Increment impression counter"""
        self.impression_count += 1
        self.save(update_fields=['impression_count'])
    
    def get_logo_url(self):
        """Get logo URL (uploaded or external)"""
        if self.sponsor_logo:
            return self.sponsor_logo.url
        return self.sponsor_logo_url
    
    def approve(self, user):
        """Approve sponsorship"""
        self.status = 'active'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def reject(self):
        """Reject sponsorship"""
        self.status = 'rejected'
        self.is_active = False
        self.save()
    
    def cancel(self):
        """Cancel sponsorship"""
        self.status = 'cancelled'
        self.is_active = False
        self.save()


class SponsorInquiry(models.Model):
    """
    Represents a sponsor inquiry from a potential sponsor
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('contacted', 'Contacted'),
        ('negotiating', 'Negotiating'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    # Target Team
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='sponsor_inquiries'
    )
    
    # Inquiry Details
    company_name = models.CharField(max_length=200)
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True, validators=[URLValidator()])
    
    # Sponsorship Interest
    interested_tier = models.CharField(
        max_length=20,
        choices=TeamSponsor.TIER_CHOICES,
        blank=True
    )
    budget_range = models.CharField(max_length=100, blank=True)
    message = models.TextField(help_text="Why they want to sponsor")
    
    # Additional Info
    industry = models.CharField(max_length=100, blank=True)
    company_size = models.CharField(
        max_length=50,
        blank=True,
        help_text="Number of employees or revenue range"
    )
    previous_sponsorships = models.TextField(
        blank=True,
        help_text="Previous esports/gaming sponsorships"
    )
    
    # Status & Processing
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_inquiries'
    )
    admin_notes = models.TextField(blank=True)
    
    # Spam Prevention
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)
    
    # Conversion
    converted_to_sponsor = models.ForeignKey(
        TeamSponsor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_inquiry'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['team', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['contact_email']),
        ]
        verbose_name = 'Sponsor Inquiry'
        verbose_name_plural = 'Sponsor Inquiries'
    
    def __str__(self):
        return f"{self.company_name} → {self.team.name}"
    
    def mark_contacted(self, user=None):
        """Mark inquiry as contacted"""
        self.status = 'contacted'
        self.responded_at = timezone.now()
        if user:
            self.assigned_to = user
        self.save()
    
    def convert_to_sponsor(self, sponsor):
        """Link inquiry to created sponsor"""
        self.converted_to_sponsor = sponsor
        self.status = 'approved'
        self.save()


class TeamMerchItem(models.Model):
    """
    Represents merchandise items for a team
    """
    
    CATEGORY_CHOICES = [
        ('jersey', 'Jersey'),
        ('hoodie', 'Hoodie'),
        ('tshirt', 'T-Shirt'),
        ('cap', 'Cap'),
        ('accessory', 'Accessory'),
        ('collectible', 'Collectible'),
        ('digital', 'Digital Item'),
        ('other', 'Other'),
    ]
    
    # Relationships
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='merchandise'
    )
    
    # Product Info
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, blank=True)
    sku = models.CharField(
        max_length=100,
        unique=True,
        help_text="Stock Keeping Unit"
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='tshirt'
    )
    description = models.TextField()
    
    # Pricing
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        blank=True,
        null=True,
        help_text="Discounted price if on sale"
    )
    
    # Inventory
    stock = models.PositiveIntegerField(
        default=0,
        help_text="Available quantity"
    )
    is_in_stock = models.BooleanField(default=True)
    unlimited_stock = models.BooleanField(
        default=False,
        help_text="Digital items or print-on-demand"
    )
    
    # Media
    image = models.ImageField(
        upload_to='merchandise/',
        blank=True,
        null=True
    )
    image_url = models.URLField(
        blank=True,
        validators=[URLValidator()],
        help_text="External image URL"
    )
    
    # External Integration
    external_link = models.URLField(
        blank=True,
        validators=[URLValidator()],
        help_text="Link to external store (e.g., Shopify, Teespring)"
    )
    affiliate_link = models.URLField(
        blank=True,
        validators=[URLValidator()],
        help_text="Affiliate tracking link"
    )
    
    # Variants (simple approach)
    has_variants = models.BooleanField(
        default=False,
        help_text="Has sizes/colors"
    )
    variant_options = models.JSONField(
        default=dict,
        blank=True,
        help_text='{"sizes": ["S", "M", "L"], "colors": ["Black", "White"]}'
    )
    
    # Display Settings
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    
    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['team', 'display_order', '-created_at']
        indexes = [
            models.Index(fields=['team', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['is_featured', 'is_active']),
        ]
        verbose_name = 'Team Merchandise Item'
        verbose_name_plural = 'Team Merchandise Items'
    
    def __str__(self):
        return f"{self.title} - {self.team.name}"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug and update stock status"""
        if not self.slug:
            self.slug = slugify(f"{self.team.slug}-{self.title}")
        
        # Update stock status
        if not self.unlimited_stock:
            self.is_in_stock = self.stock > 0
        
        super().save(*args, **kwargs)
    
    def get_price(self):
        """Get current price (sale price if available)"""
        if self.sale_price and self.sale_price < self.price:
            return self.sale_price
        return self.price
    
    def is_on_sale(self):
        """Check if item is on sale"""
        return self.sale_price and self.sale_price < self.price
    
    def get_image_url(self):
        """Get image URL (uploaded or external)"""
        if self.image:
            return self.image.url
        return self.image_url
    
    def increment_views(self):
        """Increment view counter"""
        self.view_count += 1
        self.save(update_fields=['view_count'])
    
    def increment_clicks(self):
        """Increment click counter"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    def reduce_stock(self, quantity=1):
        """Reduce stock after purchase"""
        if not self.unlimited_stock:
            self.stock = max(0, self.stock - quantity)
            self.is_in_stock = self.stock > 0
            self.save(update_fields=['stock', 'is_in_stock'])


class TeamPromotion(models.Model):
    """
    Represents paid promotions for teams (featured placement, ads, etc.)
    """
    
    PROMOTION_TYPES = [
        ('featured_homepage', 'Featured on Homepage'),
        ('featured_hub', 'Featured in Team Hub'),
        ('banner_ad', 'Banner Advertisement'),
        ('spotlight', 'Team Spotlight'),
        ('boosted_ranking', 'Boosted in Rankings'),
        ('social_media', 'Social Media Feature'),
        ('newsletter', 'Newsletter Feature'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    # Relationships
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='promotions'
    )
    
    # Promotion Details
    promotion_type = models.CharField(
        max_length=30,
        choices=PROMOTION_TYPES
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Scheduling
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    is_active = models.BooleanField(default=False)
    
    # Pricing
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    currency = models.CharField(max_length=3, default='USD')
    
    # Payment
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    transaction_ref = models.CharField(
        max_length=200,
        blank=True,
        help_text="Payment gateway transaction ID"
    )
    payment_method = models.CharField(max_length=50, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    # Analytics
    impression_count = models.PositiveIntegerField(default=0)
    click_count = models.PositiveIntegerField(default=0)
    conversion_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of conversions (follows, visits, etc.)"
    )
    
    # Admin Management
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_promotions'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_at']
        indexes = [
            models.Index(fields=['team', 'status']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['start_at', 'end_at']),
            models.Index(fields=['promotion_type', 'is_active']),
        ]
        verbose_name = 'Team Promotion'
        verbose_name_plural = 'Team Promotions'
    
    def __str__(self):
        return f"{self.team.name} - {self.get_promotion_type_display()} ({self.start_at.date()})"
    
    def save(self, *args, **kwargs):
        """Auto-update is_active based on dates and status"""
        if self.status in ['paid', 'active']:
            now = timezone.now()
            if self.start_at <= now <= self.end_at:
                self.is_active = True
                self.status = 'active'
            elif now > self.end_at:
                self.is_active = False
                self.status = 'completed'
            else:
                self.is_active = False
        else:
            self.is_active = False
        
        super().save(*args, **kwargs)
    
    def is_expired(self):
        """Check if promotion has expired"""
        return timezone.now() > self.end_at
    
    def days_remaining(self):
        """Calculate days remaining"""
        if self.is_expired():
            return 0
        return (self.end_at - timezone.now()).days
    
    def approve(self, user):
        """Approve promotion"""
        self.status = 'paid'
        self.approved_by = user
        self.approved_at = timezone.now()
        self.save()
    
    def increment_impressions(self):
        """Increment impression counter"""
        self.impression_count += 1
        self.save(update_fields=['impression_count'])
    
    def increment_clicks(self):
        """Increment click counter"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    def increment_conversions(self):
        """Increment conversion counter"""
        self.conversion_count += 1
        self.save(update_fields=['conversion_count'])
    
    def get_ctr(self):
        """Calculate click-through rate"""
        if self.impression_count == 0:
            return 0
        return (self.click_count / self.impression_count) * 100
    
    def get_conversion_rate(self):
        """Calculate conversion rate"""
        if self.click_count == 0:
            return 0
        return (self.conversion_count / self.click_count) * 100
