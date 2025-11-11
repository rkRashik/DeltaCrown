"""
Prize Transaction Admin Interface

Module 5.2: Prize Payouts & Reconciliation

Implements:
- PHASE_5_IMPLEMENTATION_PLAN.md#module-52-prize-payouts--reconciliation (admin interface)
- 01_ARCHITECTURE_DECISIONS.md#adr-001-service-layer-pattern (view-only admin)

This admin interface provides read-only access to prize transaction records.
Prize transactions are created programmatically by PayoutService; admins can
view the audit trail but cannot manually create/edit/delete transactions through
the admin interface.

Security:
    View-only. Mutations must go through PayoutService to ensure proper
    idempotency, reconciliation, and audit trail generation.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import PrizeTransaction


@admin.register(PrizeTransaction)
class PrizeTransactionAdmin(admin.ModelAdmin):
    """
    View-only admin interface for prize transaction audit trail.
    
    Prize transactions are created programmatically via PayoutService.
    This interface provides visibility for organizers and admins to:
    - Monitor payout status
    - Track prize distribution
    - Reconcile discrepancies
    - Audit payout history
    """
    
    # List Display
    list_display = [
        'id',
        'tournament_link',
        'participant_link',
        'placement',
        'amount_display',
        'status_badge',
        'coin_transaction_link',
        'created_at',
        'processed_by',
    ]
    
    # Filters
    list_filter = [
        'status',
        'placement',
        'created_at',
    ]
    
    # Search
    search_fields = [
        'tournament__title',
        'tournament__slug',
        'participant__user__username',
        'participant__team_name',
        'notes',
    ]
    
    # Read-only fields (all fields)
    readonly_fields = [
        'id',
        'tournament',
        'participant',
        'placement',
        'amount',
        'coin_transaction_id',
        'status',
        'notes',
        'created_at',
        'updated_at',
        'processed_by',
    ]
    
    # Fieldsets
    fieldsets = (
        ('Transaction Details', {
            'fields': (
                'id',
                'tournament',
                'participant',
                'placement',
                'amount',
                'status',
            )
        }),
        ('Economy Integration', {
            'fields': (
                'coin_transaction_id',
            ),
            'description': 'Reference to DeltaCrownTransaction in apps.economy (IntegerField, not FK)'
        }),
        ('Metadata', {
            'fields': (
                'processed_by',
                'notes',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )
    
    # Ordering
    ordering = ['-created_at', '-id']
    
    # Pagination
    list_per_page = 50
    
    # Permissions: View-only (no add/change/delete)
    def has_add_permission(self, request):
        """Disable add - transactions created by PayoutService only."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable edit - transactions are immutable audit records."""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Disable delete - transactions are immutable audit records."""
        return False
    
    # Custom Display Methods
    
    def tournament_link(self, obj):
        """Link to tournament admin page."""
        if obj.tournament:
            url = f'/admin/tournaments/tournament/{obj.tournament.id}/change/'
            return format_html('<a href="{}">{}</a>', url, obj.tournament.title)
        return '-'
    tournament_link.short_description = 'Tournament'
    
    def participant_link(self, obj):
        """Link to registration admin page."""
        if obj.participant:
            url = f'/admin/tournaments/registration/{obj.participant.id}/change/'
            display = obj.participant.team_name or obj.participant.user.username
            return format_html('<a href="{}">{}</a>', url, display)
        return '-'
    participant_link.short_description = 'Participant'
    
    def amount_display(self, obj):
        """Format amount as Delta Coins."""
        return f'Ð{obj.amount}'
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            'pending': '#FFA500',    # Orange
            'completed': '#28A745',  # Green
            'failed': '#DC3545',     # Red
            'refunded': '#6C757D',   # Gray
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'status'
    
    def coin_transaction_link(self, obj):
        """
        Display coin transaction ID with link to economy admin.
        
        Note: Uses IntegerField reference (not FK), so link is constructed manually.
        """
        if obj.coin_transaction_id:
            # Link to economy.DeltaCrownTransaction admin page
            url = f'/admin/economy/deltacrowntransaction/{obj.coin_transaction_id}/change/'
            return format_html('<a href="{}" target="_blank">Tx #{}</a>', url, obj.coin_transaction_id)
        return '-'
    coin_transaction_link.short_description = 'Coin Transaction'
    coin_transaction_link.admin_order_field = 'coin_transaction_id'
