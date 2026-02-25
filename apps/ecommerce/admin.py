from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from apps.common.admin_mixins import SafeUploadMixin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Category, Brand, Product, ProductImage, ProductVariant,
    Cart, CartItem, Order, OrderItem, Wishlist, Review,
    Coupon, LoyaltyProgram
)

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'category_type', 'is_active', 'sort_order']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['sort_order', 'name']

@admin.register(Brand)
class BrandAdmin(ModelAdmin):
    list_display = ['name', 'is_featured', 'is_active']
    list_filter = ['is_featured', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}

class ProductImageInline(TabularInline):
    model = ProductImage
    extra = 1
    fields = ['image', 'alt_text', 'is_featured', 'sort_order']

class ProductVariantInline(TabularInline):
    model = ProductVariant
    extra = 1
    fields = ['name', 'value', 'price_adjustment', 'stock', 'sku', 'is_active']

@admin.register(Product)
class ProductAdmin(SafeUploadMixin, ModelAdmin):
    list_display = [
        'name', 'category', 'brand', 'price', 'stock', 'is_featured', 
        'is_active', 'product_type', 'rarity'
    ]
    list_filter = [
        'category', 'brand', 'product_type', 'rarity', 'is_featured', 
        'is_active', 'is_digital', 'is_member_exclusive'
    ]
    search_fields = ['name', 'description', 'short_description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, ProductVariantInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'short_description', 'category', 'brand')
        }),
        ('Pricing', {
            'fields': ('price', 'original_price', 'discount_percentage')
        }),
        ('Product Details', {
            'fields': ('product_type', 'rarity', 'featured_image', 'hover_image')
        }),
        ('Inventory', {
            'fields': ('stock', 'track_stock', 'allow_backorder')
        }),
        ('Features', {
            'fields': (
                'is_featured', 'is_digital', 'is_member_exclusive', 
                'is_limited_edition', 'limited_quantity'
            )
        }),
        ('Gaming', {
            'fields': ('compatible_games', 'esports_team')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'brand')

class OrderItemInline(TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'unit_price', 'total_price']

@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = [
        'order_number', 'user', 'status', 'payment_method', 
        'total_price', 'created_at'
    ]
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['order_number', 'user__display_name', 'billing_email']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'user', 'status', 'payment_method')
        }),
        ('Pricing', {
            'fields': ('subtotal', 'tax_amount', 'shipping_cost', 'discount_amount', 'total_price')
        }),
        ('Billing Address', {
            'fields': (
                'billing_name', 'billing_email', 'billing_phone',
                'billing_address', 'billing_city', 'billing_state',
                'billing_zip', 'billing_country'
            )
        }),
        ('Shipping Address', {
            'fields': (
                'shipping_name', 'shipping_address', 'shipping_city',
                'shipping_state', 'shipping_zip', 'shipping_country'
            ),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('notes', 'tracking_number'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'shipped_at', 'delivered_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

class CartItemInline(TabularInline):
    model = CartItem
    extra = 0

@admin.register(Cart)
class CartAdmin(ModelAdmin):
    list_display = ['user', 'total_items', 'total_price', 'created_at']
    search_fields = ['user__display_name']
    inlines = [CartItemInline]
    
    def total_items(self, obj):
        return obj.total_items
    total_items.short_description = 'Total Items'
    
    def total_price(self, obj):
        return f"${obj.total_price}"
    total_price.short_description = 'Total Price'

@admin.register(Review)
class ReviewAdmin(ModelAdmin):
    list_display = ['product', 'user', 'rating', 'is_verified_purchase', 'is_approved', 'created_at']
    list_filter = ['rating', 'is_verified_purchase', 'is_approved', 'created_at']
    search_fields = ['product__name', 'user__display_name', 'title', 'comment']
    actions = ['approve_reviews', 'disapprove_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "Approve selected reviews"
    
    def disapprove_reviews(self, request, queryset):
        queryset.update(is_approved=False)
    disapprove_reviews.short_description = "Disapprove selected reviews"

@admin.register(Coupon)
class CouponAdmin(ModelAdmin):
    list_display = [
        'code', 'discount_type', 'discount_value', 'used_count', 
        'maximum_uses', 'valid_from', 'valid_to', 'is_active'
    ]
    list_filter = ['discount_type', 'is_active', 'member_exclusive']
    search_fields = ['code', 'description']
    readonly_fields = ['used_count']

@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(ModelAdmin):
    list_display = ['user', 'tier', 'points', 'total_spent']
    list_filter = ['tier']
    search_fields = ['user__display_name']
    readonly_fields = ['total_spent']

@admin.register(Wishlist)
class WishlistAdmin(ModelAdmin):
    list_display = ['user', 'product_count', 'created_at']
    search_fields = ['user__display_name']
    filter_horizontal = ['products']
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Products'

# Unregister if already registered (to avoid conflicts)
try:
    admin.site.unregister(Product)
except admin.sites.NotRegistered:
    pass