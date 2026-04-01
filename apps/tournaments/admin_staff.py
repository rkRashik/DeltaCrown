"""
Tournament Staff Management - Django Admin Configuration

⚠️ LEGACY: This Django admin customization is DEPRECATED as of Phase 7, Epic 7.6.
The new Staffing Management (Epic 7.3) and Organizer Console provide superior UX for staff role/assignment management.

This file is retained ONLY for:
1. Emergency administrative access (super admin use only)
2. Backward compatibility
3. System role management (until fully migrated to Organizer Console)

SCHEDULED FOR REMOVAL: Phase 8+
REPLACEMENT: Staffing Management UI (Epic 7.3)

Provides admin interfaces for managing tournament staff roles and assignments.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.contrib import messages

from apps.tournaments.models import TournamentStaffRole


@admin.register(TournamentStaffRole)
class TournamentStaffRoleAdmin(ModelAdmin):
    """Admin interface for managing staff roles and permissions."""
    
    list_display = [
        'name', 'slug', 'permission_summary', 'staff_count', 
        'is_system_role', 'is_active', 'created_at'
    ]
    list_filter = ['is_system_role', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created_at', 'updated_at', 'staff_count']
    prepopulated_fields = {'slug': ('name',)}
    list_per_page = 25

    def get_queryset(self, request):
        """Annotate staff count to avoid per-row queries."""
        return super().get_queryset(request).annotate(
            _active_staff_count=Count(
                'staff_assignments',
                filter=Q(staff_assignments__is_active=True),
            )
        )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'is_active')
        }),
        ('Tournament Management Permissions', {
            'fields': (
                'can_review_participants',
                'can_verify_payments',
                'can_manage_brackets',
                'can_manage_matches',
                'can_enter_scores',
                'can_handle_disputes',
                'can_send_notifications',
                'can_manage_social_media',
                'can_access_support',
                'can_modify_tournament',
            ),
            'description': 'Grant permissions for tournament operations'
        }),
        ('Data Access Permissions', {
            'fields': (
                'can_view_pii',
                'can_view_payment_proofs',
                'can_export_data',
            ),
            'description': 'Control access to sensitive data (PII compliance)'
        }),
        ('System', {
            'fields': ('is_system_role', 'created_at', 'updated_at', 'staff_count'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_roles', 'deactivate_roles', 'clone_role']
    
    def permission_summary(self, obj):
        """Display granted permissions as badges."""
        permissions = obj.get_permissions_summary()
        if not permissions:
            return format_html('<span style="color: gray;">No permissions</span>')
        
        # Show first 3 permissions, then count
        badges = []
        for perm in permissions[:3]:
            badges.append(f'<span style="background: #2196F3; color: white; padding: 2px 8px; '
                         f'border-radius: 3px; margin-right: 4px; font-size: 11px;">{perm}</span>')
        
        if len(permissions) > 3:
            badges.append(f'<span style="color: gray; font-size: 11px;">+{len(permissions) - 3} more</span>')
        
        return format_html(''.join(badges))
    permission_summary.short_description = 'Permissions'
    
    def staff_count(self, obj):
        """Display count of staff members with this role (from annotation)."""
        count = getattr(obj, '_active_staff_count', 0)
        if count > 0:
            url = f'/admin/tournaments/tournamentstaff/?role__id__exact={obj.id}&is_active__exact=1'
            return format_html('<a href="{}">{} active</a>', url, count)
        return format_html('<span style="color: gray;">0 active</span>')
    staff_count.short_description = 'Active Staff'
    
    def activate_roles(self, request, queryset):
        """Activate selected roles."""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} role(s) activated successfully.', messages.SUCCESS)
    activate_roles.short_description = "✅ Activate selected roles"
    
    def deactivate_roles(self, request, queryset):
        """Deactivate selected roles."""
        # Check for system roles
        system_roles = queryset.filter(is_system_role=True)
        if system_roles.exists():
            self.message_user(
                request, 
                'Cannot deactivate system roles. Please uncheck is_system_role first.',
                messages.ERROR
            )
            return
        
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} role(s) deactivated.', messages.INFO)
    deactivate_roles.short_description = "❌ Deactivate selected roles"
    
    def clone_role(self, request, queryset):
        """Clone selected roles for customization."""
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one role to clone.', messages.WARNING)
            return
        
        original = queryset.first()
        clone = TournamentStaffRole.objects.create(
            name=f'{original.name} (Copy)',
            slug=f'{original.slug}-copy',
            description=original.description,
            can_review_participants=original.can_review_participants,
            can_verify_payments=original.can_verify_payments,
            can_manage_brackets=original.can_manage_brackets,
            can_manage_matches=original.can_manage_matches,
            can_enter_scores=original.can_enter_scores,
            can_handle_disputes=original.can_handle_disputes,
            can_send_notifications=original.can_send_notifications,
            can_manage_social_media=original.can_manage_social_media,
            can_access_support=original.can_access_support,
            can_modify_tournament=original.can_modify_tournament,
            can_view_pii=original.can_view_pii,
            can_view_payment_proofs=original.can_view_payment_proofs,
            can_export_data=original.can_export_data,
            is_system_role=False,
            is_active=True,
        )
        
        self.message_user(
            request, 
            f'Role "{original.name}" cloned as "{clone.name}". You can now customize it.',
            messages.SUCCESS
        )
    clone_role.short_description = "📋 Clone selected role"
    
    def get_readonly_fields(self, request, obj=None):
        """Make system roles mostly read-only."""
        readonly = list(super().get_readonly_fields(request, obj))
        
        if obj and obj.is_system_role:
            # System roles can only have name/description/is_active modified
            readonly.extend([
                'slug', 'can_review_participants', 'can_verify_payments',
                'can_manage_brackets', 'can_manage_matches', 'can_enter_scores',
                'can_handle_disputes', 'can_send_notifications', 'can_manage_social_media',
                'can_access_support', 'can_modify_tournament', 'can_view_pii',
                'can_view_payment_proofs', 'can_export_data', 'is_system_role'
            ])
        
        return readonly


# TournamentStaffAdmin and TournamentStaffInline removed in Phase 1 cleanup.
# TournamentStaff model has been deleted. Use TournamentStaffAssignment instead.
