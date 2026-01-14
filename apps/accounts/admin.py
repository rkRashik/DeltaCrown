from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import EmailOTP, PendingSignup, User, AccountDeletionRequest
from apps.user_profile.models import SocialLink


class SocialLinkInline(admin.TabularInline):
    """Inline social links editor for Discord Link + other platforms"""
    model = SocialLink
    extra = 0
    fields = ['platform', 'url', 'handle', 'is_verified']
    readonly_fields = ['is_verified']
    verbose_name = "Social Link"
    verbose_name_plural = "Social Links (Discord, Twitter, YouTube, etc.)"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "is_active", "is_verified", "is_staff")
    inlines = [SocialLinkInline]
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


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ('user_username', 'status', 'requested_at', 'scheduled_for', 'days_remaining_display', 'can_cancel_display')
    list_filter = ('status', 'requested_at', 'scheduled_for')
    search_fields = ('user__username', 'user__email', 'reason')
    readonly_fields = ('requested_at', 'canceled_at', 'completed_at', 'last_ip', 'last_user_agent')
    autocomplete_fields = ('user',)
    date_hierarchy = 'requested_at'
    
    fieldsets = (
        ('User', {
            'fields': ('user', 'status')
        }),
        ('Timing', {
            'fields': ('requested_at', 'scheduled_for', 'canceled_at', 'completed_at')
        }),
        ('Details', {
            'fields': ('reason', 'confirmation_phrase')
        }),
        ('Metadata', {
            'fields': ('last_ip', 'last_user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    def user_username(self, obj):
        return obj.user.username
    user_username.short_description = 'Username'
    user_username.admin_order_field = 'user__username'
    
    def days_remaining_display(self, obj):
        days = obj.days_remaining()
        if days is None:
            return '-'
        return f"{days} days"
    days_remaining_display.short_description = 'Days Remaining'
    
    def can_cancel_display(self, obj):
        return '✓' if obj.is_cancellable() else '✗'
    can_cancel_display.short_description = 'Can Cancel'
    can_cancel_display.boolean = True
