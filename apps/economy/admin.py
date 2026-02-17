# apps/economy/admin.py
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from django import forms
from django.contrib import admin, messages
from unfold.admin import ModelAdmin, StackedInline
from django.db.models import Sum
from django.http import HttpRequest
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import CoinPolicy, DeltaCrownTransaction, DeltaCrownWallet, TopUpRequest, WalletPINOTP, WithdrawalRequest


@admin.register(DeltaCrownWallet)
class DeltaCrownWalletAdmin(ModelAdmin):
    list_display = ("id", "profile_display", "cached_balance", "updated_at")
    search_fields = ("profile__user__username", "profile__user__email", "profile__public_id")
    readonly_fields = ("created_at", "updated_at", "cached_balance")
    autocomplete_fields = ("profile",)
    actions = ["recalculate_balances", "reconcile_to_profile"]

    def profile_display(self, obj):
        u = getattr(obj.profile, "user", None)
        public_id = getattr(obj.profile, 'public_id', None)
        username = getattr(u, 'username', '') or getattr(u, 'email', '')
        if public_id:
            return f"{public_id} — {username}"
        return f"{getattr(obj.profile, 'id', None)} — {username}"

    profile_display.short_description = "Profile"


@admin.register(WalletPINOTP)
class WalletPINOTPAdmin(ModelAdmin):
    """UP-PHASE7.7: Read-only admin for OTP audit trail"""
    list_display = ("id", "wallet_user", "purpose", "is_used", "attempt_count", "created_at", "expires_at", "validity_status")
    list_filter = ("purpose", "is_used", "created_at")
    search_fields = ("wallet__profile__user__username", "wallet__profile__user__email")
    readonly_fields = ("wallet", "code_hash", "purpose", "attempt_count", "max_attempts", "is_used", "used_at", "created_at", "expires_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def has_add_permission(self, request):
        """Prevent manual OTP creation - must go through API"""
        return False

    def has_change_permission(self, request, obj=None):
        """Read-only view for security audit"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion for audit trail"""
        return False

    def wallet_user(self, obj):
        """Display wallet owner username"""
        if obj.wallet and obj.wallet.profile and obj.wallet.profile.user:
            return obj.wallet.profile.user.username
        return "—"
    wallet_user.short_description = "User"

    def validity_status(self, obj):
        """Show if OTP is currently valid"""
        if obj.is_used:
            return format_html('<span style="color: gray;">✓ Used</span>')
        if not obj.is_valid():
            return format_html('<span style="color: red;">✗ Expired/Invalid</span>')
        if obj.attempt_count >= obj.max_attempts:
            return format_html('<span style="color: orange;">⚠ Max Attempts</span>')
        return format_html('<span style="color: green;">✓ Valid</span>')
    validity_status.short_description = "Status"


@admin.register(TopUpRequest)
class TopUpRequestAdmin(ModelAdmin):
    list_display = ['id', 'wallet_link', 'amount', 'bdt_display', 'payment_method', 'status_badge', 'requested_at', 'reviewed_by_display']
    list_filter = ['status', 'payment_method', 'requested_at', 'reviewed_at']
    search_fields = ['wallet__profile__user__username', 'wallet__profile__user__email', 'wallet__profile__real_full_name', 'payment_number', 'admin_note']
    readonly_fields = ['wallet', 'requested_at', 'reviewed_at', 'reviewed_by', 'completed_at', 'transaction', 'payment_details_display', 'bdt_amount']
    
    fieldsets = [
        ('Top-Up Info', {
            'fields': ['wallet', 'amount', 'status']
        }),
        ('Payment Details', {
            'fields': ['payment_method', 'payment_number', 'payment_details_display']
        }),
        ('Exchange Rate', {
            'fields': ['dc_to_bdt_rate', 'bdt_amount'],
            'classes': ['collapse']
        }),
        ('Notes', {
            'fields': ['user_note', 'admin_note', 'rejection_reason']
        }),
        ('Review Metadata', {
            'fields': ['requested_at', 'reviewed_at', 'reviewed_by', 'completed_at'],
            'classes': ['collapse']
        }),
        ('Transaction', {
            'fields': ['transaction'],
            'classes': ['collapse']
        }),
    ]
    
    actions = ['approve_topups', 'reject_topups']
    
    def wallet_link(self, obj):
        url = reverse('admin:economy_deltacrownwallet_change', args=[obj.wallet.id])
        return format_html('<a href="{}">{}</a>', url, obj.wallet.profile.user.username)
    wallet_link.short_description = 'Wallet'
    
    def bdt_display(self, obj):
        return f"৳{obj.bdt_amount}"
    bdt_display.short_description = 'BDT Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'approved': '#3b82f6',
            'completed': '#10b981',
            'rejected': '#ef4444',
            'cancelled': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def reviewed_by_display(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.username
        return '-'
    reviewed_by_display.short_description = 'Reviewed By'
    
    def payment_details_display(self, obj):
        html = f'<strong>Method:</strong> {obj.get_payment_method_display()}<br>'
        html += f'<strong>Number:</strong> {obj.payment_number}<br>'
        
        if obj.payment_details:
            for key, value in obj.payment_details.items():
                html += f'<strong>{key.replace("_", " ").title()}:</strong> {value}<br>'
        
        return mark_safe(html)
    payment_details_display.short_description = 'Payment Details'
    
    def approve_topups(self, request, queryset):
        """Bulk approve top-up requests"""
        from django.db import transaction as db_transaction
        from django.utils import timezone
        
        approved_count = 0
        for topup in queryset.filter(status='pending'):
            try:
                with db_transaction.atomic():
                    # Create transaction record
                    txn = DeltaCrownTransaction.objects.create(
                        wallet=topup.wallet,
                        amount=topup.amount,
                        reason='top_up',
                        note=f'Top-up request #{topup.id} approved by {request.user.username}'
                    )
                    
                    # Update top-up request
                    topup.status = 'completed'
                    topup.reviewed_at = timezone.now()
                    topup.reviewed_by = request.user
                    topup.completed_at = timezone.now()
                    topup.transaction = txn
                    topup.admin_note = f'Bulk approved by {request.user.username}'
                    topup.save()
                    
                    # Recalculate wallet balance
                    topup.wallet.recalc_and_save()
                    
                    approved_count += 1
                    
            except Exception as e:
                self.message_user(request, f'Error approving #{topup.id}: {str(e)}', level=messages.ERROR)
        
        if approved_count > 0:
            self.message_user(request, f'Successfully approved {approved_count} top-up(s)', level=messages.SUCCESS)
    approve_topups.short_description = 'Approve selected top-ups'
    
    def reject_topups(self, request, queryset):
        """Bulk reject top-up requests"""
        from django.utils import timezone
        
        rejected_count = 0
        for topup in queryset.filter(status='pending'):
            try:
                topup.status = 'rejected'
                topup.reviewed_at = timezone.now()
                topup.reviewed_by = request.user
                topup.rejection_reason = 'Bulk rejection by admin'
                topup.save()
                rejected_count += 1
            except Exception as e:
                self.message_user(request, f'Error rejecting #{topup.id}: {str(e)}', level=messages.ERROR)
        
        if rejected_count > 0:
            self.message_user(request, f'Successfully rejected {rejected_count} top-up(s)', level=messages.SUCCESS)
    reject_topups.short_description = 'Reject selected top-ups'


class AdjustForm(forms.Form):
    amount = forms.IntegerField(help_text="Positive to credit, negative to debit")
    note = forms.CharField(required=False, max_length=255)


@admin.register(DeltaCrownTransaction)
class DeltaCrownTransactionAdmin(ModelAdmin):
    list_display = (
        "id",
        "wallet",
        "amount",
        "reason",
        "tournament_id",
        "registration_id",
        "match_id",
        "created_by",
        "created_at",
    )
    list_filter = ("reason",)  # Removed "tournament" filter (legacy app removed)
    search_fields = (
        "wallet__profile__user__username",
        "wallet__profile__user__email",
        "idempotency_key",
        "note",
    )
    readonly_fields = ("created_at", "tournament_id", "registration_id", "match_id")  # Legacy fields readonly
    autocomplete_fields = ("wallet", "created_by")  # Removed tournament/registration/match (legacy)
    actions = ["export_csv", "adjust_balance"]

    @admin.action(description="Export selected rows to CSV")
    def export_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="coin_transactions.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "wallet_id",
                "profile_id",
                "amount",
                "reason",
                "tournament_id",
                "registration_id",
                "match_id",
                "note",
                "created_by_id",
                "idempotency_key",
                "created_at",
            ]
        )
        for tx in queryset.select_related("wallet__profile"):
            writer.writerow(
                [
                    tx.id,
                    tx.wallet_id,
                    getattr(tx.wallet.profile, "id", None),
                    tx.amount,
                    tx.reason,
                    tx.tournament_id,
                    tx.registration_id,
                    tx.match_id,
                    tx.note,
                    tx.created_by_id,
                    tx.idempotency_key,
                    tx.created_at.isoformat(),
                ]
            )
        return response

    @admin.action(description="Adjust balance (opens a small form)")
    def adjust_balance(self, request: HttpRequest, queryset):
        """
        Bulk adjustment action with a small ActionForm.
        """
        if "apply" in request.POST:
            form = AdjustForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data["amount"]
                note = form.cleaned_data.get("note") or ""
                n = 0
                for wallet in queryset:
                    DeltaCrownTransaction.objects.create(
                        wallet=wallet,
                        amount=int(amount),
                        reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                        note=note or "Manual adjustment",
                        created_by=getattr(request, "user", None),
                    )
                    wallet.recalc_and_save()
                    n += 1
                self.message_user(request, f"Adjusted {n} wallet(s) by {amount} coins.", level=messages.SUCCESS)
                return None
            else:
                self.message_user(request, "Invalid input.", level=messages.ERROR)
        else:
            form = AdjustForm()

        from django.template.response import TemplateResponse

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Adjust selected wallet balances",
            "queryset": queryset,
            "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
            "form": form,
        }
        return TemplateResponse(request, "admin/economy/adjust_balance.html", context)


# Legacy Tournament Integration - Disabled (November 2, 2025)
# This inline was used to attach CoinPolicy to Tournament admin
# Will be reimplemented when new Tournament Engine is built

# class CoinPolicyInline(StackedInline):
#     model = CoinPolicy
#     can_delete = False
#     extra = 0
#     fk_name = "tournament"
#     fields = ("enabled", "participation", "top4", "runner_up", "winner")

# NOTE: When new Tournament Engine is built, re-enable this pattern:
# 1. Create CoinPolicyInline (similar to above)
# 2. Hook into new Tournament admin via try/except
# 3. Use apps.get_model() to avoid direct imports


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(ModelAdmin):
    list_display = ['id', 'wallet_link', 'amount', 'bdt_display', 'payment_method', 'status_badge', 'requested_at', 'reviewed_by_display']
    list_filter = ['status', 'payment_method', 'requested_at', 'reviewed_at']
    search_fields = ['wallet__profile__user__username', 'wallet__profile__user__email', 'wallet__profile__real_full_name', 'payment_number', 'admin_note']
    readonly_fields = ['wallet', 'requested_at', 'reviewed_at', 'reviewed_by', 'completed_at', 'transaction', 'payment_details_display', 'bdt_amount']
    
    fieldsets = [
        ('Withdrawal Info', {
            'fields': ['wallet', 'amount', 'status']
        }),
        ('Payment Details', {
            'fields': ['payment_method', 'payment_number', 'payment_details_display']
        }),
        ('Exchange & Fees', {
            'fields': ['dc_to_bdt_rate', 'processing_fee', 'bdt_amount'],
            'classes': ['collapse']
        }),
        ('Notes', {
            'fields': ['user_note', 'admin_note', 'rejection_reason']
        }),
        ('Review Metadata', {
            'fields': ['requested_at', 'reviewed_at', 'reviewed_by', 'completed_at'],
            'classes': ['collapse']
        }),
        ('Transaction', {
            'fields': ['transaction'],
            'classes': ['collapse']
        }),
    ]
    
    actions = ['approve_withdrawals', 'reject_withdrawals']
    
    def wallet_link(self, obj):
        url = reverse('admin:economy_deltacrownwallet_change', args=[obj.wallet.id])
        return format_html('<a href="{}">{}</a>', url, obj.wallet.profile.user.username)
    wallet_link.short_description = 'Wallet'
    
    def bdt_display(self, obj):
        return f"৳{obj.bdt_amount}"
    bdt_display.short_description = 'BDT Amount'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b',
            'approved': '#3b82f6',
            'completed': '#10b981',
            'rejected': '#ef4444',
            'cancelled': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 11px; font-weight: 600;">{}</span>',
            color,
            obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'
    
    def reviewed_by_display(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.username
        return '-'
    reviewed_by_display.short_description = 'Reviewed By'
    
    def payment_details_display(self, obj):
        html = f'<strong>Method:</strong> {obj.get_payment_method_display()}<br>'
        html += f'<strong>Number:</strong> {obj.payment_number}<br>'
        
        if obj.payment_details:
            for key, value in obj.payment_details.items():
                html += f'<strong>{key.replace("_", " ").title()}:</strong> {value}<br>'
        
        return mark_safe(html)
    payment_details_display.short_description = 'Payment Details'
    
    def approve_withdrawals(self, request, queryset):
        """Bulk approve withdrawal requests"""
        approved_count = 0
        for withdrawal in queryset.filter(status='pending'):
            try:
                withdrawal.approve(
                    reviewed_by=request.user,
                    admin_note=f'Bulk approved by {request.user.username}',
                    completed_immediately=True
                )
                approved_count += 1
                
                # Award first withdrawal badge
                try:
                    from apps.user_profile.signals import award_first_withdrawal_badge
                    user = withdrawal.wallet.user_profile.user
                    award_first_withdrawal_badge(user)
                except Exception as e:
                    # Don't fail withdrawal approval if badge award fails
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to award withdrawal badge to {user.username}: {e}")
                
            except Exception as e:
                self.message_user(request, f'Error approving #{withdrawal.id}: {str(e)}', level=messages.ERROR)
        
        if approved_count > 0:
            self.message_user(request, f'Successfully approved {approved_count} withdrawal(s)', level=messages.SUCCESS)
    approve_withdrawals.short_description = 'Approve selected withdrawals'
    
    def reject_withdrawals(self, request, queryset):
        """Bulk reject withdrawal requests"""
        rejected_count = 0
        for withdrawal in queryset.filter(status='pending'):
            try:
                withdrawal.reject(
                    reviewed_by=request.user,
                    rejection_reason='Bulk rejection by admin'
                )
                rejected_count += 1
            except Exception as e:
                self.message_user(request, f'Error rejecting #{withdrawal.id}: {str(e)}', level=messages.ERROR)
        
        if rejected_count > 0:
            self.message_user(request, f'Successfully rejected {rejected_count} withdrawal(s)', level=messages.SUCCESS)
    reject_withdrawals.short_description = 'Reject selected withdrawals'


@admin.register(CoinPolicy)
class CoinPolicyAdmin(ModelAdmin):
    list_display = ['tournament_id', 'enabled', 'participation', 'top4', 'runner_up', 'winner', 'created_at']
    list_filter = ['enabled', 'created_at']
    search_fields = ['tournament_id']
    
    fieldsets = [
        ('Tournament', {
            'fields': ['tournament_id', 'enabled']
        }),
        ('Rewards', {
            'fields': ['participation', 'top4', 'runner_up', 'winner']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    readonly_fields = ['created_at', 'updated_at']


# =====================================================================
# PHASE 3A: INVENTORY SYSTEM ADMIN
# =====================================================================

from .models import InventoryItem, UserInventoryItem, GiftRequest, TradeRequest


@admin.register(InventoryItem)
class InventoryItemAdmin(ModelAdmin):
    list_display = ('slug', 'name', 'item_type', 'rarity', 'tradable', 'giftable', 'created_at')
    list_filter = ('item_type', 'rarity', 'tradable', 'giftable')
    search_fields = ('slug', 'name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Basic Info', {
            'fields': ['slug', 'name', 'description']
        }),
        ('Classification', {
            'fields': ['item_type', 'rarity']
        }),
        ('Trade & Gift', {
            'fields': ['tradable', 'giftable']
        }),
        ('Visuals', {
            'fields': ['icon', 'icon_url']
        }),
        ('Metadata', {
            'fields': ['metadata'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    )


@admin.register(UserInventoryItem)
class UserInventoryItemAdmin(ModelAdmin):
    list_display = ('id', 'profile_display', 'item', 'quantity', 'locked', 'acquired_from', 'acquired_at')
    list_filter = ('locked', 'acquired_from', 'item__item_type', 'item__rarity')
    search_fields = ('profile__user__username', 'item__name', 'item__slug')
    readonly_fields = ('acquired_at', 'updated_at')
    autocomplete_fields = ('profile', 'item')
    
    def profile_display(self, obj):
        username = getattr(obj.profile.user, 'username', 'Unknown')
        return f"{username}"
    profile_display.short_description = 'User'
    
    fieldsets = (
        ('Ownership', {
            'fields': ['profile', 'item']
        }),
        ('Quantity & Status', {
            'fields': ['quantity', 'locked']
        }),
        ('Acquisition', {
            'fields': ['acquired_from', 'acquired_at', 'updated_at'],
        }),
    )


@admin.register(GiftRequest)
class GiftRequestAdmin(ModelAdmin):
    list_display = ('id', 'sender_display', 'receiver_display', 'item', 'quantity', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('sender_profile__user__username', 'receiver_profile__user__username', 'item__name')
    readonly_fields = ('created_at', 'resolved_at')
    autocomplete_fields = ('sender_profile', 'receiver_profile', 'item')
    
    def sender_display(self, obj):
        return getattr(obj.sender_profile.user, 'username', 'Unknown')
    sender_display.short_description = 'Sender'
    
    def receiver_display(self, obj):
        return getattr(obj.receiver_profile.user, 'username', 'Unknown')
    receiver_display.short_description = 'Receiver'
    
    fieldsets = (
        ('Parties', {
            'fields': ['sender_profile', 'receiver_profile']
        }),
        ('Item Details', {
            'fields': ['item', 'quantity', 'message']
        }),
        ('Status', {
            'fields': ['status', 'created_at', 'resolved_at']
        }),
    )


@admin.register(TradeRequest)
class TradeRequestAdmin(ModelAdmin):
    list_display = ('id', 'initiator_display', 'target_display', 'offered_item', 'requested_item', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('initiator_profile__user__username', 'target_profile__user__username', 'offered_item__name', 'requested_item__name')
    readonly_fields = ('created_at', 'resolved_at')
    autocomplete_fields = ('initiator_profile', 'target_profile', 'offered_item', 'requested_item')
    
    def initiator_display(self, obj):
        return getattr(obj.initiator_profile.user, 'username', 'Unknown')
    initiator_display.short_description = 'Initiator'
    
    def target_display(self, obj):
        return getattr(obj.target_profile.user, 'username', 'Unknown')
    target_display.short_description = 'Target'
    
    fieldsets = (
        ('Parties', {
            'fields': ['initiator_profile', 'target_profile']
        }),
        ('Offered Item', {
            'fields': ['offered_item', 'offered_quantity']
        }),
        ('Requested Item (Optional)', {
            'fields': ['requested_item', 'requested_quantity']
        }),
        ('Message & Status', {
            'fields': ['message', 'status', 'created_at', 'resolved_at']
        }),
    )
