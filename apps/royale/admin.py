from django.contrib import admin

from .models import RoyaleEntry, RoyaleLobby


@admin.register(RoyaleLobby)
class RoyaleLobbyAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code", "title", "game", "status",
        "slot_capacity", "entry_fee_dc", "scheduled_at", "closure_reason",
    )
    list_filter = ("status", "closure_reason", "game", "is_public", "is_featured")
    search_fields = ("reference_code", "title")
    readonly_fields = ("reference_code", "created_at", "updated_at")
    autocomplete_fields = ("tournament", "game", "created_by")


@admin.register(RoyaleEntry)
class RoyaleEntryAdmin(admin.ModelAdmin):
    list_display = (
        "lobby", "user", "status", "placement", "kills",
        "closure_reason", "reserved_at",
    )
    list_filter = ("status", "closure_reason", "lobby__game")
    search_fields = ("lobby__reference_code", "user__username")
    readonly_fields = (
        "reserved_at", "scored_at", "resolved_at",
        "escrow_lock_txn", "payout_txn",
    )
    autocomplete_fields = ("lobby", "user")
