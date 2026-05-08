from django.contrib import admin

from .models import ContractEnrollment, ContractTemplate


@admin.register(ContractTemplate)
class ContractTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "title", "game", "entry_fee_dc", "reward_dc",
        "duration_hours", "is_active", "valid_from", "valid_until",
    )
    list_filter = ("is_active", "game", "goal_type")
    search_fields = ("title", "description", "badge_slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ContractEnrollment)
class ContractEnrollmentAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code", "user", "template", "status",
        "closure_reason", "deadline_at", "enrolled_at",
    )
    list_filter = ("status", "closure_reason", "template__game")
    search_fields = ("reference_code", "user__username", "template__title")
    readonly_fields = (
        "reference_code", "enrolled_at", "resolved_at",
        "escrow_lock_txn", "reward_payout_txn",
    )
