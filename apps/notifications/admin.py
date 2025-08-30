from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "title",
        "recipient_username",
        "ref_display",
        "is_read",
        "created_at",
    )
    list_filter  = ("type", "is_read", "created_at")
    search_fields = (
        "title", "body", "url",
        "recipient__user__username", "recipient__display_name",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    raw_id_fields = ("recipient", "tournament", "match")

    def recipient_username(self, obj):
        u = getattr(obj.recipient, "user", None)
        return getattr(u, "username", obj.recipient_id)
    recipient_username.short_description = "Recipient"

    def ref_display(self, obj):
        if obj.match_id:
            return f"match #{obj.match_id}"
        if obj.tournament_id:
            return f"tournament #{obj.tournament_id}"
        return "-"
    ref_display.short_description = "Ref"

    actions = ("mark_as_read", "mark_as_unread")

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"Marked {updated} notification(s) as read.")
    mark_as_read.short_description = "Mark selected as read"

    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"Marked {updated} notification(s) as unread.")
    mark_as_unread.short_description = "Mark selected as unread"
