# apps/user_profile/admin/users.py
from django.contrib import admin

from ..models import UserProfile
from .exports import export_userprofiles_csv


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "coin_balance", "created_at")
    search_fields = ("user__username", "display_name", "user__email")
    list_filter = ()
    date_hierarchy = "created_at"
    actions = [export_userprofiles_csv]

    # UX + perf
    list_select_related = ("user",)
    autocomplete_fields = ("user",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        try:
            return qs.select_related("user")
        except Exception:
            return qs


    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Optimize common relation; ignore if schema differs
        try:
            return qs.select_related("user")
        except Exception:
            return qs

    def coin_balance(self, obj):
        wallet = getattr(obj, "dc_wallet", None)
        return wallet.cached_balance if wallet else 0

    coin_balance.short_description = "ΔC Coins"
