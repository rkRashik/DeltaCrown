"""Admin registrations for the custom user model and OTPs."""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import EmailOTP

User = get_user_model()


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (*DjangoUserAdmin.fieldsets, (_("Verification"), {"fields": ("is_verified",)}))
    list_display = DjangoUserAdmin.list_display + ("is_verified",)
    list_filter = DjangoUserAdmin.list_filter + ("is_verified",)
    readonly_fields = getattr(DjangoUserAdmin, "readonly_fields", ())


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "code", "created_at", "expires_at", "is_used", "attempts")
    search_fields = ("user__username", "user__email", "code")
    list_filter = ("purpose", "is_used")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "expires_at", "code")
