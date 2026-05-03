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

from .models import (
    CoinPolicy, DeltaCrownTransaction, DeltaCrownWallet,
    EconomyConfig, EconomyDashboard, TopUpRequest, WalletPINOTP,
    WithdrawalRequest,   # DEPRECATED — kept for admin visibility of legacy rows
    PrizeClaim,
    FinancialFortress,
)


# [FORTRESS] DeltaCrownWallet — unregistered; managed exclusively via Financial Fortress
# @admin.register(DeltaCrownWallet)
class DeltaCrownWalletAdmin(ModelAdmin):
    list_display = ("id", "treasury_badge", "profile_display", "cached_balance", "updated_at")
    search_fields = ("profile__user__username", "profile__user__email", "profile__public_id")
    readonly_fields = ("created_at", "updated_at", "cached_balance", "is_treasury")
    autocomplete_fields = ("profile",)
    actions = ["recalculate_balances", "reconcile_to_profile", "adjust_balance"]

    # ── Fortress lock: only superusers may create or delete wallet rows ───────
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Staff may view but not edit wallet rows directly; use Fortress for mutations."""
        return request.user.is_superuser

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def treasury_badge(self, obj):
        if obj.is_treasury:
            return format_html('<span style="background:#f59e0b;color:#fff;padding:2px 8px;'
                               'border-radius:8px;font-size:11px;font-weight:700;">🏦 TREASURY</span>')
        return ""
    treasury_badge.short_description = "Type"

    def profile_display(self, obj):
        if obj.is_treasury:
            return format_html('<em style="color:#6b7280;">Master Treasury (system)</em>')
        u = getattr(obj.profile, "user", None)
        public_id = getattr(obj.profile, 'public_id', None)
        username = getattr(u, 'username', '') or getattr(u, 'email', '')
        if public_id:
            return f"{public_id} — {username}"
        return f"{getattr(obj.profile, 'id', None)} — {username}"
    profile_display.short_description = "Profile"

    # ------------------------------------------------------------------
    # Action: recalculate_balances  (was listed but never implemented — Bug #4)
    # ------------------------------------------------------------------

    @admin.action(description="Recalculate balance from ledger SUM (safe, atomic)")
    def recalculate_balances(self, request, queryset):
        """
        Re-derive cached_balance from SUM(transaction.amount) for each selected wallet.
        Uses select_for_update so concurrent writes cannot race.
        """
        fixed = skipped = 0
        for wallet in queryset:
            try:
                old = wallet.cached_balance
                new = wallet.recalc_and_save()
                if old != new:
                    fixed += 1
            except Exception as exc:
                self.message_user(
                    request,
                    f"Wallet #{wallet.id}: {exc}",
                    level=messages.ERROR,
                )
                skipped += 1
        self.message_user(
            request,
            f"Done — {fixed} wallet(s) corrected, {skipped} error(s).",
            level=messages.SUCCESS if not skipped else messages.WARNING,
        )

    # ------------------------------------------------------------------
    # Action: reconcile_to_profile  (was listed but never implemented — Bug #4)
    # ------------------------------------------------------------------

    @admin.action(description="Sync wallet balance → user profile fields")
    def reconcile_to_profile(self, request, queryset):
        """Push cached_balance to profile.deltacoin_balance for selected user wallets."""
        from apps.user_profile.services.economy_sync import sync_wallet_to_profile
        synced = skipped = 0
        for wallet in queryset.filter(is_treasury=False):
            try:
                sync_wallet_to_profile(wallet.id)
                synced += 1
            except Exception as exc:
                self.message_user(request, f"Wallet #{wallet.id}: {exc}", level=messages.ERROR)
                skipped += 1
        self.message_user(
            request,
            f"Synced {synced} wallet(s) to profile. {skipped} error(s).",
            level=messages.SUCCESS if not skipped else messages.WARNING,
        )

    # ------------------------------------------------------------------
    # Action: adjust_balance  (moved from TransactionAdmin — Bug #6)
    # ------------------------------------------------------------------

    @admin.action(description="Manually adjust balance (credit or debit)")
    def adjust_balance(self, request: HttpRequest, queryset):
        """
        Apply a manual MANUAL_ADJUST transaction to selected wallets.
        queryset here contains DeltaCrownWallet objects (correct, unlike the old location).
        """
        if "apply" in request.POST:
            form = AdjustForm(request.POST)
            if form.is_valid():
                amount = form.cleaned_data["amount"]
                note = form.cleaned_data.get("note") or "Manual adjustment"
                n = 0
                for wallet in queryset:
                    DeltaCrownTransaction.objects.create(
                        wallet=wallet,
                        amount=int(amount),
                        reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                        note=note,
                        created_by=request.user,
                    )
                    # recalc_and_save() is also triggered by DeltaCrownTransaction.save(),
                    # but calling it explicitly here ensures the admin reflects the update
                    # immediately without relying on the model-layer side effect.
                    wallet.recalc_and_save()
                    n += 1
                self.message_user(
                    request,
                    f"Adjusted {n} wallet(s) by {amount:+d} DC.",
                    level=messages.SUCCESS,
                )
                return None
            self.message_user(request, "Invalid input.", level=messages.ERROR)
        else:
            form = AdjustForm()

        from django.template.response import TemplateResponse
        return TemplateResponse(
            request,
            "admin/economy/adjust_balance.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Adjust selected wallet balances",
                "queryset": queryset,
                "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
                "form": form,
            },
        )


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


# [FORTRESS] TopUpRequest — unregistered; managed exclusively via Financial Fortress
# @admin.register(TopUpRequest)
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
        """Bulk approve top-up requests — debits Master Treasury then credits user."""
        from django.db import transaction as db_transaction
        from django.utils import timezone
        from .services import get_master_treasury

        approved_count = 0
        for topup in queryset.filter(status='pending'):
            try:
                with db_transaction.atomic():
                    treasury = get_master_treasury()

                    # 1. Debit the Master Treasury (establishes where the coins come from).
                    #    idempotency_key prevents duplicate debits on retry.
                    DeltaCrownTransaction.objects.create(
                        wallet=treasury,
                        amount=-topup.amount,
                        reason=DeltaCrownTransaction.Reason.TOP_UP,
                        note=f'Treasury debit for top-up #{topup.id}',
                        created_by=request.user,
                        idempotency_key=f'topup_{topup.id}_treasury',
                    )

                    # 2. Credit the user wallet.
                    #    Same idempotency family; unique constraint prevents double-credit.
                    txn = DeltaCrownTransaction.objects.create(
                        wallet=topup.wallet,
                        amount=topup.amount,
                        reason=DeltaCrownTransaction.Reason.TOP_UP,
                        note=f'Top-up #{topup.id} approved by {request.user.username}',
                        created_by=request.user,
                        idempotency_key=f'topup_{topup.id}',
                    )

                    # 3. Persist top-up request state.
                    topup.status = 'completed'
                    topup.reviewed_at = timezone.now()
                    topup.reviewed_by = request.user
                    topup.completed_at = timezone.now()
                    topup.transaction = txn
                    topup.admin_note = f'Approved by {request.user.username}'
                    topup.save()

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


# [FORTRESS] DeltaCrownTransaction — immutable ledger; no admin access
# @admin.register(DeltaCrownTransaction)
class DeltaCrownTransactionAdmin(ModelAdmin):
    """
    Immutable ledger admin — ALL mutations are blocked.
    Transactions are only ever created programmatically through services.py
    or the Financial Fortress. Direct admin editing is forbidden.
    """
    list_display = (
        "id",
        "wallet",
        "amount",
        "cached_balance_after",
        "reason",
        "tournament_id",
        "registration_id",
        "match_id",
        "created_by",
        "created_at",
    )
    list_filter = ("reason",)
    search_fields = (
        "wallet__profile__user__username",
        "wallet__profile__user__email",
        "idempotency_key",
        "note",
    )
    # Every field is read-only — the ledger is immutable by design
    readonly_fields = (
        "wallet", "amount", "reason", "note", "created_by",
        "idempotency_key", "cached_balance_after",
        "tournament_id", "registration_id", "match_id",
        "created_at",
    )
    actions = ["export_csv"]

    # ── Fortress lock: ledger rows are NEVER editable from the admin ──────────
    def has_add_permission(self, request):
        return False  # Transactions created only via services.py / Fortress API

    def has_change_permission(self, request, obj=None):
        return False  # Ledger is immutable — no direct edits ever

    def has_delete_permission(self, request, obj=None):
        return False  # Preserve audit trail — no deletions ever

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

# adjust_balance action removed from here — it was operating on a Transaction
# queryset, not a Wallet queryset, making every iteration a type error.
# It now lives correctly on DeltaCrownWalletAdmin above.


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


# [FORTRESS] WithdrawalRequest — deprecated; read-only audit via Fortress
# @admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(ModelAdmin):
    """
    [DEPRECATED] Legacy DC-to-Fiat withdrawal admin.

    DC withdrawals are no longer permitted (closed-loop economy compliance).
    This admin is READ-ONLY to allow auditing of historical records.
    All add / change / delete actions are disabled.
    Use PrizeClaimAdmin (below) for official tournament prize disbursements.
    """
    list_display = ['id', 'wallet_link', 'amount', 'bdt_display', 'payment_method',
                    'status_badge', 'requested_at', 'reviewed_by_display']
    list_filter = ['status', 'payment_method', 'requested_at']
    search_fields = ['wallet__profile__user__username', 'wallet__profile__user__email',
                     'admin_note']
    readonly_fields = [
        'wallet', 'amount', 'status', 'payment_method', 'payment_number',
        'payment_details', 'dc_to_bdt_rate', 'processing_fee', 'bdt_amount',
        'requested_at', 'reviewed_at', 'reviewed_by', 'completed_at',
        'user_note', 'admin_note', 'rejection_reason', 'transaction',
    ]

    def has_add_permission(self, request):
        """Block new withdrawals — closed-loop economy."""
        return False

    def has_change_permission(self, request, obj=None):
        """Read-only audit trail."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve audit trail."""
        return False

    def wallet_link(self, obj):
        url = reverse('admin:economy_deltacrownwallet_change', args=[obj.wallet.id])
        return format_html('<a href="{}">{}</a>', url, obj.wallet.profile.user.username)
    wallet_link.short_description = 'Wallet'

    def bdt_display(self, obj):
        return f"৳{obj.bdt_amount}"
    bdt_display.short_description = 'BDT'

    def status_badge(self, obj):
        colors = {
            'pending': '#f59e0b', 'approved': '#3b82f6',
            'completed': '#10b981', 'rejected': '#ef4444', 'cancelled': '#6b7280',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'

    def reviewed_by_display(self, obj):
        return obj.reviewed_by.username if obj.reviewed_by else '—'
    reviewed_by_display.short_description = 'Reviewed By'


# [FORTRESS] PrizeClaim — managed exclusively via Financial Fortress
# @admin.register(PrizeClaim)
class PrizeClaimAdmin(ModelAdmin):
    """
    Admin interface for official tournament prize disbursements (BDT fiat).

    Workflow for admins:
      1. Review PENDING claims — verify tournament name & account details.
      2. If KYC required, use 'Start KYC Verification' action to escalate.
      3. Transfer funds externally (bKash / Nagad / Bank).
      4. Use 'Mark as PAID' action — enter the external transfer reference.
      5. Use 'Reject Claim' action with a clear rejection note if fraud suspected.
    """
    list_display = [
        'id', 'wallet_link', 'tournament_name', 'amount_bdt_display',
        'payment_method', 'status_badge', 'submitted_at', 'resolved_by_display',
    ]
    list_filter = ['status', 'payment_method', 'submitted_at']
    search_fields = [
        'wallet__profile__user__username', 'wallet__profile__user__email',
        'tournament_name', 'admin_note',
    ]
    readonly_fields = [
        'wallet', 'tournament_name', 'amount_bdt', 'payment_method',
        'account_details', 'submitted_at', 'resolved_at', 'resolved_by',
    ]
    fieldsets = [
        ('Claim Details', {
            'fields': ['wallet', 'tournament_name', 'amount_bdt'],
        }),
        ('Payout Info', {
            'fields': ['payment_method', 'account_details'],
        }),
        ('Status & Resolution', {
            'fields': ['status', 'admin_note'],
        }),
        ('Audit Trail', {
            'fields': ['submitted_at', 'resolved_at', 'resolved_by'],
            'classes': ['collapse'],
        }),
    ]
    actions = ['action_start_kyc', 'action_mark_paid', 'action_reject']

    # ── Display helpers ────────────────────────────────────────────────────────────

    def wallet_link(self, obj):
        url = reverse('admin:economy_deltacrownwallet_change', args=[obj.wallet.id])
        username = getattr(getattr(obj.wallet, 'profile', None), 'user', None)
        label = getattr(username, 'username', f'Wallet #{obj.wallet_id}')
        return format_html('<a href="{}">{}</a>', url, label)
    wallet_link.short_description = 'Claimant'

    def amount_bdt_display(self, obj):
        return format_html('<strong>৳{}</strong>', obj.amount_bdt)
    amount_bdt_display.short_description = 'Amount (BDT)'

    def status_badge(self, obj):
        colors = {
            PrizeClaim.Status.PENDING:       '#f59e0b',
            PrizeClaim.Status.VERIFYING_KYC: '#6366f1',
            PrizeClaim.Status.PAID:          '#10b981',
            PrizeClaim.Status.REJECTED:      '#ef4444',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background:{};color:#fff;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:600;">{}</span>',
            color, obj.get_status_display().upper()
        )
    status_badge.short_description = 'Status'

    def resolved_by_display(self, obj):
        return obj.resolved_by.username if obj.resolved_by else '—'
    resolved_by_display.short_description = 'Resolved By'

    # ── Actions ───────────────────────────────────────────────────────────────

    @admin.action(description='🔍 Escalate to KYC Verification')
    def action_start_kyc(self, request, queryset):
        updated = queryset.filter(status=PrizeClaim.Status.PENDING).update(
            status=PrizeClaim.Status.VERIFYING_KYC
        )
        self.message_user(request, f'{updated} claim(s) escalated to KYC verification.',
                          level=messages.SUCCESS)

    @admin.action(description='✅ Mark selected claims as PAID')
    def action_mark_paid(self, request, queryset):
        paid = skipped = 0
        for claim in queryset:
            try:
                claim.mark_paid(admin_user=request.user)
                paid += 1
            except ValueError as exc:
                self.message_user(request, f'Claim #{claim.id}: {exc}',
                                  level=messages.WARNING)
                skipped += 1
        if paid:
            self.message_user(
                request,
                f'{paid} claim(s) marked PAID. '
                f'Remember to record the transfer reference in admin_note.',
                level=messages.SUCCESS,
            )

    @admin.action(description='❌ Reject selected claims')
    def action_reject(self, request, queryset):
        rejected = skipped = 0
        for claim in queryset:
            try:
                claim.reject(
                    admin_user=request.user,
                    reason=f'Bulk rejected by {request.user.username}',
                )
                rejected += 1
            except ValueError as exc:
                self.message_user(request, f'Claim #{claim.id}: {exc}',
                                  level=messages.WARNING)
                skipped += 1
        if rejected:
            self.message_user(request, f'{rejected} claim(s) rejected.',
                              level=messages.WARNING)


# [FORTRESS] CoinPolicy — legacy; read-only via Fortress audit log
# @admin.register(CoinPolicy)
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


# =============================================================================
# ECONOMY PLAYBOOK — Internal Financial Documentation
# =============================================================================

from .models import EconomyPlaybook


# [FORTRESS] EconomyPlaybook — internal doc; no admin editing
# @admin.register(EconomyPlaybook)
class EconomyPlaybookAdmin(ModelAdmin):
    """
    Admin-editable knowledge base for internal economy rules and SOPs.

    Admins can create, read, and update playbook articles covering:
      • Treasury minting procedures
      • Prize claim disbursement SOPs
      • Escrow wager limits (manual vs API games)
      • KYC verification checklists
      • Closed-loop economy compliance policy

    Articles are never exposed to end-users.
    """
    list_display  = ('title', 'slug', 'updated_at', 'content_preview')
    search_fields = ('title', 'content')
    readonly_fields = ('slug', 'updated_at')
    prepopulated_fields = {}  # slug is auto-generated in model.save()

    fieldsets = [
        ('Article', {
            'fields': ['title', 'slug'],
        }),
        ('Content (Markdown / Plain Text)', {
            'fields': ['content'],
            'description': (
                'Use ## for headings, - for bullets, ``` for code blocks. '
                'This content is only visible to admin staff.'
            ),
        }),
        ('Meta', {
            'fields': ['updated_at'],
            'classes': ['collapse'],
        }),
    ]

    def content_preview(self, obj):
        """Show first 120 chars of content as a quick preview in the list view."""
        preview = obj.content[:120]
        if len(obj.content) > 120:
            preview += '…'
        return preview
    content_preview.short_description = 'Preview'

    def has_delete_permission(self, request, obj=None):
        """Only superusers may delete playbook articles."""
        return request.user.is_superuser


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


# =============================================================================
# ECONOMY CONFIGURATION & DASHBOARD ADMIN  (Phase 2 / Phase 3)
# =============================================================================

class MintToTreasuryForm(forms.Form):
    """Superuser-only form to credit the Master Treasury with freshly minted DC."""
    bdt_amount = forms.DecimalField(
        min_value=1,
        max_digits=12,
        decimal_places=2,
        label="BDT Amount Received (৳)",
        help_text="Real-world BDT deposited. DC is calculated using the current exchange rate.",
    )
    note = forms.CharField(
        max_length=255,
        required=False,
        label="Reference Note",
        initial="Genesis Mint / Admin Fiat Deposit",
    )


@admin.register(EconomyConfig)
class EconomyConfigAdmin(ModelAdmin):
    """
    Singleton admin for EconomyConfig.
    Only one row (pk=1) is meaningful; Add and Delete are hidden.
    Hosts the Economy Command Center dashboard at /admin/economy/economyconfig/dashboard/
    """
    list_display = ("__str__", "bdt_per_dc", "dc_per_bdt_display",
                    "top_up_min_dc", "withdrawal_min_dc", "withdrawal_fee_pct",
                    "updated_at", "dashboard_link")
    readonly_fields = ("updated_at", "dc_per_bdt_display")

    fieldsets = [
        ("Exchange Rate", {
            "fields": ["bdt_per_dc", "dc_per_bdt_display"],
            "description": (
                "Set <strong>bdt_per_dc</strong> to control how many BDT a single DeltaCoin costs. "
                "Default: 0.1000 → 1 BDT = 10 DC."
            ),
        }),
        ("Top-Up Policy", {"fields": ["top_up_min_dc"]}),
        ("Withdrawal Policy", {"fields": ["withdrawal_min_dc", "withdrawal_fee_pct"]}),
        ("Meta", {"fields": ["updated_at"], "classes": ["collapse"]}),
    ]

    # ------------------------------------------------------------------
    # Singleton enforcement
    # ------------------------------------------------------------------

    def has_add_permission(self, request):
        return not EconomyConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def dc_per_bdt_display(self, obj):
        return format_html(
            "<strong style='color:#10b981;font-size:16px;'>{}</strong> DC per BDT",
            obj.dc_per_bdt,
        )
    dc_per_bdt_display.short_description = "Effective rate (DC per BDT)"

    def dashboard_link(self, obj):
        url = reverse("admin:economy_dashboard")
        return format_html(
            '<a class="button" href="{}" style="background:#6366f1;color:#fff;'
            'padding:4px 14px;border-radius:6px;font-size:.8rem;white-space:nowrap;">'
            '💰 Open Dashboard</a>',
            url,
        )
    dashboard_link.short_description = "Command Center"

    # ------------------------------------------------------------------
    # Custom URL: /admin/economy/economyconfig/dashboard/
    # ------------------------------------------------------------------

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom = [
            path(
                "dashboard/",
                self.admin_site.admin_view(self.dashboard_view),
                name="economy_dashboard",
            ),
        ]
        return custom + urls

    # ------------------------------------------------------------------
    # Dashboard view
    # ------------------------------------------------------------------

    def dashboard_view(self, request):
        from decimal import Decimal
        from django.db import transaction as db_transaction
        from django.db.models import Sum
        from django.contrib import messages as dj_messages
        from django.utils import timezone
        from .models import DeltaCrownTransaction, DeltaCrownWallet
        from .services import get_master_treasury

        config = EconomyConfig.get_solo()
        treasury = get_master_treasury()

        # ---- Live metrics -------------------------------------------- #
        circulating_supply = int(
            DeltaCrownWallet.objects
            .filter(is_treasury=False)
            .aggregate(total=Sum("cached_balance"))["total"] or 0
        )
        fiat_reserve_required = Decimal(str(circulating_supply)) * config.bdt_per_dc

        # ---- Mint form (POST) ---------------------------------------- #
        mint_form = None
        if request.user.is_superuser:
            if request.method == "POST" and "mint_submit" in request.POST:
                mint_form = MintToTreasuryForm(request.POST)
                if mint_form.is_valid():
                    bdt_amount = mint_form.cleaned_data["bdt_amount"]
                    note = mint_form.cleaned_data.get("note") or "Genesis Mint / Admin Fiat Deposit"
                    dc_amount = int(bdt_amount / config.bdt_per_dc)
                    if dc_amount > 0:
                        with db_transaction.atomic():
                            DeltaCrownTransaction.objects.create(
                                wallet=treasury,
                                amount=dc_amount,
                                reason=DeltaCrownTransaction.Reason.MANUAL_ADJUST,
                                note=note,
                                created_by=request.user,
                                idempotency_key=(
                                    f"mint_treasury_{request.user.id}"
                                    f"_{int(timezone.now().timestamp())}"
                                ),
                            )
                            treasury.recalc_and_save()
                        dj_messages.success(
                            request,
                            f"✅ Minted {dc_amount:,} DC to Treasury "
                            f"(৳{bdt_amount} BDT deposited at {config.dc_per_bdt} DC/BDT).",
                        )
                        treasury.refresh_from_db()
                        # Recalculate after mint for fresh metrics
                        circulating_supply = int(
                            DeltaCrownWallet.objects
                            .filter(is_treasury=False)
                            .aggregate(total=Sum("cached_balance"))["total"] or 0
                        )
                        fiat_reserve_required = Decimal(str(circulating_supply)) * config.bdt_per_dc
                        mint_form = MintToTreasuryForm(
                            initial={"note": "Genesis Mint / Admin Fiat Deposit"}
                        )
                    else:
                        dj_messages.error(request, "BDT amount too small to mint any DC.")
            else:
                mint_form = MintToTreasuryForm(
                    initial={"note": "Genesis Mint / Admin Fiat Deposit"}
                )

        # ---- Recent treasury transactions ---------------------------- #
        recent_treasury_txns = (
            DeltaCrownTransaction.objects
            .filter(wallet=treasury)
            .select_related("created_by")
            .order_by("-created_at")[:20]
        )

        from django.template.response import TemplateResponse
        return TemplateResponse(
            request,
            "admin/economy/economy_dashboard.html",
            {
                **self.admin_site.each_context(request),
                "title": "Economy Command Center",
                "opts": self.model._meta,
                "config": config,
                "treasury": treasury,
                "circulating_supply": circulating_supply,
                "fiat_reserve_required": fiat_reserve_required,
                "mint_form": mint_form,
                "recent_treasury_txns": recent_treasury_txns,
            },
        )


# =============================================================================
# ECONOMY DASHBOARD SIDEBAR PROXY ADMIN  (Phase 3.5 — navigation shim)
# =============================================================================

@admin.register(EconomyDashboard)
class EconomyDashboardAdmin(ModelAdmin):
    """
    Sidebar navigation shim.

    Django's get_app_list() evaluates ALL four permission checks before
    including a model link in the sidebar. All four must return a truthy
    value — overriding only module/view is not enough. has_add and
    has_change are also checked internally even for display-only entries.

    changelist_view immediately 302s to the real dashboard URL so the
    link acts as a pure navigation shim with no list/change/delete UI.
    """

    def changelist_view(self, request, extra_context=None):
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(reverse("admin:economy_dashboard"))

    # ── All four must return True for the sidebar link to render ──────────
    def has_module_permission(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return request.user.is_staff

    # ── Delete stays blocked — never expose a destructive action ──────────
    def has_delete_permission(self, request, obj=None):
        return False


# =============================================================================
# FINANCIAL FORTRESS SIDEBAR PROXY ADMIN  (Phase A — Fortress entry point)
# =============================================================================

# [FORTRESS] FinancialFortress proxy — sidebar link now injected via UNFOLD SIDEBAR config
# @admin.register(FinancialFortress)
class FinancialFortressAdmin(ModelAdmin):
    """
    Superuser-only navigation shim that creates the '🛡️ Financial Fortress'
    entry in the Django Admin sidebar.

    Clicking the link immediately 302s to the secure fortress_dashboard view.
    All four Django permission checks return True ONLY for superusers so the
    link is invisible to regular staff / partial admins.
    """

    def changelist_view(self, request, extra_context=None):
        from django.http import HttpResponseRedirect
        if not request.user.is_superuser:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Financial Fortress: superuser access required.")
        return HttpResponseRedirect(reverse("economy:fortress_dashboard"))

    # ── All four must return True for the sidebar link to render ──────────
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False  # Never expose a destructive action on a proxy shim


# =============================================================================
# FORTRESS READ-ONLY RE-REGISTRATION
# =============================================================================
# The 8 ledger models below were previously unregistered to prevent manual
# corruption.  However, un-registering them breaks existing templates that
# reference their changelist URLs via {% url 'admin:economy_..._changelist' %}.
#
# FIX: Re-register every model using thin subclasses that inherit from
# ReadOnlyFortressMixin FIRST (highest MRO priority), making them view-only:
# → has_add_permission    → False
# → has_change_permission → False
# → has_delete_permission → False
#
# All ledger mutations must go through the Fortress API service layer only.
# =============================================================================

class ReadOnlyFortressMixin:
    """
    Fortress security mixin: makes any ModelAdmin fully read-only.
    All three write-permission methods unconditionally return False,
    overriding any methods defined in the subclass or base ModelAdmin.

    Signatures match Django's ModelAdmin calling convention exactly:
      has_add_permission(request, obj=None)
      has_change_permission(request, obj=None)
      has_delete_permission(request, obj=None)
    """
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        """Explicitly allow viewing — read-only means read, not blind."""
        return request.user.is_active and (request.user.is_staff or request.user.is_superuser)


# Import models that need to be re-registered (not already imported above)
from .models import EconomyPlaybook  # noqa: E402  (imported at module scope)


@admin.register(DeltaCrownWallet)
class _ReadOnlyWalletAdmin(ReadOnlyFortressMixin, DeltaCrownWalletAdmin):
    """View-only mirror of DeltaCrownWalletAdmin — write paths blocked."""


@admin.register(DeltaCrownTransaction)
class _ReadOnlyTransactionAdmin(ReadOnlyFortressMixin, DeltaCrownTransactionAdmin):
    """View-only mirror of DeltaCrownTransactionAdmin — write paths blocked."""


@admin.register(TopUpRequest)
class _ReadOnlyTopUpAdmin(ReadOnlyFortressMixin, TopUpRequestAdmin):
    """View-only mirror of TopUpRequestAdmin — write paths blocked."""


@admin.register(WithdrawalRequest)
class _ReadOnlyWithdrawalAdmin(ReadOnlyFortressMixin, WithdrawalRequestAdmin):
    """View-only mirror of WithdrawalRequestAdmin — write paths blocked."""


@admin.register(PrizeClaim)
class _ReadOnlyPrizeClaimAdmin(ReadOnlyFortressMixin, PrizeClaimAdmin):
    """View-only mirror of PrizeClaimAdmin — write paths blocked."""


@admin.register(CoinPolicy)
class _ReadOnlyCoinPolicyAdmin(ReadOnlyFortressMixin, CoinPolicyAdmin):
    """View-only mirror of CoinPolicyAdmin — write paths blocked."""


@admin.register(EconomyPlaybook)
class _ReadOnlyPlaybookAdmin(ReadOnlyFortressMixin, EconomyPlaybookAdmin):
    """View-only mirror of EconomyPlaybookAdmin — write paths blocked."""
