from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import EmailOTP, PendingSignup, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Enhanced User Admin with UUID support and extended profile fields.
    """
    list_display = (
        "username",
        "email",
        "role",
        "is_active",
        "is_verified",
        "is_staff",
        "date_joined"
    )
    list_filter = (
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined"
    )
    search_fields = ("username", "email", "first_name", "last_name", "phone_number")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "uuid", "date_joined", "last_login", "email_verified_at")
    
    fieldsets = (
        (None, {
            "fields": ("id", "uuid", "username", "password")
        }),
        ("Personal Info", {
            "fields": (
                "first_name",
                "last_name",
                "email",
                "phone_number",
                "date_of_birth",
                "country"
            )
        }),
        ("Profile", {
            "fields": ("avatar", "bio")
        }),
        ("Role & Permissions", {
            "fields": (
                "role",
                "is_active",
                "is_verified",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Important Dates", {
            "fields": ("last_login", "date_joined", "email_verified_at")
        }),
    )
    
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "email",
                "password1",
                "password2",
                "role",
                "is_staff",
                "is_superuser"
            ),
        }),
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make UUID readonly after creation."""
        if obj:  # Editing existing object
            return self.readonly_fields + ("username",)
        return self.readonly_fields


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
