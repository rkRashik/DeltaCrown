from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from apps.user_profile.models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "is_private", "show_email", "show_phone", "show_socials")
    list_filter = ("is_private", "show_email", "show_phone", "show_socials")
    search_fields = ("user__username", "user__email")

try:
    admin.site.register(UserProfile, UserProfileAdmin)
except AlreadyRegistered:
    pass
