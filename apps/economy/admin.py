# apps/economy/admin.py
from __future__ import annotations

from django import forms
from django.contrib import admin, messages
from django.db.models import Sum
from django.http import HttpRequest

from .models import CoinPolicy, DeltaCrownTransaction, DeltaCrownWallet


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
