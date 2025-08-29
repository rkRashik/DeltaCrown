from django.contrib import admin
from .models import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "region", "discord_id", "riot_id", "efootball_id", "created_at")
    list_filter = ("region",)
    search_fields = ("user__username", "user__email", "display_name", "discord_id", "riot_id", "efootball_id")
