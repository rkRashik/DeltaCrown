# apps/user_profile/admin/users.py
from django.contrib import admin

from ..models import UserProfile
from .exports import export_userprofiles_csv


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "created_at")
    search_fields = ("user__username", "display_name", "user__email")
    list_filter = ()
    date_hierarchy = "created_at"
    actions = [export_userprofiles_csv]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Optimize common relation; ignore if schema differs
        try:
            return qs.select_related("user")
        except Exception:
            return qs
