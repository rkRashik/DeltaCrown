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
        "tournament",
        "registration",
        "match",
        "created_by",
        "created_at",
    )
    list_filter = ("reason", "tournament")
    search_fields = (
        "wallet__profile__user__username",
        "wallet__profile__user__email",
        "registration__id",
        "idempotency_key",
        "note",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("wallet", "tournament", "registration", "match", "created_by")
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


class CoinPolicyInline(admin.StackedInline):
    model = CoinPolicy
    can_delete = False
    extra = 0
    fk_name = "tournament"
    fields = ("enabled", "participation", "top4", "runner_up", "winner")


# Hook this inline into Tournament admin if available (best-effort)
try:
    from django.contrib import admin as _admin
    from apps.tournaments.models import Tournament as _Tournament

    class _TournamentPolicyMixin:
        inlines = [CoinPolicyInline]

    # If a TournamentAdmin exists, mix in our inline dynamically.
    _reg = _admin.site._registry.get(_Tournament)
    if _reg:
        # Monkey-patch the class to include our inline without re-registering
        if CoinPolicyInline not in getattr(_reg.__class__, "inlines", []):
            _reg.__class__.inlines = list(getattr(_reg.__class__, "inlines", [])) + [CoinPolicyInline]  # type: ignore
except Exception:
    # Never break admin on import issues
    pass
