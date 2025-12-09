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
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from django.contrib import messages

from apps.tournaments.models import TournamentStaffRole, TournamentStaff


@admin.register(TournamentStaffRole)
class TournamentStaffRoleAdmin(admin.ModelAdmin):
    """Admin interface for managing staff roles and permissions."""
    
    list_display = [
        'name', 'slug', 'permission_summary', 'staff_count', 
        'is_system_role', 'is_active', 'created_at'
    ]
    list_filter = ['is_system_role', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    readonly_fields = ['created_at', 'updated_at', 'staff_count']
    prepopulated_fields = {'slug': ('name',)}
    
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
        """Display count of staff members with this role."""
        count = TournamentStaff.objects.filter(role=obj, is_active=True).count()
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


@admin.register(TournamentStaff)
class TournamentStaffAdmin(admin.ModelAdmin):
    """Admin interface for managing staff assignments."""
    
    list_display = [
        'user_link', 'tournament_link', 'role', 'status_badge',
        'assigned_at', 'assigned_by', 'quick_actions'
    ]
    list_filter = [
        'is_active', 'role', 'assigned_at',
        ('tournament', admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'tournament__name', 'tournament__slug', 'role__name'
    ]
    readonly_fields = [
        'assigned_at', 'assigned_by', 'deactivated_at', 'deactivated_by'
    ]
    autocomplete_fields = ['user', 'tournament', 'assigned_by', 'deactivated_by']
    
    fieldsets = (
        ('Staff Assignment', {
            'fields': ('tournament', 'user', 'role', 'is_active')
        }),
        ('Assignment Details', {
            'fields': ('notes', 'assigned_at', 'assigned_by')
        }),
        ('Deactivation Info', {
            'fields': ('deactivated_at', 'deactivated_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activate_assignments', 'deactivate_assignments']
    
    def user_link(self, obj):
        """Display user with link to their profile."""
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html(
            '<a href="{}">{}</a> <span style="color: gray; font-size: 11px;">({})</span>',
            url, obj.user.get_full_name() or obj.user.username, obj.user.username
        )
    user_link.short_description = 'Staff Member'
    user_link.admin_order_field = 'user__username'
    
    def tournament_link(self, obj):
        """Display tournament with link."""
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html('<a href="{}">{}</a>', url, obj.tournament.name)
    tournament_link.short_description = 'Tournament'
    tournament_link.admin_order_field = 'tournament__name'
    
    def status_badge(self, obj):
        """Display active/inactive status as colored badge."""
        if obj.is_active:
            return format_html(
                '<span style="background: #4CAF50; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">✓ Active</span>'
            )
        else:
            return format_html(
                '<span style="background: #9E9E9E; color: white; padding: 3px 10px; '
                'border-radius: 3px;">✗ Inactive</span>'
            )
    status_badge.short_description = 'Status'
    status_badge.admin_order_field = 'is_active'
    
    def quick_actions(self, obj):
        """Display quick action buttons."""
        if obj.is_active:
            return format_html(
                '<a class="button" href="#" onclick="return confirm(\'Deactivate this staff assignment?\');">Deactivate</a>'
            )
        else:
            return format_html(
                '<a class="button" href="#">Reactivate</a>'
            )
    quick_actions.short_description = 'Actions'
    
    def activate_assignments(self, request, queryset):
        """Activate selected staff assignments."""
        count = 0
        for assignment in queryset.filter(is_active=False):
            assignment.reactivate()
            count += 1
        
        self.message_user(request, f'{count} assignment(s) reactivated.', messages.SUCCESS)
    activate_assignments.short_description = "✅ Activate selected assignments"
    
    def deactivate_assignments(self, request, queryset):
        """Deactivate selected staff assignments."""
        count = 0
        for assignment in queryset.filter(is_active=True):
            assignment.deactivate(deactivated_by=request.user)
            count += 1
        
        self.message_user(request, f'{count} assignment(s) deactivated.', messages.INFO)
    deactivate_assignments.short_description = "❌ Deactivate selected assignments"
    
    def save_model(self, request, obj, form, change):
        """Track who assigned the staff member."""
        if not change:  # New assignment
            obj.assigned_by = request.user
        
        super().save_model(request, obj, form, change)


# Inline for TournamentAdmin
class TournamentStaffInline(admin.TabularInline):
    """Inline editor for staff assignments within Tournament admin."""
    model = TournamentStaff
    extra = 0
    can_delete = True
    show_change_link = True
    
    fields = ['user', 'role', 'is_active', 'notes']
    autocomplete_fields = ['user']
    
    def get_queryset(self, request):
        """Show only active assignments by default."""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'role')
