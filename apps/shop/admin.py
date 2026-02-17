"""
DeltaCoin Shop Admin - Module 7.2

Lightweight admin for ShopItem catalog management.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ShopItem, ReservationHold


@admin.register(ShopItem)
class ShopItemAdmin(ModelAdmin):
    """Admin interface for ShopItem catalog."""
    
    list_display = ['sku', 'name', 'price', 'active', 'created_at']
    list_filter = ['active', 'created_at']
    search_fields = ['sku', 'name']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(ReservationHold)
class ReservationHoldAdmin(ModelAdmin):
    """Admin interface for ReservationHold (read-only monitoring)."""
    
    list_display = ['id', 'wallet', 'sku', 'amount', 'status', 'expires_at', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sku', 'idempotency_key']
    readonly_fields = ['wallet', 'sku', 'amount', 'status', 'expires_at', 'idempotency_key', 'captured_txn_id', 'meta', 'created_at']
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Holds can only be created via service layer."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Holds are immutable after creation."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Holds cannot be deleted (audit trail)."""
        return False
