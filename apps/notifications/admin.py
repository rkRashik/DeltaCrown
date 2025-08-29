from django.contrib import admin
from .models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "type", "title", "is_read", "tournament", "match", "created_at")
    list_filter = ("type", "is_read", "tournament")
    search_fields = ("title", "body", "recipient__display_name", "recipient__user__username")
    autocomplete_fields = ("recipient", "tournament", "match")
