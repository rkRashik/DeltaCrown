from django.db import models
from django.urls import reverse
from django.utils import timezone
from apps.user_profile.models import UserProfile
from decimal import Decimal
import uuid

class Category(models.Model):
    CATEGORY_TYPES = [
        ('featured', 'Featured Collections'),
        ('merchandise', 'Esports Lifestyle'),
        ('digital', 'Subscriptions & Utilities'),
        ('exclusive', 'Member Exclusive'),
        ('limited', 'Limited Edition'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES, default='merchandise')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        app_label = 'ecommerce'
        verbose_name_plural = 'Categories'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('ecommerce:category_detail', kwargs={'slug': self.slug})

class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="brands/", blank=True, null=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'ecommerce'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    PRODUCT_TYPES = [
        ('physical', 'Physical Product'),
        ('digital', 'Digital Product'),
        ('subscription', 'Subscription'),
        ('bundle', 'Bundle'),
    ]
    
    RARITY_LEVELS = [
        ('common', 'Common'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
        ('mythic', 'Mythic'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    short_description = models.CharField(max_length=255, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2)
    original_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    discount_percentage = models.PositiveIntegerField(default=0)
    
    # Product details
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPES, default='physical')
    rarity = models.CharField(max_length=20, choices=RARITY_LEVELS, default='common')
    
    # Images
    featured_image = models.ImageField(upload_to="products/", blank=True, null=True)
    hover_image = models.ImageField(upload_to="products/", blank=True, null=True)
    
    # Inventory
    stock = models.PositiveIntegerField(default=0)
    track_stock = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    
    # Features
    is_featured = models.BooleanField(default=False)
    is_digital = models.BooleanField(default=False)
    is_member_exclusive = models.BooleanField(default=False)
    is_limited_edition = models.BooleanField(default=False)
    limited_quantity = models.PositiveIntegerField(blank=True, null=True)
    
    # SEO and metadata
    meta_title = models.CharField(max_length=200, blank=True)
    meta_description = models.CharField(max_length=300, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Gaming related
    compatible_games = models.CharField(max_length=255, blank=True, help_text="Comma-separated game names")
    esports_team = models.CharField(max_length=100, blank=True)
    
    class Meta:
        app_label = 'ecommerce'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('ecommerce:product_detail', kwargs={'slug': self.slug})
    
    @property
    def discount_amount(self):
        if self.original_price:
            return self.original_price - self.price
        return Decimal('0.00')
    
    @property
    def is_on_sale(self):
        return self.original_price and self.original_price > self.price
    
    @property
    def is_in_stock(self):
        if not self.track_stock:
            return True
        return self.stock > 0 or self.allow_backorder
    
    @property
    def rarity_color(self):
        colors = {
            'common': '#94a3b8',
            'rare': '#3b82f6',
            'epic': '#8b5cf6',
            'legendary': '#f59e0b',
            'mythic': '#ef4444',
        }
        return colors.get(self.rarity, '#94a3b8')

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to="products/")
    alt_text = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta:
        app_label = 'ecommerce'
        ordering = ['sort_order', 'id']
    
    def __str__(self):
        return f"{self.product.name} - Image {self.id}"

class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=50, blank=True)
    material = models.CharField(max_length=100, blank=True)
    sku = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        app_label = 'ecommerce'
    
    def __str__(self):
        return f"{self.product.name} - {self.name}"

class Cart(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        app_label = 'ecommerce'
    
    def __str__(self):
        return f"Cart for {self.user.display_name}"
    
    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())
    
    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'ecommerce'
        unique_together = ['cart', 'product', 'variant']
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name}"
    
    @property
    def unit_price(self):
        base_price = self.product.price
        if self.variant:
            base_price += self.variant.price_adjustment
        return base_price
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending Payment"),
        ("processing", "Processing"),
        ("paid", "Paid"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
        ("refunded", "Refunded"),
    ]
    
    PAYMENT_METHODS = [
        ('delta_coins', 'DeltaCrown Coins'),
        ('credit_card', 'Credit Card'),
        ('paypal', 'PayPal'),
        ('crypto', 'Cryptocurrency'),
    ]
    
    # Order identification
    order_number = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='orders')
    
    # Order details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='delta_coins')
    
    # Pricing
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Addresses
    billing_name = models.CharField(max_length=100)
    billing_email = models.EmailField()
    billing_phone = models.CharField(max_length=20, blank=True)
    billing_address = models.TextField()
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=100)
    billing_zip = models.CharField(max_length=20)
    billing_country = models.CharField(max_length=100)
    
    shipping_name = models.CharField(max_length=100, blank=True)
    shipping_address = models.TextField(blank=True)
    shipping_city = models.CharField(max_length=100, blank=True)
    shipping_state = models.CharField(max_length=100, blank=True)
    shipping_zip = models.CharField(max_length=20, blank=True)
    shipping_country = models.CharField(max_length=100, blank=True)
    
    # Additional info
    notes = models.TextField(blank=True)
    tracking_number = models.CharField(max_length=100, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        app_label = 'ecommerce'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.order_number} by {self.user.display_name}"
    
    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)
    
    def generate_order_number(self):
        return f"DC{timezone.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    def get_absolute_url(self):
        return reverse('ecommerce:order_detail', kwargs={'order_number': self.order_number})

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Store product details at time of purchase
    product_name = models.CharField(max_length=200)
    product_sku = models.CharField(max_length=100, blank=True)
    
    class Meta:
        app_label = 'ecommerce'
    
    def __str__(self):
        return f"{self.quantity} x {self.product_name}"

class Wishlist(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    products = models.ManyToManyField(Product, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'ecommerce'
    
    def __str__(self):
        return f"Wishlist for {self.user.display_name}"

class Review(models.Model):
    RATING_CHOICES = [(i, i) for i in range(1, 6)]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        app_label = 'ecommerce'
        unique_together = ['product', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.rating}-star review for {self.product.name} by {self.user.display_name}"

class Coupon(models.Model):
    DISCOUNT_TYPES = [
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ]
    
    code = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=200)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_TYPES)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    maximum_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    member_exclusive = models.BooleanField(default=False)
    
    class Meta:
        app_label = 'ecommerce'
    
    def __str__(self):
        return self.code
    
    @property
    def is_valid(self):
        now = timezone.now()
        return (self.is_active and 
                self.valid_from <= now <= self.valid_to and
                (self.maximum_uses is None or self.used_count < self.maximum_uses))

class LoyaltyProgram(models.Model):
    user = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    points = models.PositiveIntegerField(default=0)
    tier = models.CharField(max_length=20, default='Bronze')
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        app_label = 'ecommerce'
    
    def __str__(self):
        return f"{self.user.display_name} - {self.tier} ({self.points} points)"
