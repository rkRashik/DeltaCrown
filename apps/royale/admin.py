from django.contrib import admin, messages
from django.db.models import Count
from unfold.admin import ModelAdmin, TabularInline

from .models import RoyaleEntry, RoyaleLobby
from .services import RoyaleService

RoyaleLobby._meta.verbose_name = "Dropzone Lobby"
RoyaleLobby._meta.verbose_name_plural = "Dropzone Lobbies"
RoyaleEntry._meta.verbose_name = "Dropzone Entry"
RoyaleEntry._meta.verbose_name_plural = "Dropzone Entries"


class RoyaleEntryInline(TabularInline):
    model = RoyaleEntry
    extra = 0
    can_delete = False
    fields = (
        "user", "status", "placement", "kills", "score_summary",
        "escrow_state", "closure_reason", "reserved_at", "scored_at",
        "resolved_at",
    )
    readonly_fields = (
        "user", "status", "score_summary", "escrow_state",
        "closure_reason", "reserved_at", "scored_at", "resolved_at",
    )

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Score")
    def score_summary(self, obj):
        if obj.placement is None:
            return "Unscored"
        kills = obj.kills if obj.kills is not None else 0
        return f"#{obj.placement} / {kills} kills"

    @admin.display(description="Escrow")
    def escrow_state(self, obj):
        return RoyaleEntryAdmin.entry_escrow_state_static(obj)


@admin.register(RoyaleLobby)
class RoyaleLobbyAdmin(ModelAdmin):
    """Service-backed admin interface for Dropzone lobbies."""

    list_display = (
        "reference_code", "title", "game", "status", "scheduled_at",
        "reserved_slots_display", "entry_fee_dc", "prize_summary",
        "room_status", "settlement_state",
    )
    list_filter = ("status", "closure_reason", "game", "is_public", "is_featured")
    search_fields = ("reference_code", "title", "tournament__name", "tournament__title")
    readonly_fields = (
        "reference_code", "status", "reserved_slots_display", "total_pot_display",
        "prize_summary", "room_status", "settlement_state",
        "closure_reason", "closure_note", "created_at", "updated_at",
    )
    autocomplete_fields = ("tournament", "game", "created_by")
    date_hierarchy = "scheduled_at"
    inlines = (RoyaleEntryInline,)
    actions = (
        "record_scores_from_entries",
        "settle_selected_lobbies",
        "cancel_refund_selected_lobbies",
        "mark_selected_lobbies_live",
        "close_selected_reservations",
    )

    fieldsets = (
        ("Dropzone Lobby", {
            "fields": ("reference_code", "title", "tournament", "game", "status"),
        }),
        ("Capacity & Reward", {
            "fields": (
                "slot_capacity", "reserved_slots_display", "entry_fee_dc",
                "total_pot_display", "prize_distribution", "prize_summary",
            ),
        }),
        ("Schedule", {
            "fields": ("scheduled_at", "registration_opens_at", "registration_closes_at"),
        }),
        ("Room Credentials", {
            "fields": ("room_id", "room_password", "room_status"),
            "description": "Credentials remain editable for operators and are only revealed publicly by API redaction rules.",
        }),
        ("Closure", {
            "fields": ("closure_reason", "closure_note", "settlement_state"),
        }),
        ("Visibility", {
            "fields": ("is_public", "is_featured"),
        }),
        ("Meta", {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "game", "tournament", "created_by",
        ).annotate(_entry_count=Count("entries"))

    @admin.display(description="Reserved")
    def reserved_slots_display(self, obj):
        try:
            reserved = obj.reserved_count
        except Exception:
            reserved = getattr(obj, "_entry_count", 0)
        return f"{reserved}/{obj.slot_capacity}"

    @admin.display(description="Total pot")
    def total_pot_display(self, obj):
        return f"{obj.total_pot_dc} DC"

    @admin.display(description="Prize distribution")
    def prize_summary(self, obj):
        cfg = obj.prize_distribution or {}
        mode = (cfg.get("mode") or "PERCENT").upper()
        splits = cfg.get("splits") or {}
        if not splits:
            return "No prize split configured"
        preview = ", ".join(f"#{place}: {amount}" for place, amount in list(splits.items())[:3])
        suffix = "%" if mode == "PERCENT" else " DC"
        return f"{mode}: {preview}{suffix}"

    @admin.display(description="Room")
    def room_status(self, obj):
        if obj.room_id and obj.room_password:
            return "Credentials set"
        if obj.room_id:
            return "Room ID set"
        return "Missing credentials"

    @admin.display(description="Settlement")
    def settlement_state(self, obj):
        if obj.status == "SETTLED":
            return "Settled"
        if obj.status == "CANCELLED":
            return "Cancelled/refunded"
        if obj.status == "SCORING":
            return "Ready for settlement"
        return "Open"

    def _run_lobby_action(self, request, queryset, callback, success_label):
        success_count = 0
        error_count = 0
        for lobby in queryset:
            try:
                callback(lobby)
                success_count += 1
            except Exception as exc:
                error_count += 1
                self.message_user(
                    request,
                    f"{lobby.reference_code}: {exc}",
                    level=messages.ERROR,
                )
        if success_count:
            self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
        if error_count:
            self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

    @admin.action(description="Record scores from entered placements/kills")
    def record_scores_from_entries(self, request, queryset):
        self._run_lobby_action(
            request,
            queryset,
            lambda lobby: RoyaleService.admin_record_scores_from_entries(
                lobby_id=lobby.pk,
                actor=request.user,
            ),
            "Recorded Dropzone scores",
        )

    @admin.action(description="Settle selected Dropzone lobbies")
    def settle_selected_lobbies(self, request, queryset):
        self._run_lobby_action(
            request,
            queryset,
            lambda lobby: RoyaleService.admin_settle_lobby(
                lobby_id=lobby.pk,
                actor=request.user,
                note=f"Settled from Django admin by {request.user.username}.",
            ),
            "Settled Dropzone lobbies",
        )

    @admin.action(description="Cancel/refund selected Dropzone lobbies")
    def cancel_refund_selected_lobbies(self, request, queryset):
        self._run_lobby_action(
            request,
            queryset,
            lambda lobby: RoyaleService.admin_cancel_lobby(
                lobby_id=lobby.pk,
                actor=request.user,
                note=f"Cancelled/refunded from Django admin by {request.user.username}.",
            ),
            "Cancelled/refunded Dropzone lobbies",
        )

    @admin.action(description="Mark selected Dropzone lobbies live")
    def mark_selected_lobbies_live(self, request, queryset):
        self._run_lobby_action(
            request,
            queryset,
            lambda lobby: RoyaleService.admin_mark_live(
                lobby_id=lobby.pk,
                actor=request.user,
                note=f"Marked live from Django admin by {request.user.username}.",
            ),
            "Marked Dropzone lobbies live",
        )

    @admin.action(description="Close selected Dropzone reservations")
    def close_selected_reservations(self, request, queryset):
        self._run_lobby_action(
            request,
            queryset,
            lambda lobby: RoyaleService.admin_close_reservations(
                lobby_id=lobby.pk,
                actor=request.user,
                note=f"Reservations closed from Django admin by {request.user.username}.",
            ),
            "Closed Dropzone reservations",
        )


@admin.register(RoyaleEntry)
class RoyaleEntryAdmin(ModelAdmin):
    """Admin interface for Dropzone entries.

    Placement and kills are intentionally editable as the MVP scoring input.
    Settlement, refund, and lifecycle transitions stay service-backed.
    """

    list_display = (
        "lobby", "user", "status", "placement", "kills",
        "entry_escrow_state", "closure_reason", "reserved_at",
        "scored_at", "resolved_at",
    )
    list_filter = ("status", "closure_reason", "lobby__game")
    search_fields = ("lobby__reference_code", "lobby__title", "user__username", "user__email")
    readonly_fields = (
        "status", "reserved_at", "scored_at", "resolved_at",
        "escrow_lock_txn", "payout_txn", "closure_reason", "closure_note",
        "entry_escrow_state",
    )
    autocomplete_fields = ("lobby", "user")
    raw_id_fields = ("escrow_lock_txn", "payout_txn")
    date_hierarchy = "reserved_at"

    fieldsets = (
        ("Dropzone Entry", {
            "fields": ("lobby", "user", "status"),
        }),
        ("Scoring Input", {
            "fields": ("placement", "kills"),
            "description": "Operators may enter placement and kills here, then run the lobby scoring action.",
        }),
        ("Escrow & Settlement", {
            "fields": ("entry_escrow_state", "escrow_lock_txn", "payout_txn"),
            "classes": ("collapse",),
        }),
        ("Closure", {
            "fields": ("closure_reason", "closure_note"),
        }),
        ("Timestamps", {
            "fields": ("reserved_at", "scored_at", "resolved_at"),
            "classes": ("collapse",),
        }),
    )

    @staticmethod
    def entry_escrow_state_static(obj):
        if obj.payout_txn_id:
            return "Settled/refunded"
        if obj.escrow_lock_txn_id:
            return "Entry locked"
        if obj.lobby and obj.lobby.entry_fee_dc:
            return "Missing lock"
        return "Free entry"

    @admin.display(description="Escrow")
    def entry_escrow_state(self, obj):
        return self.entry_escrow_state_static(obj)
