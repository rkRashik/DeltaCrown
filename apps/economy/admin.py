from __future__ import annotations

from django.contrib import admin
from django.db.models import Sum

from .models import DeltaCrownWallet, DeltaCrownTransaction, CoinPolicy


@admin.register(DeltaCrownWallet)
class DeltaCrownWalletAdmin(admin.ModelAdmin):
    list_display = ("id", "profile_display", "cached_balance", "updated_at")
    search_fields = ("profile__user__username", "profile__user__email")
    readonly_fields = ("created_at", "updated_at", "cached_balance")

    def profile_display(self, obj):
        u = getattr(obj.profile, "user", None)
        return getattr(u, "username", None) or getattr(u, "email", None) or obj.profile_id
    profile_display.short_description = "Profile"


@admin.register(DeltaCrownTransaction)
class DeltaCrownTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "wallet", "amount", "reason", "tournament", "registration", "match", "created_at")
    list_filter = ("reason", "tournament")
    search_fields = ("wallet__profile__user__username", "wallet__profile__user__email", "registration__id")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("wallet", "tournament", "registration", "match")


class CoinPolicyInline(admin.StackedInline):
    model = CoinPolicy
    can_delete = False
    extra = 0
    fk_name = "tournament"
    fields = ("enabled", "participation", "top4", "runner_up", "winner")
