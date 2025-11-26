# apps/economy/admin.py
from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.db.models import Sum
from django.http import HttpRequest
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import CoinPolicy, DeltaCrownTransaction, DeltaCrownWallet, WithdrawalRequest


@admin.register(DeltaCrownWallet)
class DeltaCrownWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "profile_display", "cached_balance", "updated_at")
    search_fields = ("profile__user__username", "profile__user__email")
    readonly_fields = ("created_at", "updated_at", "cached_balance")
    autocomplete_fields = ("profile",)
    actions = ["recalculate_balances"]

    def profile_display(self, obj):
        u = getattr(obj.profile, "user", None)
        return f"{getattr(obj.profile, 'id', None)} — {getattr(u, 'username', '') or getattr(u, 'email', '')}"

    profile_display.short_description = "Profile"

    @admin.action(description="Recalculate selected wallet balances")
    def recalculate_balances(self, request: HttpRequest, queryset):
        count = 0
        for w in queryset:
            w.recalc_and_save()
            count += 1
        self.message_user(request, f"Recalculated {count} wallet(s).", level=messages.SUCCESS)


class AdjustForm(forms.Form):
    amount = forms.IntegerField(help_text="Positive to credit, negative to debit")
    note = forms.CharField(required=False, max_length=255)


@admin.register(DeltaCrownTransaction)
class DeltaCrownTransactionAdmin(admin.ModelAdmin):
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

# class CoinPolicyInline(admin.StackedInline):
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
class WithdrawalRequestAdmin(admin.ModelAdmin):
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
class CoinPolicyAdmin(admin.ModelAdmin):
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
