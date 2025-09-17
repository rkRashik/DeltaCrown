from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import EmailOTP, PendingSignup, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "is_active", "is_verified", "is_staff")
    list_filter = ("is_verified", "is_active", "is_staff")
    search_fields = ("username", "email")
    ordering = ("username",)
    fieldsets = (
        (None, {"fields": ("username", "password")} ),
        ("Personal info", {"fields": ("first_name", "last_name", "email")} ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined", "email_verified_at")} ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(PendingSignup)
class PendingSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "username", "created_at")
    search_fields = ("email", "username")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ("target", "purpose", "code", "created_at", "expires_at", "is_used", "attempts")
    search_fields = (
        "user__username",
        "user__email",
        "pending_signup__username",
        "pending_signup__email",
        "code",
    )
    list_filter = ("purpose", "is_used")
    readonly_fields = ("created_at", "expires_at", "attempts")

    def has_add_permission(self, request):
        return False

    def expire_status(self, obj):
        return "expired" if timezone.now() > obj.expires_at else "active"

    def target(self, obj):
        if obj.user:
            return obj.user.email
        if obj.pending_signup:
            return f"Pending: {obj.pending_signup.email}"
        return "-"
    target.short_description = "Target"
